"""Convert the JSON dataset to a compact, compressed .npz file.

Usage:
    python convert_dataset.py [--source dynamic_data_60fnew.json]
                              [--target dynamic_data_60fnew.npz]

The training script (train_model3.py) automatically prefers the .npz file
when it exists — it is much smaller and loads faster than the 27 MB
pretty-printed JSON.

savedata1.py still writes JSON (so samples can be appended incrementally);
run this script again after recording to refresh the .npz copy.
"""
import os
import json
import argparse
from collections import Counter

import joblib
import numpy as np

import config


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def convert(source=None, target=None):
    source = source or config.DATASET_FILE
    target = target or config.DATASET_NPZ_FILE

    if not os.path.exists(source):
        print(f"Error: dataset '{source}' not found.")
        return 1

    print(f"Loading {source} ...")
    raw = load_json(source)

    if not raw:
        print("Error: empty dataset.")
        return 1

    expected_frames = len(raw[0]["data"])
    num_sensors = len(raw[0]["data"][0])

    X, y, timestamps = [], [], []
    skipped = 0
    for item in raw:
        seq = item.get("data")
        ok = (
            seq is not None
            and len(seq) == expected_frames
            and all(isinstance(f, list) and len(f) == num_sensors for f in seq)
        )
        if not ok:
            skipped += 1
            continue
        X.append(np.asarray(seq).flatten())
        y.append(item.get("label", "unlabeled"))
        timestamps.append(item.get("timestamp", ""))

    if not X:
        print("Error: no valid samples to convert.")
        return 1

    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y)
    timestamps = np.asarray(timestamps)

    payload = {
        "X": X,
        "y": y,
        "timestamps": timestamps,
        "expected_frames": expected_frames,
        "num_sensors": num_sensors,
    }

    try:
        np.savez_compressed(target, **payload)
        out_file = target
        out_format = "npz"
    except (AttributeError, ImportError, OSError):
        # The stdlib zipfile module is broken on some installs (it is required
        # for .npz), so fall back to a joblib container instead — same data,
        # similar size, and loadable by train_model3.py.
        out_file = target.replace(".npz", ".joblib")
        if os.path.exists(out_file):
            os.remove(out_file)
        joblib.dump(payload, out_file, compress=3)
        out_format = "joblib"
        print(f"(Warning: .npz unavailable — stdlib zipfile is broken on this machine; "
              f"using .joblib container instead.)")

    src_size = os.path.getsize(source)
    dst_size = os.path.getsize(out_file)

    print(f"Saved {out_file} ({out_format})")
    print(f"  Samples : {len(X)} ({expected_frames} frames x {num_sensors} sensors)")
    print(f"  Classes : {len(set(y))}")
    print(f"  Size    : {src_size / 1e6:.1f} MB -> {dst_size / 1e6:.2f} MB "
          f"({(1 - dst_size / src_size) * 100:.0f}% smaller)")
    print("  Per-class counts: " + ", ".join(f"{k}: {v}" for k, v in Counter(y).most_common()))
    if skipped:
        print(f"  Skipped {skipped} malformed sample(s).")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert JSON dataset to .npz")
    parser.add_argument("--source", default=None, help="input JSON file (default: config.DATASET_FILE)")
    parser.add_argument("--target", default=None, help="output .npz file (default: config.DATASET_NPZ_FILE)")
    args = parser.parse_args()
    raise SystemExit(convert(args.source, args.target))
