"""Runner integration with Kareem's real gateway and a test-only key provider."""
import base64
import json
import secrets
import threading
import unittest
from http.client import HTTPConnection

from cryptography.exceptions import InvalidTag
from main import ActionError, RunnerState, create_server


class TestKeyPool:
    """No application fallback: a controllable provider for integration tests only."""
    def __init__(self):
        self.records = []
        self.consumed = 0
        self.supply_enabled = True

    def replenish(self):
        if self.supply_enabled:
            key = secrets.token_bytes(32)
            self.records.append({'key_id': 'test-record', 'device_key': key, 'twin_key': key})

    def consume_key(self):
        if not self.records:
            return None
        self.consumed += 1
        return self.records.pop(0)


class RunnerGatewayTests(unittest.TestCase):
    def setUp(self):
        self.pool = TestKeyPool()
        self.runner = RunnerState(key_pool=self.pool)
        self.reading = {'sensor_id': 'test-sensor', 'value_ppm': 650,
                        'timestamp': '2026-11-07T12:00:00+00:00'}

    def test_missing_or_empty_pool_fails_without_epoch(self):
        for runner in (RunnerState(), self.runner):
            with self.assertRaises(ActionError):
                runner.apply({'action': 'start_epoch'})
            self.assertEqual(runner.status()['gateway']['connection_state'], 'DISCONNECTED')

    def test_matching_keys_repeated_readings_and_supply_interruption(self):
        self.pool.replenish()
        key = self.pool.records[0]['device_key']
        started = self.runner.apply({'action': 'start_epoch'})
        epoch = started['gateway']['connection_epoch']
        self.assertTrue(epoch)
        self.pool.supply_enabled = False
        for _ in range(3):
            envelope = self.runner.protect_reading(self.reading)
            self.assertEqual(self.runner.verify_reading(envelope), self.reading)
        self.assertEqual(self.pool.consumed, 1)
        status = self.runner.status()
        self.assertEqual(status['gateway']['connection_epoch'], epoch)
        self.assertEqual(status['gateway']['verification'], 'VERIFIED')
        self.assertIsNone(status['readings_delivered'])  # Verified is not Twin-accepted.
        self.assertNotIn(key.hex(), json.dumps(status))
        self.assertNotIn(base64.b64encode(key).decode(), json.dumps(status))
        with self.assertRaises(ActionError):
            self.runner.apply({'action': 'start_epoch'})
        self.assertEqual(self.pool.consumed, 1)
        self.runner.apply({'action': 'end_epoch'})
        self.assertIsNone(self.runner._device_key)
        self.assertIsNone(self.runner._twin_key)
        with self.assertRaises(ActionError):
            self.runner.apply({'action': 'start_epoch'})
        self.pool.supply_enabled = True
        self.pool.replenish()
        recovered = self.runner.apply({'action': 'start_epoch'})
        self.assertNotEqual(recovered['gateway']['connection_epoch'], epoch)
        self.assertEqual(self.pool.consumed, 2)

    def test_tampering_rejected_without_delivery_claim(self):
        self.pool.replenish()
        self.runner.start_epoch()
        envelope = self.runner.protect_reading(self.reading)
        data = bytearray(base64.b64decode(envelope['ciphertext']))
        data[0] ^= 1
        envelope['ciphertext'] = base64.b64encode(data).decode()
        with self.assertRaises(InvalidTag):
            self.runner.verify_reading(envelope)
        self.assertEqual(self.runner.status()['gateway']['verification'], 'REJECTED')
        self.assertIsNone(self.runner.status()['twin'])
        self.assertIsNone(self.runner.status()['readings_delivered'])

    def test_reset_and_closed_epoch_cannot_use_old_keys(self):
        self.pool.replenish()
        self.runner.start_epoch()
        envelope = self.runner.protect_reading(self.reading)
        self.runner.apply({'action': 'reset'})
        self.assertEqual(self.runner.status()['gateway'], {
            'connection_state': 'DISCONNECTED', 'connection_epoch': None, 'verification': None})
        for operation in (lambda: self.runner.protect_reading(self.reading),
                          lambda: self.runner.verify_reading(envelope)):
            with self.assertRaises(ActionError):
                operation()

    def test_mismatched_pair_never_establishes_epoch(self):
        self.pool.records.append({'key_id': 'test-record', 'device_key': secrets.token_bytes(32),
                                  'twin_key': secrets.token_bytes(32)})
        with self.assertRaises(ActionError):
            self.runner.start_epoch()
        self.assertEqual(self.runner.status()['gateway']['connection_state'], 'DISCONNECTED')
        self.assertIsNone(self.runner._device_key)

    def test_http_epoch_status_and_panel_are_wired(self):
        self.pool.replenish()
        with create_server(0) as server:
            server.state = self.runner
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            def request(path, payload=None):
                connection = HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                try:
                    connection.request('GET' if payload is None else 'POST', path,
                        body=None if payload is None else json.dumps(payload),
                        headers={} if payload is None else {'Content-Type': 'application/json'})
                    response = connection.getresponse()
                    return response.status, response.read()
                finally:
                    connection.close()
            try:
                code, body = request('/api/actions', {'action': 'start_epoch'})
                self.assertEqual(code, 200)
                self.assertEqual(json.loads(body)['gateway']['connection_state'], 'CONNECTED')
                self.runner.verify_reading(self.runner.protect_reading(self.reading))
                code, body = request('/api/status')
                self.assertEqual(json.loads(body)['gateway']['verification'], 'VERIFIED')
                code, body = request('/gateway-panel.js')
                self.assertEqual(code, 200)
                self.assertIn(b'export function renderGatewayPanel', body)
                self.assertIn(b'type="module"', request('/')[1])
                self.assertIn(b'./gateway-panel.js', request('/app.js')[1])
                code, body = request('/api/actions', {'action': 'end_epoch'})
                self.assertEqual(code, 200)
                self.assertEqual(json.loads(body)['gateway']['connection_state'], 'DISCONNECTED')
            finally:
                server.shutdown()
                thread.join(timeout=3)


if __name__ == '__main__':
    unittest.main()
