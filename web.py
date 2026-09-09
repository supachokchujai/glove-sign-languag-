import json
import socket
import sys
import threading
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

# One UDP socket for the app's lifetime, created lazily on first use so that
# merely importing web.py (e.g. from tests) does not claim the port.
_receiver = None
_receiver_lock = threading.Lock()
_record_lock = threading.Lock()   # only one gesture collection at a time


def _get_receiver():
    """Create and bind the UDP socket once; reuse it for every request."""
    global _receiver
    with _receiver_lock:
        if _receiver is None:
            # No SO_REUSEADDR on purpose: on Windows it would let a second
            # socket silently steal the port instead of failing fast. A UDP
            # receiver doesn't need it (no TIME_WAIT like TCP).
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((UDP_IP, UDP_PORT))
            sock.settimeout(FRAME_GAP_TIMEOUT)
            _receiver = sock
        return _receiver


def _drain_socket(sock):
    """Discard stale packets buffered before this recording started."""
    sock.settimeout(0)
    try:
        while True:
            sock.recvfrom(2048)
    except BlockingIOError:
        pass
    finally:
        sock.settimeout(FRAME_GAP_TIMEOUT)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/predict_once')
def predict_once():
    if not _record_lock.acquire(blocking=False):
        return jsonify({
            "status": "error",
            "message": "Another prediction is already in progress",
        })

    start = time.monotonic()
    print(f"Starting gesture recording (waiting for {expected_frames} frames)...")

    try:
        try:
            sock = _get_receiver()
        except OSError as e:
            msg = (f"Cannot bind UDP port {UDP_PORT} — is savedata1.py or a "
                   f"monitor script already running? ({e})")
            print(f"Error: {msg}")
            return jsonify({"status": "error", "message": msg})

        _drain_socket(sock)

        buffer_frames = []
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
        _record_lock.release()


if __name__ == '__main__':
    # Claim the UDP port up front so a conflict is reported immediately,
    # not on the first click of the predict button.
    try:
        _get_receiver()
    except OSError as e:
        print(f"Critical Error: cannot bind UDP port {UDP_PORT} — is "
              f"savedata1.py or a monitor script already running?\n  {e}")
        sys.exit(1)

    # debug reloader must stay off: it spawns a second process that would
    # fight over the UDP socket.
    print(f"Web app ready: http://localhost:{config.WEB_PORT}")
    app.run(host=config.WEB_HOST, port=config.WEB_PORT, debug=False, use_reloader=False)
