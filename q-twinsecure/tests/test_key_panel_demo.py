"""Check the independent panel's real backend without teammate dependencies."""

import json
from threading import Thread
from time import monotonic, sleep
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from qkd.panel_demo import create_server


class KeyPanelDemoTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server(port=0, capacity=1, generation_interval=0.05)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def action(self, name):
        request = Request(self.base + "/api/key-pool/actions",
                          data=json.dumps({"action": name}).encode(),
                          headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=2) as response:
            return json.load(response)

    def wait_for_keys(self):
        deadline = monotonic() + 3
        while monotonic() < deadline:
            with urlopen(self.base + "/api/key-pool", timeout=2) as response:
                state = json.load(response)
            if state["key_pool"]["keys_available"] == 1:
                return state
            sleep(0.01)
        self.fail("Preview did not replenish automatically")

    def test_real_status_normal_interruption_and_recovery(self):
        # No browser or API request is needed to trigger generation.
        sleep(0.12)
        state = self.wait_for_keys()
        self.assertEqual(state["key_pool"]["keys_generated"], 1)
        self.assertFalse(self.action("interrupt")["key_pool"]["supply_enabled"])
        self.assertEqual(self.action("consume")["key_pool"]["keys_consumed"], 1)
        self.assertIn("failed", self.action("consume")["result"])
        sleep(0.12)
        with urlopen(self.base + "/api/key-pool", timeout=2) as response:
            self.assertEqual(json.load(response)["key_pool"]["keys_generated"], 1)
        self.assertTrue(self.action("resume")["key_pool"]["supply_enabled"])
        state = self.wait_for_keys()
        self.assertEqual(state["key_pool"]["keys_generated"], 2)
        self.assertEqual(set(state), {"key_pool"})
        self.assertTrue(all(type(value) in (bool, int) for value in state["key_pool"].values()))

    def test_static_files_and_unknown_paths(self):
        for path, content_type in (("/", "text/html"), ("/key-panel.js", "text/javascript")):
            with self.subTest(path=path), urlopen(self.base + path, timeout=2) as response:
                self.assertTrue(response.headers["Content-Type"].startswith(content_type))
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base + "/qkd/key_pool.py", timeout=2)
        self.assertEqual(error.exception.code, 404)
        error.exception.close()

    def test_full_pool_waits_and_refills_only_after_allocation(self):
        full_status = self.wait_for_keys()["key_pool"]
        self.assertEqual(full_status["keys_available"], full_status["capacity"])
        sleep(0.12)
        with urlopen(self.base + "/api/key-pool", timeout=2) as response:
            self.assertEqual(json.load(response)["key_pool"], full_status)
        self.action("consume")
        refilled = self.wait_for_keys()["key_pool"]
        self.assertEqual(refilled["keys_available"], refilled["capacity"])
        self.assertEqual(refilled["keys_generated"], full_status["keys_generated"] + 1)
        self.assertEqual(refilled["keys_consumed"], 1)

    def test_invalid_actions_and_cross_origin_rejected(self):
        for body in (b"not-json", b"[]", b'{"action":"unknown"}',
                     b'{"action":"generate"}', b'{"action":"consume","count":2}', b"x" * 1025):
            request = Request(self.base + "/api/key-pool/actions", data=body)
            with self.subTest(body=body[:30]), self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=2)
            self.assertEqual(error.exception.code, 400)
            error.exception.close()
        request = Request(self.base + "/api/key-pool/actions", data=b'{"action":"generate"}',
                          headers={"Origin": "http://example.invalid"})
        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=2)
        self.assertEqual(error.exception.code, 403)
        error.exception.close()


if __name__ == "__main__":
    unittest.main()
