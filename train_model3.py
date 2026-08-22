import os
import json
import joblib
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

import config


def load_dataset():
    """Load samples as (X, y, expected_frames, num_sensors).

    Prefers the compact .npz / .joblib copy (see convert_dataset.py); falls
    back to the JSON file if neither compact copy exists.
    """
    npz_file = config.DATASET_NPZ_FILE
    joblib_file = config.DATASET_NPZ_FILE.replace(".npz", ".joblib")

    if os.path.exists(npz_file):
        print(f"Loading dataset from {npz_file} (compressed)...")
        data = np.load(npz_file)
    elif os.path.exists(joblib_file):
        print(f"Loading dataset from {joblib_file} (compressed)...")
        data = joblib.load(joblib_file)
    else:
        data = None

    if data is not None:
        expected_frames = int(data["expected_frames"])
        num_sensors = int(data["num_sensors"])
        X = data["X"]
        y = data["y"]
        print(f"Detected structure: {expected_frames} frames x {num_sensors} sensors")
        print(f"Total features per sample: {expected_frames * num_sensors}")
        return X, y, expected_frames, num_sensors

    if not os.path.exists(config.DATASET_FILE):
        print(f"Error: Dataset file '{config.DATASET_FILE}' not found.")
        return None

    print(f"Loading dataset from {config.DATASET_FILE}...")
    with open(config.DATASET_FILE, 'r', encoding='utf-8') as f:
        try:
            raw_data = json.load(f)
        except json.JSONDecodeError as err:
            print(f"Error: Malformed JSON dataset file: {err}")
            return None

    if not raw_data:
        print("Error: Empty dataset.")
        return None

    expected_frames = len(raw_data[0]['data'])
    num_sensors = len(raw_data[0]['data'][0])

    print(f"Detected structure: {expected_frames} frames x {num_sensors} sensors")
    print(f"Total features per sample: {expected_frames * num_sensors}")

    X, y = [], []
    skipped = 0

    for item in raw_data:
        sequence = np.array(item['data'])
        if len(sequence) != expected_frames:
            skipped += 1
            continue
        X.append(sequence.flatten())
        y.append(item['label'])

    print(f"Successfully loaded {len(X)} samples (skipped {skipped} due to frame mismatch)\n")

    if not X:
        print("Error: No usable samples.")
        return None
    return np.array(X), np.array(y), expected_frames, num_sensors


def train_network():
    print("--- Starting Model Training (Dynamic Version) ---\n")

    loaded = load_dataset()
    if loaded is None:
        return
    X, y, expected_frames, num_sensors = loaded

    print(f"Total samples: {len(X)}\n")

    # Split dataset
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
    except ValueError:
        print("Warning: Class imbalance or low counts. Disabling stratification split.")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

    print(f"Training set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples\n")

    # Scale data
    print("Scaling input features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Initialize and train MLP
    print("\nTraining Multi-Layer Perceptron model...")
    model = MLPClassifier(
        hidden_layer_sizes=(256, 128),
        activation='relu',
        solver='adam',
        max_iter=500,
        random_state=42,
        verbose=True,
        early_stopping=False
    )
    
    model.fit(X_train_scaled, y_train)

    # Evaluate performance
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nModel Accuracy: {accuracy * 100:.2f}%")

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Save Confusion Matrix plot
    print("Generating confusion matrix plot...")
    try:
        cm = confusion_matrix(y_test, y_pred)
        plt.figure(figsize=(8, 6))
        classes = np.unique(np.concatenate((y_test, y_pred)))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=classes, yticklabels=classes)
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.title('Confusion Matrix (Dynamic Gestures)')
        plt.tight_layout()
        plt.savefig(config.CONFUSION_MATRIX_FILE, dpi=300)
        plt.close()
        print(f"Confusion matrix saved to '{config.CONFUSION_MATRIX_FILE}'.")
    except Exception as plot_err:
        print(f"Warning: Could not save plot: {plot_err}")

    # Save model artifacts
    model_data = {
        "model": model,
        "expected_frames": expected_frames
    }
    joblib.dump(model_data, config.MODEL_FILE)
    joblib.dump(scaler, config.SCALER_FILE)
    
    print("\nTraining sequence completed successfully.")
    print(f"Saved model: {config.MODEL_FILE}")
    print(f"Saved scaler: {config.SCALER_FILE}")

if __name__ == "__main__":
    train_network()