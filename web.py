import json
import socket
import sys
import time

import joblib
import numpy as np
from flask import Flask, jsonify, render_template

import config
from glove_utils import build_frame_vector

app = Flask(__name__)

try:
    model_data = joblib.load(config.MODEL_FILE)
    model = model_data["model"]
    expected_frames = model_data["expected_frames"]
    scaler = joblib.load(config.SCALER_FILE)
    print(f"Model loaded successfully. Expected frames per gesture: {expected_frames}")
except Exception as e:
    print(f"Critical Error: Failed to load model or scaler: {e}")
    sys.exit(1)

# UDP settings — keep in sync with sketch_feb11a/main/config.h on the ESP32.
UDP_IP = config.UDP_IP
UDP_PORT = config.UDP_PORT
# ESP32 sends ~20 Hz, so expected_frames (60) frames take ~3 s to collect.
FRAME_GAP_TIMEOUT = 1.0     # seconds without a packet -> give up
MAX_RECORD_SECONDS = 6.0    # hard cap (60 frames @ ~20 Hz needs ~3 s)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/predict_once')
def predict_once():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(FRAME_GAP_TIMEOUT)

    buffer_frames = []
    start = time.monotonic()
    print(f"Starting gesture recording (waiting for {expected_frames} frames)...")

    try:
        while len(buffer_frames) < expected_frames:
            if time.monotonic() - start > MAX_RECORD_SECONDS:
                return jsonify({
                    "status": "error",
                    "message": "Glove data collection timed out (max duration reached)",
                })

            try:
                data, _ = sock.recvfrom(2048)
            except socket.timeout:
                continue  # keep waiting until the overall cap is hit

            try:
                frame_vector = build_frame_vector(json.loads(data.decode('utf-8')))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue  # skip malformed packets

            buffer_frames.append(frame_vector)

        # Reshape frames from (expected_frames, 11) to (1, expected_frames * 11)
        X_realtime = np.array(buffer_frames).reshape(1, -1)
        X_realtime_scaled = scaler.transform(X_realtime)
        prediction = model.predict(X_realtime_scaled)[0]
        elapsed = time.monotonic() - start

        print(f"Prediction success: {prediction} ({elapsed:.1f}s)")
        return jsonify({
            "status": "success",
            "prediction": str(prediction),
            "duration_seconds": round(elapsed, 2),
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        sock.close()


if __name__ == '__main__':
    app.run(host=config.WEB_HOST, port=config.WEB_PORT, debug=True)
