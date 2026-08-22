import json
import socket
import threading
import time
import unittest

import savedata1


def make_udp_pair():
    """Return (receiver_socket, send_to_addr) bound to a random free port."""
    recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv.bind(("127.0.0.1", 0))
    recv.settimeout(0.5)
    addr = ("127.0.0.1", recv.getsockname()[1])
    return recv, addr


def send_frames(addr, n, delay):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for i in range(n):
        payload = {
            "flex": [100 + i] * 5,
            "acc": [0.0, 0.0, 9.8],
            "gyro": [0.0, 0.0, 0.0],
        }
        s.sendto(json.dumps(payload).encode(), addr)
        time.sleep(delay)
    s.close()


class TestCollectSample(unittest.TestCase):
    def test_collects_expected_frames(self):
        recv, addr = make_udp_pair()
        t = threading.Thread(
            target=send_frames, args=(addr, savedata1.config.TARGET_FRAMES, 0.01), daemon=True
        )
        t.start()
        frames, stats = savedata1.collect_sample(recv)
        recv.close()
        self.assertEqual(len(frames), savedata1.config.TARGET_FRAMES)
        self.assertIsNone(stats["reason"])
        self.assertGreater(stats["rate"], 0)

    def test_aborts_on_packet_gap(self):
        recv, addr = make_udp_pair()
        t = threading.Thread(target=send_frames, args=(addr, 3, 0.01), daemon=True)
        t.start()
        frames, stats = savedata1.collect_sample(recv)
        recv.close()
        self.assertIsNone(frames)
        self.assertIn("no packet", stats["reason"])

    def test_skips_malformed_packets(self):
        recv, addr = make_udp_pair()

        def bad_then_good():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for _ in range(5):
                s.sendto(b"not json", addr)
                time.sleep(0.01)
            s.close()
            send_frames(addr, savedata1.config.TARGET_FRAMES, 0.01)

        t = threading.Thread(target=bad_then_good, daemon=True)
        t.start()
        frames, stats = savedata1.collect_sample(recv)
        recv.close()
        self.assertEqual(len(frames), savedata1.config.TARGET_FRAMES)
        self.assertIsNone(stats["reason"])


if __name__ == "__main__":
    unittest.main()
