"""Shared configuration for the Smart Glove sign-language translator.

Central place for UDP settings, file paths, and frame constants so every
script uses the same values. Edit here instead of hardcoding in each file.

The Arduino side has its own copy: `sketch_feb11a/main/config.h`.
Keep UDP_PORT / SEND_DELAY_MS in sync with it.
"""
import os

# --- UDP / hardware ---
UDP_IP = "0.0.0.0"        # bind address for receiving UDP packets
UDP_PORT = 4210           # port the ESP32 sends to (sync with config.h)
TARGET_FRAMES = 60        # frames per gesture sample (must match the trained model)
SEND_DELAY_MS = 50        # ESP32 send interval in ms -> ~20 Hz

# --- Files (absolute paths, independent of the working directory) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_FILE = os.path.join(BASE_DIR, "dynamic_data_60fnew.json")
DATASET_NPZ_FILE = os.path.join(BASE_DIR, "dynamic_data_60fnew.npz")
MODEL_FILE = os.path.join(BASE_DIR, "smart_glove_model_dynamic2.pkl")
SCALER_FILE = os.path.join(BASE_DIR, "scaler_dynamic2.pkl")
CONFUSION_MATRIX_FILE = os.path.join(BASE_DIR, "confusion_matrix.png")

# --- Data recording (savedata1.py) ---
# If no packet arrives for this long while recording, treat the sample as
# finished/aborted (protects against a dropped link or ESP32 stalls).
RECORD_GAP_TIMEOUT = 0.5   # seconds
# Hard cap per sample: 60 frames @ ~20 Hz should take ~3 s.
RECORD_MAX_SECONDS = 6.0   # seconds

# --- Web server (web.py) ---
WEB_HOST = "0.0.0.0"
WEB_PORT = 5000
