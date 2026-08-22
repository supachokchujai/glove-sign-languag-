import os
import json
import unittest

import joblib
import numpy as np

import config


class TestJoblibDataset(unittest.TestCase):
    """Fallback container used when the stdlib zipfile is broken."""

    def test_structure_is_consistent(self):
        path = config.DATASET_NPZ_FILE.replace(".npz", ".joblib")
        if not os.path.exists(path):
            self.skipTest("dataset .joblib not present (run convert_dataset.py)")

        data = joblib.load(path)
        X, y = data["X"], data["y"]

        self.assertGreater(len(X), 0)
        self.assertEqual(len(X), len(y))
        self.assertEqual(X.ndim, 2)
        self.assertEqual(
            X.shape[1],
            int(data["expected_frames"]) * int(data["num_sensors"]),
        )
        self.assertEqual(int(data["expected_frames"]), config.TARGET_FRAMES)


class TestJsonDataset(unittest.TestCase):
    def test_structure_is_consistent(self):
        if not os.path.exists(config.DATASET_FILE):
            self.skipTest("dataset JSON not present (regenerate with savedata1.py)")

        with open(config.DATASET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertGreater(len(data), 0)
        first = data[0]
        self.assertIn("label", first)
        self.assertIn("data", first)

        frames = len(first["data"])
        sensors = len(first["data"][0])
        self.assertEqual(frames, config.TARGET_FRAMES)
        self.assertEqual(sensors, 11)  # flex 5 + acc 3 + gyro 3

        for item in data:
            self.assertEqual(len(item["data"]), frames)
            self.assertTrue(item["label"])
            for frame in item["data"]:
                self.assertEqual(len(frame), sensors)


class TestNpzDataset(unittest.TestCase):
    def test_structure_is_consistent(self):
        if not os.path.exists(config.DATASET_NPZ_FILE):
            self.skipTest("dataset .npz not present (run convert_dataset.py)")

        data = np.load(config.DATASET_NPZ_FILE)
        X, y = data["X"], data["y"]

        self.assertGreater(len(X), 0)
        self.assertEqual(len(X), len(y))
        self.assertEqual(X.ndim, 2)
        self.assertEqual(
            X.shape[1],
            int(data["expected_frames"]) * int(data["num_sensors"]),
        )
        self.assertEqual(int(data["expected_frames"]), config.TARGET_FRAMES)


if __name__ == "__main__":
    unittest.main()
