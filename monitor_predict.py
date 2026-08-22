import os
import sys
import json
import socket
import joblib
import numpy as np
from collections import deque

import config
from glove_utils import build_frame_vector

if not os.path.exists(config.MODEL_FILE) or not os.path.exists(config.SCALER_FILE):
    print("Error: Model or scaler files not found. Please train the model first.")
    sys.exit(1)

try:
    model_data = joblib.load(config.MODEL_FILE)
    model = model_data["model"]
    expected_frames = model_data["expected_frames"]
    scaler = joblib.load(config.SCALER_FILE)
    print(f"Configuration loaded. Expected frames: {expected_frames}")
except Exception as e:
    print(f"Error: Failed to load model state: {e}")
    sys.exit(1)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((config.UDP_IP, config.UDP_PORT))
print(f"Listening for UDP packets on port {config.UDP_PORT}...\n")

frame_buffer = deque(maxlen=expected_frames)

header = f"{'Thumb':^8} | {'Index':^8} | {'Middle':^8} | {'Ring':^8} | {'Pinky':^8} | {'Buffer':^8} | {'Prediction':^15}"
print(header)
print("-" * len(header))

last_prediction = "None"

try:
    while True:
        data, _ = sock.recvfrom(2048)
        try:
            payload = json.loads(data.decode('utf-8'))
            
            # Combine flex and IMU readings to create single frame vector
            frame_vector = build_frame_vector(payload)
            frame_buffer.append(frame_vector)
            
            prediction = last_prediction
            if len(frame_buffer) == expected_frames:
                # Flatten the sliding window buffer using numpy reshape
                X_realtime = np.array(frame_buffer).reshape(1, -1)
                X_realtime_scaled = scaler.transform(X_realtime)
                prediction = model.predict(X_realtime_scaled)[0]
                last_prediction = prediction
            
            flex_str = " | ".join([f"{val:^8}" for val in payload.get('flex', [0, 0, 0, 0, 0])])
            buffer_str = f"{len(frame_buffer)}/{expected_frames}"
            
            sys.stdout.write(f"\r{flex_str} | {buffer_str:^8} | \033[1;32;40m{prediction:^15}\033[0m")
            sys.stdout.flush()
            
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        except Exception as e:
            sys.stdout.write(f"\r[Error] {str(e)}")
            sys.stdout.flush()

except KeyboardInterrupt:
    print("\n\nReal-time Translation Monitor stopped.")
