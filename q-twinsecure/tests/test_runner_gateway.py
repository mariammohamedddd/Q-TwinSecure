"""Integrated runner checks using the real team components and matching key pool."""
import base64
import json
import unittest
from cryptography.exceptions import InvalidTag
from main import ActionError, RunnerState


class RunnerGatewayTests(unittest.TestCase):
    def setUp(self):
        self.runner = RunnerState()

    def tearDown(self):
        self.runner.key_pool.close()

    def ready(self):
        self.runner.apply({'action': 'generate_keys', 'count': 1})
        self.runner.apply({'action': 'start_epoch'})

    def test_empty_pool_fails_and_overlapping_epoch_does_not_consume(self):
        with self.assertRaises(ActionError):
            self.runner.apply({'action': 'start_epoch'})
        self.ready()
        with self.assertRaises(ActionError):
            self.runner.apply({'action': 'start_epoch'})
        self.assertEqual(self.runner.status()['key_pool']['keys_consumed'], 1)

    def test_tampered_envelope_never_changes_twin_or_delivery_count(self):
        self.ready()
        self.runner.apply({'action': 'send_reading'})
        before = self.runner.status()
        envelope = self.runner.protect_reading(self.runner.sensor.read())
        data = bytearray(base64.b64decode(envelope['ciphertext']))
        data[0] ^= 1
        envelope['ciphertext'] = base64.b64encode(data).decode()
        with self.assertRaises(InvalidTag):
            self.runner.accept_envelope(envelope)
        after = self.runner.status()
        self.assertEqual(after['twin'], before['twin'])
        self.assertEqual(after['readings_delivered'], before['readings_delivered'])
        self.assertEqual(after['gateway']['verification'], 'REJECTED')

    def test_twin_validation_failure_does_not_count_delivery(self):
        self.ready()
        reading = {'sensor_id': 'test', 'value_ppm': -1, 'timestamp': self.runner.now().isoformat()}
        with self.assertRaises(ValueError):
            self.runner.accept_envelope(self.runner.protect_reading(reading))
        self.assertEqual(self.runner.status()['readings_delivered'], 0)
        self.assertIsNone(self.runner.status()['twin']['timestamp'])

    def test_private_key_handoff_multiple_readings_and_status_safety(self):
        self.ready()
        key = self.runner._device_key
        epoch = self.runner.status()['gateway']['connection_epoch']
        self.runner.apply({'action': 'interrupt_supply'})
        for _ in range(3):
            status = self.runner.apply({'action': 'send_reading'})
        self.assertEqual(status['key_pool']['keys_consumed'], 1)
        self.assertEqual(status['readings_delivered'], 3)
        self.assertEqual(status['gateway']['connection_epoch'], epoch)
        encoded = json.dumps(status)
        self.assertNotIn(key.hex(), encoded)
        self.assertNotIn(base64.b64encode(key).decode(), encoded)
        for secret_field in ('device_key', 'twin_key', 'ciphertext', 'nonce'):
            self.assertNotIn(secret_field, encoded)
        self.runner.apply({'action': 'end_epoch'})
        self.assertIsNone(self.runner._device_key)
        self.assertIsNone(self.runner._twin_key)
        with self.assertRaises(ActionError):
            self.runner.protect_reading({})

    def test_buffered_keys_survive_interruption_and_capacity_is_respected(self):
        self.runner.apply({'action': 'generate_keys', 'count': 100})
        self.assertEqual(self.runner.status()['key_pool']['keys_available'], 10)
        with self.assertRaises(ActionError):
            self.runner.apply({'action': 'generate_keys', 'count': 1})
        self.runner.apply({'action': 'interrupt_supply'})
        self.runner.apply({'action': 'start_epoch'})
        self.assertEqual(self.runner.status()['key_pool']['keys_available'], 9)


if __name__ == '__main__':
    unittest.main()
