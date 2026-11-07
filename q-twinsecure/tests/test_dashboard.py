"""Real HTTP checks for Nancy's Phase 2 control API."""
import json
import threading
import unittest
from http.client import HTTPConnection
from main import create_server, RunnerState, ActionError, MAX_EVENTS


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=3)
        cls.server.server_close()

    def setUp(self):
        self.server.state = RunnerState()

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
                               ("/style.css", "text/css"), ("/key-panel.js", "text/javascript"),
                               ("/sensor-panel.js", "text/javascript"), ("/twin-panel.js", "text/javascript"),
                               ("/sensor-panel.css", "text/css"), ("/gateway-panel.js", "text/javascript")]:
            with self.subTest(path=path):
                code, kind, body = self.request(path)
                self.assertEqual(code, 200)
                self.assertIn(expected, kind)
                self.assertTrue(body)

    def test_initial_real_status(self):
        code, _, body = self.request('/api/status')
        status = json.loads(body)
        self.assertEqual(code, 200)
        self.assertEqual(status['phase'], 3)
        self.assertTrue(status['integration_ready'])
        self.assertEqual(status['key_pool']['keys_available'], 0)
        self.assertEqual(status['gateway']['connection_state'], 'DISCONNECTED')
        self.assertIsNone(status['sensor'])
        self.assertEqual(status['twin']['freshness'], 'MISSING')
        self.assertEqual(status['readings_delivered'], 0)

    def test_http_normal_interruption_expiry_recovery_and_reset(self):
        def act(action, **fields):
            code, data = self.action({'action': action, **fields})
            self.assertEqual(code, 200, data)
            return data
        act('generate_keys', count=1)
        act('start_epoch')
        first = act('send_reading')
        self.assertEqual(first['sensor']['value_ppm'], first['twin']['value_ppm'])
        self.assertEqual(first['twin']['freshness'], 'CURRENT')
        act('interrupt_supply')
        active = act('send_reading')
        self.assertEqual(active['readings_delivered'], 2)
        self.assertEqual(active['key_pool']['keys_consumed'], 1)
        self.assertEqual(self.action({'action': 'generate_keys', 'count': 1})[0], 409)
        act('end_epoch')
        code, blocked = self.action({'action': 'start_epoch'})
        self.assertEqual(code, 409)
        self.assertEqual(blocked['status']['gateway']['connection_state'], 'DISCONNECTED')
        self.assertEqual(self.action({'action': 'send_reading'})[0], 409)
        self.assertEqual(act('advance_time', seconds=6)['twin']['freshness'], 'DELAYED')
        self.assertEqual(act('advance_time', seconds=10)['twin']['freshness'], 'MISSING')
        act('resume_supply')
        act('generate_keys', count=1)
        act('start_epoch')
        recovered = act('send_reading')
        self.assertEqual(recovered['twin']['freshness'], 'CURRENT')
        self.assertEqual(recovered['readings_delivered'], 3)
        self.assertEqual(recovered['key_pool']['keys_consumed'], 2)
        reset = act('reset')
        self.assertEqual(reset['readings_delivered'], 0)
        self.assertEqual(reset['readings_generated'], 0)
        self.assertEqual(reset['key_pool']['keys_generated'], 0)
        self.assertEqual(reset['clock']['elapsed_seconds'], 0)
        self.assertIsNone(reset['sensor'])
        self.assertEqual(reset['twin']['freshness'], 'MISSING')
        self.assertEqual(len(reset['events']), 1)

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
        state = RunnerState()
        for _ in range(24):
            state.apply({'action': 'advance_time', 'seconds': 3600})
        with self.assertRaises(ActionError):
            state.apply({'action': 'advance_time', 'seconds': 1})
        self.assertEqual(state.elapsed_seconds, 86400)
        state.apply({'action': 'reset'})
        self.assertEqual(state.apply({'action': 'advance_time', 'seconds': 1})['clock']['elapsed_seconds'], 1)

    def test_event_history_bound_and_status_copy(self):
        state = RunnerState()
        for _ in range(MAX_EVENTS + 10):
            state.apply({'action': 'advance_time', 'seconds': 1})
        status = state.status()
        self.assertEqual(len(status['events']), MAX_EVENTS)
        self.assertEqual(status['events'][0]['elapsed_seconds'], 11)
        status['events'].clear()
        self.assertEqual(len(state.events), MAX_EVENTS)


if __name__ == '__main__':
    unittest.main()
