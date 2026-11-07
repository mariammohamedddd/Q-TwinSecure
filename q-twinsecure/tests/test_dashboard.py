"""Real HTTP checks for the integrated control API."""
import json
import threading
import unittest
from http.client import HTTPConnection
from main import create_server, RunnerState, ActionError, MAX_EVENTS


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(0, auto_generate=False)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=3)
        cls.server.server_close()

    def setUp(self):
        self.server.state.close()
        self.server.state = RunnerState(auto_generate=False)

    def request(self, path, method="GET", body=None, headers=None):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.getheader("Content-Type"), response.read()
        finally:
            connection.close()

    def action(self, payload):
        code, _, body = self.request('/api/actions', 'POST', json.dumps(payload),
                                    {'Content-Type': 'application/json'})
        return code, json.loads(body)

    def test_page_and_assets(self):
        for path, expected in [("/", "text/html"), ("/app.js", "text/javascript"),
                               ("/style.css", "text/css"), ("/twin", "text/html"),
                               ("/twin-panel.js", "text/javascript"), ("/twin-panel.css", "text/css"),
                               ("/twin-live.css", "text/css")]:
            with self.subTest(path=path):
                code, kind, body = self.request(path)
                self.assertEqual(code, 200)
                self.assertIn(expected, kind)
                self.assertTrue(body)

    def test_status_does_not_fabricate_component_results(self):
        code, _, body = self.request("/api/status")
        self.assertEqual(code, 200)
        status = json.loads(body)
        self.assertEqual(status['phase'], 3)
        self.assertTrue(status["integration_ready"])
        self.assertIsNone(status['sensor'])
        self.assertIsNone(status['twin']['timestamp'])
        self.assertEqual(status['twin']['freshness'], 'MISSING')
        self.assertEqual(status['key_pool']['keys_available'], 0)
        self.assertEqual(status['gateway']['connection_state'], 'DISCONNECTED')
        self.assertEqual(status['readings_generated'], 0)
        self.assertEqual(status['readings_delivered'], 0)
        self.assertEqual(status["events"], [])
        self.assertTrue(status['actions']['reset']['enabled'])
        self.assertFalse(status['actions']['start_epoch']['enabled'])

    def test_advance_and_reset(self):
        for expected in (5, 10):
            code, status = self.action({'action': 'advance_time', 'seconds': 5})
            self.assertEqual(code, 200)
            self.assertEqual(status['clock']['elapsed_seconds'], expected)
            self.assertEqual(status['events'][-1]['elapsed_seconds'], expected)
        code, status = self.action({'action': 'reset'})
        self.assertEqual(code, 200)
        self.assertEqual(status['clock']['elapsed_seconds'], 0)
        self.assertEqual(len(status['events']), 1)
        self.assertEqual(status['events'][0]['action'], 'reset')
        self.assertEqual(status['readings_delivered'], 0)

    def test_component_actions_explicitly_unavailable(self):
        for action in ('resume_supply', 'start_epoch', 'end_epoch', 'send_reading'):
            payload = {'action': action}
            if action == 'generate_keys':
                payload['count'] = 1
            code, data = self.action(payload)
            self.assertEqual(code, 409)
            self.assertEqual(data['status']['events'][-1]['outcome'], 'unavailable')
            self.assertEqual(data['status']['readings_delivered'], 0)

    def test_invalid_actions_cannot_mutate_state_or_echo_input(self):
        payloads = [None, [], {}, {'action': 'secret-test-input'},
                    {'action': 'reset', 'secret': 'secret-test-input'},
                    {'action': 'advance_time'}, {'action': 'generate_keys', 'count': True}]
        payloads += [{'action': 'advance_time', 'seconds': value}
                     for value in (True, 0, -1, 3601, 1.5, '5', None)]
        for payload in payloads:
            with self.subTest(payload=payload):
                code, data = self.action(payload)
                self.assertEqual(code, 400)
                self.assertEqual(data['status']['clock']['elapsed_seconds'], 0)
                self.assertEqual(data['status']['events'], [])
                self.assertNotIn('secret-test-input', json.dumps(data))

    def test_request_validation(self):
        for body, headers, expected in [
            ('{}', {}, 415),
            ('{', {'Content-Type': 'application/json'}, 400),
            ('x' * 4097, {'Content-Type': 'application/json'}, 413),
            ('{}', {'Content-Type': 'application/json', 'Origin': 'https://example.com'}, 403),
        ]:
            with self.subTest(expected=expected):
                self.assertEqual(self.request('/api/actions', 'POST', body, headers)[0], expected)
        origin = f'http://127.0.0.1:{self.server.server_port}'
        self.assertEqual(self.request('/api/actions', 'POST', '{"action":"reset"}',
                         {'Content-Type': 'application/json', 'Origin': origin})[0], 200)

    def test_unknown_paths_cannot_read_project_files(self):
        for path in ("/main.py", "/../main.py", "/%2e%2e/main.py", "/missing"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request('/missing', 'POST')[0], 404)

    def test_loopback_binding(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")


class RunnerStateTests(unittest.TestCase):
    def test_clock_total_limit_and_reset_recovery(self):
        state = RunnerState(auto_generate=False)
        self.addCleanup(state.close)
        for _ in range(24):
            state.apply({'action': 'advance_time', 'seconds': 3600})
        with self.assertRaises(ActionError):
            state.apply({'action': 'advance_time', 'seconds': 1})
        self.assertEqual(state.elapsed_seconds, 86400)
        state.apply({'action': 'reset'})
        self.assertEqual(state.apply({'action': 'advance_time', 'seconds': 1})['clock']['elapsed_seconds'], 1)

    def test_event_history_bound_and_status_copy(self):
        state = RunnerState(auto_generate=False)
        self.addCleanup(state.close)
        for _ in range(MAX_EVENTS + 10):
            state.apply({'action': 'advance_time', 'seconds': 1})
        status = state.status()
        self.assertEqual(len(status['events']), MAX_EVENTS)
        self.assertEqual(status['events'][0]['elapsed_seconds'], 11)
        status['events'].clear()
        self.assertEqual(len(state.events), MAX_EVENTS)


if __name__ == '__main__':
    unittest.main()
