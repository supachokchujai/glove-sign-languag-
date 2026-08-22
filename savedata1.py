"""Data recording tool for the smart glove.

Usage:
    python savedata1.py

Improvements over the original:
  * Time-aware recording: elapsed time and effective frame rate are measured
    and reported. A recording is aborted if no packet arrives for
    RECORD_GAP_TIMEOUT (dropped link / ESP32 stall) or if it exceeds
    RECORD_MAX_SECONDS — it no longer just counts packets blindly.
  * Per-sample labels: type `l <label>` to switch the current label at any
    time (fixes the mislabel risk of one label per session), `q` to quit,
    or press Enter to record one sample with the current label.
  * Saves compact JSON (no pretty-print indent) to keep the file small.
    Run `python convert_dataset.py` afterwards for a compressed .npz copy.
"""
import os
import json
import time
import socket
import datetime

import config
from glove_utils import build_frame_vector


def flush_socket(sock):
    """Drop any stale UDP packets that arrived before the user pressed Enter."""
    sock.setblocking(False)
    while True:
        try:
            sock.recv(2048)
        except BlockingIOError:
            break
    sock.setblocking(True)
    sock.settimeout(config.RECORD_GAP_TIMEOUT)


def collect_sample(sock):
    """Collect TARGET_FRAMES frames with timing/gap detection.

    Returns (frames, stats) on success, or (None, stats) when aborted.
    stats = {"elapsed", "frames", "rate", "reason"}
    """
    sequence = []
    last_packet = None
    start = time.monotonic()

    while len(sequence) < config.TARGET_FRAMES:
        now = time.monotonic()

        if now - start > config.RECORD_MAX_SECONDS:
            return None, {
                "elapsed": now - start,
                "frames": len(sequence),
                "rate": 0.0,
                "reason": f"exceeded max duration ({config.RECORD_MAX_SECONDS:.0f}s)",
            }

        if last_packet is not None and now - last_packet > config.RECORD_GAP_TIMEOUT:
            return None, {
                "elapsed": now - start,
                "frames": len(sequence),
                "rate": 0.0,
                "reason": f"no packet for {config.RECORD_GAP_TIMEOUT * 1000:.0f}ms "
                          "(link lost or ESP32 stalled)",
            }

        try:
            data, _ = sock.recvfrom(2048)
        except socket.timeout:
            continue

        try:
            frame_vector = build_frame_vector(json.loads(data.decode("utf-8")))
        except (json.JSONDecodeError, KeyError, TypeError):
            continue  # skip malformed packets instead of counting them

        sequence.append(frame_vector)
        last_packet = time.monotonic()
        if len(sequence) % 10 == 0:
            print(".", end="", flush=True)

    elapsed = time.monotonic() - start
    return sequence, {
        "elapsed": elapsed,
        "frames": len(sequence),
        "rate": len(sequence) / elapsed if elapsed > 0 else 0.0,
        "reason": None,
    }


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((config.UDP_IP, config.UDP_PORT))

    print(f"--- Data Recording Server Active on Port {config.UDP_PORT} ---")
    print(f"Target Configuration: {config.TARGET_FRAMES} frames per gesture")
    print(f"Output File: {config.DATASET_FILE}")

    data_store = []
    if os.path.exists(config.DATASET_FILE):
        try:
            with open(config.DATASET_FILE, "r", encoding="utf-8") as f:
                data_store = json.load(f)
            print(f"Loaded {len(data_store)} existing samples.")
        except Exception as e:
            print(f"Warning: Could not read existing dataset file: {e}")

    current_label = input("\nEnter label name (e.g., 'hello', 'thanks'): ").strip() or "unlabeled"
    print(f"Recording session initialized for: '{current_label}'")
    print("Commands: [Enter] record sample | 'l <label>' switch label | 'q' quit")

    try:
        while True:
            prompt = (f"\nPress [ENTER] to record sample #{len(data_store) + 1} "
                      f"| Label: '{current_label}'\n"
                      f"  (l <label> = switch label, q = quit): ")
            cmd = input(prompt).strip()

            if cmd.lower() in ("q", "quit", "exit"):
                break

            if cmd.lower().startswith("l ") or cmd.lower().startswith("label "):
                new_label = cmd.split(" ", 1)[1].strip()
                if new_label:
                    current_label = new_label
                    print(f"Label switched to: '{current_label}'")
                else:
                    print("Usage: l <label>")
                continue

            flush_socket(sock)
            print(f"Recording {current_label} ", end="", flush=True)
            frames, stats = collect_sample(sock)

            if frames is None:
                print(f"\n[Aborted] {stats['reason']} — "
                      f"got {stats['frames']}/{config.TARGET_FRAMES} frames "
                      f"in {stats['elapsed']:.1f}s. Sample discarded.")
                continue

            record = {
                "label": current_label,
                "data": frames,
                "timestamp": datetime.datetime.now().isoformat(),
            }
            data_store.append(record)

            with open(config.DATASET_FILE, "w", encoding="utf-8") as f:
                json.dump(data_store, f, ensure_ascii=False, separators=(",", ":"))

            print(f" Done! {stats['frames']} frames in {stats['elapsed']:.1f}s "
                  f"({stats['rate']:.0f} Hz). Dataset: {len(data_store)} samples.")
            print("Hint: run 'python convert_dataset.py' to also refresh the "
                  "compressed .npz copy used by training.")

    except KeyboardInterrupt:
        print(f"\n\nSession terminated. Dataset saved to {config.DATASET_FILE}")
        print(f"Total dataset samples: {len(data_store)}")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
