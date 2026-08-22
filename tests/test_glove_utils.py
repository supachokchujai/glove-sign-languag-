import unittest

from glove_utils import build_frame_vector


class TestBuildFrameVector(unittest.TestCase):
    def test_combines_flex_acc_gyro_in_order(self):
        payload = {
            "flex": [1, 2, 3, 4, 5],
            "acc": [0.1, 0.2, 0.3],
            "gyro": [1.0, 2.0, 3.0],
        }
        self.assertEqual(
            build_frame_vector(payload),
            [1, 2, 3, 4, 5, 0.1, 0.2, 0.3, 1.0, 2.0, 3.0],
        )

    def test_result_has_11_features(self):
        payload = {
            "flex": [100, 200, 300, 400, 500],
            "acc": [0.0, 0.0, 9.8],
            "gyro": [0.0, 0.0, 0.0],
        }
        self.assertEqual(len(build_frame_vector(payload)), 11)

    def test_missing_key_raises_keyerror(self):
        payload = {"flex": [1, 2, 3, 4, 5], "acc": [0.1, 0.2, 0.3]}
        with self.assertRaises(KeyError):
            build_frame_vector(payload)

    def test_none_value_raises_typeerror(self):
        payload = {"flex": None, "acc": None, "gyro": None}
        with self.assertRaises(TypeError):
            build_frame_vector(payload)


if __name__ == "__main__":
    unittest.main()
