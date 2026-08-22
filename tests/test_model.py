import os
import unittest

import numpy as np
import joblib

import config


class TestModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(config.MODEL_FILE) or not os.path.exists(config.SCALER_FILE):
            raise unittest.SkipTest("model/scaler files not present (run train_model3.py)")
        cls.model_data = joblib.load(config.MODEL_FILE)
        cls.model = cls.model_data["model"]
        cls.scaler = joblib.load(config.SCALER_FILE)

    def test_model_and_scaler_load(self):
        self.assertIsNotNone(self.model)
        self.assertIsNotNone(self.scaler)

    def test_feature_count_matches_expected_frames(self):
        expected = self.model_data["expected_frames"]
        self.assertEqual(expected * 11, self.scaler.n_features_in_)

    def test_predict_returns_known_label(self):
        expected = self.model_data["expected_frames"]
        rng = np.random.default_rng(0)
        X = rng.normal(size=(1, expected * 11))
        X_scaled = self.scaler.transform(X)
        pred = self.model.predict(X_scaled)[0]
        self.assertIn(pred, self.model.classes_)

    def test_predict_proba_sums_to_one(self):
        expected = self.model_data["expected_frames"]
        rng = np.random.default_rng(1)
        X = rng.normal(size=(1, expected * 11))
        X_scaled = self.scaler.transform(X)
        proba = self.model.predict_proba(X_scaled)[0]
        self.assertAlmostEqual(float(proba.sum()), 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
