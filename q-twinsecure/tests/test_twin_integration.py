"""Real runner/HTTP scenarios, including failed authenticated delivery."""

import base64
import json
from http.client import HTTPConnection
from threading import Thread
import unittest
from unittest.mock import patch

from gateway.crypto import encrypt_reading
from main import ActionError, RunnerState, create_server


class IntegratedTwinTests(unittest.TestCase):
    def setUp(self):
        self.state = RunnerState(auto_generate=False)
        self.addCleanup(self.state.close)

    def act(self, action, **fields):
        return self.state.apply({'action': action, **fields})

    def connect(self):
        self.act('generate_keys', count=1)
        self.act('start_epoch')

    def test_normal_interruption_and_recovery(self):
        self.connect()
        self.act('send_reading')
        first = self.state.status()
        self.assertEqual(first['twin']['freshness'], 'CURRENT')
        self.act('send_reading')
        self.assertEqual(self.state.status()['key_pool']['keys_consumed'], 1)
        self.act('interrupt_supply')
        self.act('send_reading')
        self.assertEqual(self.state.status()['readings_delivered'], 3)
        self.act('end_epoch')
        before = self.state.status()['twin']
        with self.assertRaises(ActionError):
            self.act('start_epoch')
        with self.assertRaises(ActionError):
            self.act('send_reading')
        self.assertEqual(self.state.status()['twin'], before)
        self.assertEqual(self.act('advance_time', seconds=5)['twin']['freshness'], 'CURRENT')
        self.assertEqual(self.act('advance_time', seconds=1)['twin']['freshness'], 'DELAYED')
        self.assertEqual(self.act('advance_time', seconds=9)['twin']['freshness'], 'DELAYED')
        self.assertEqual(self.act('advance_time', seconds=1)['twin']['freshness'], 'MISSING')
        self.act('resume_supply')
        self.connect()
        recovered = self.act('send_reading')
        self.assertEqual(recovered['twin']['freshness'], 'CURRENT')
        self.assertEqual(recovered['twin']['age_seconds'], 0)
        self.assertEqual(recovered['key_pool']['keys_consumed'], 2)

    def test_tampering_rejects_without_twin_or_delivery_update(self):
        self.connect()
        self.act('send_reading')
        before = self.state.status()

        def tampered(reading, key):
            envelope = encrypt_reading(reading, key)
            data = bytearray(base64.b64decode(envelope['ciphertext']))
            data[0] ^= 1
            envelope['ciphertext'] = base64.b64encode(data).decode()
            return envelope

        with patch('digital_twin.integration.encrypt_reading', side_effect=tampered):
            with self.assertRaises(ActionError):
                self.act('send_reading')
        after = self.state.status()
        self.assertEqual(after['twin'], before['twin'])
        self.assertEqual(after['readings_delivered'], before['readings_delivered'])
        self.assertEqual(after['readings_rejected'], 1)
        self.assertEqual(after['gateway']['verification'], 'REJECTED')
        self.assertEqual(after['events'][-1]['outcome'], 'rejected')

    def test_authenticated_but_invalid_reading_is_not_accepted(self):
        self.connect()
        self.act('send_reading')
        before = self.state.status()['twin']
        reading = {'sensor_id': 'co2-simulator-01', 'value_ppm': -1,
                   'timestamp': self.state.pipeline.now().isoformat()}
        with patch.object(self.state.pipeline.sensor, 'read', return_value=reading):
            with self.assertRaises(ActionError):
                self.act('send_reading')
        self.assertEqual(self.state.status()['twin'], before)
        self.assertEqual(self.state.status()['readings_delivered'], 1)

    def test_reset_drops_observation_counts_epoch_and_old_worker(self):
        self.connect()
        self.act('send_reading')
        self.act('advance_time', seconds=20)
        previous = self.state.pipeline.pool
        result = self.act('reset')
        self.assertFalse(previous.get_status()['supply_enabled'])
        self.assertEqual(result['twin']['freshness'], 'MISSING')
        self.assertIsNone(result['twin']['value_ppm'])
        self.assertEqual(result['readings_delivered'], 0)
        self.assertEqual(result['clock']['elapsed_seconds'], 0)
        self.assertEqual(result['gateway']['connection_state'], 'DISCONNECTED')

    def test_status_does_not_consume_keys_or_advance_time_or_leak_material(self):
        self.connect()
        self.act('send_reading')
        first = self.state.status()
        self.assertEqual(self.state.status(), first)
        encoded = json.dumps(first)
        for name in ('device_key', 'twin_key', 'ciphertext', 'nonce'):
            self.assertNotIn(name, encoded)

    def test_custom_thresholds_survive_runner_reset(self):
        state = RunnerState(auto_generate=False, current_threshold=2, missing_threshold=4)
        self.addCleanup(state.close)
        state.apply({'action':'generate_keys', 'count':1})
        state.apply({'action':'start_epoch'})
        state.apply({'action':'send_reading'})
        status = state.apply({'action':'advance_time', 'seconds':3})
        self.assertEqual(status['twin']['freshness'], 'DELAYED')
        self.assertEqual(status['clock']['timestamp'], state.pipeline.now().isoformat())
        status = state.apply({'action':'reset'})
        self.assertEqual(status['twin']['current_threshold'], 2)
        self.assertEqual(status['twin']['missing_threshold'], 4)

    def test_http_actions_expose_actual_twin_and_manual_clock(self):
        server = create_server(0, auto_generate=False)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            def action(action, **fields):
                connection = HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                try:
                    connection.request('POST', '/api/actions', json.dumps({'action':action, **fields}),
                                       {'Content-Type':'application/json'})
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    return json.loads(response.read())
                finally:
                    connection.close()
            action('generate_keys', count=1)
            action('start_epoch')
            accepted = action('send_reading')
            self.assertEqual(accepted['twin']['value_ppm'], 650)
            self.assertEqual(action('advance_time', seconds=6)['twin']['freshness'], 'DELAYED')
            self.assertEqual(action('advance_time', seconds=10)['twin']['freshness'], 'MISSING')
            self.assertEqual(action('reset')['twin']['freshness'], 'MISSING')
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
