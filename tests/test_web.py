import json
import socket
import threading
import time
import unittest

import web


def make_udp_pair():
    """Return (receiver_socket, send_to_addr) bound to a random free port."""
    recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv.bind(("127.0.0.1", 0))
    recv.settimeout(0.5)
    addr = ("127.0.0.1", recv.getsockname()[1])
    return recv, addr


def send_frames(addr, n, delay=0.01):
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


class TestReceiver(unittest.TestCase):
    def setUp(self):
        # Force the shared receiver onto an ephemeral port so tests never
        # collide with a real glove monitor bound to 4210.
        web._receiver = None
        web.UDP_PORT = 0

    def tearDown(self):
        if web._receiver is not None:
            web._receiver.close()
            web._receiver = None

    def test_get_receiver_binds_once_and_reuses(self):
        sock1 = web._get_receiver()
        sock2 = web._get_receiver()
        self.assertIs(sock1, sock2)

    def test_bind_conflict_fails_fast(self):
        # Bind the blocker exactly like the real monitors do (wildcard IP),
        # then claim the same port — must raise on every OS.
        blocker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        blocker.bind(("0.0.0.0", 0))
        try:
            web._receiver = None
            web.UDP_PORT = blocker.getsockname()[1]
            with self.assertRaises(OSError):
                web._get_receiver()
        finally:
            blocker.close()

    def test_drain_socket_discards_stale_packets(self):
        sock, _addr = make_udp_pair()
        try:
            for _ in range(3):
                sock.sendto(b"stale", ("127.0.0.1", sock.getsockname()[1]))
            time.sleep(0.05)
            web._drain_socket(sock)
            # After draining, no packet should remain: a short recv must time out.
            sock.settimeout(0.2)
            with self.assertRaises(socket.timeout):
                sock.recvfrom(2048)
        finally:
            sock.close()

    def test_predict_once_rejects_concurrent_requests(self):
        acquired = web._record_lock.acquire(blocking=False)
        self.assertTrue(acquired)
        try:
            client = web.app.test_client()
            resp = client.get("/predict_once")
            body = resp.get_json()
            self.assertEqual(body["status"], "error")
            self.assertIn("already in progress", body["message"])
        finally:
            web._record_lock.release()


class TestPredictOnceTimeout(unittest.TestCase):
    def test_timeout_returns_clean_error(self):
        web._receiver = None
        web.UDP_PORT = 0
        original_cap = web.MAX_RECORD_SECONDS
        web.MAX_RECORD_SECONDS = 0.5  # keep the test fast
        try:
            # A socket bound to port 0 receives nothing, so /predict_once hits
            # the max-duration cap — proving it returns a clean JSON error
            # instead of hanging or raising.
            client = web.app.test_client()
            resp = client.get("/predict_once")
            self.assertEqual(resp.status_code, 200)
            body = resp.get_json()
            self.assertEqual(body["status"], "error")
            self.assertIn("timed out", body["message"])
        finally:
            web.MAX_RECORD_SECONDS = original_cap
            if web._receiver is not None:
                web._receiver.close()
                web._receiver = None


if __name__ == "__main__":
    unittest.main()
