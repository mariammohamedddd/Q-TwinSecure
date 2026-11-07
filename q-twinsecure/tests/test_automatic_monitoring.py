"""Automatic monitoring runs without browser polling; manual mode stays deterministic."""
import base64
import json
import math
import time
import unittest
from http.client import HTTPConnection
from threading import Thread
from unittest.mock import patch

from main import ActionError, RunnerState, create_server
from gateway.crypto import encrypt_reading


def wait_for(predicate, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.01)
    raise AssertionError('Automatic flow did not reach the expected state before timeout')


class AutomaticMonitoringTests(unittest.TestCase):
    def runner(self, **options):
        config = dict(automatic=True, reading_interval=0.06, epoch_duration=0.5,
                      pool_capacity=1, generation_interval=0.03,
                      current_threshold=0.15, missing_threshold=0.35)
        config.update(options)
        state = RunnerState(**config)
        self.addCleanup(state.close)
        return state

    def test_sampling_and_delivery_progress_without_requests_and_one_key_per_epoch(self):
        state = self.runner()
        # No status calls or browser requests drive this interval.
        time.sleep(0.25)
        status = state.status()
        self.assertGreaterEqual(status['readings_delivered'], 2)
        self.assertEqual(status['key_pool']['keys_consumed'], 1)
        self.assertEqual(status['clock']['mode'], 'realtime')
        self.assertEqual(status['twin']['freshness'], 'CURRENT')
        self.assertEqual(status['monitoring']['mode'], 'automatic')
        self.assertFalse(status['actions']['advance_time']['enabled'])
        self.assertEqual(status['sensor']['value_ppm'], status['twin']['value_ppm'])

    def test_interruption_preserves_epoch_then_exhaustion_expiry_and_recovery(self):
        state = self.runner()
        wait_for(lambda: state.status()['readings_delivered'] >= 1)
        before = state.apply({'action': 'interrupt_supply'})
        epoch = before['gateway']['connection_epoch']
        wait_for(lambda: state.status()['readings_delivered'] > before['readings_delivered'])
        self.assertEqual(state.status()['gateway']['connection_epoch'], epoch)
        wait_for(lambda: state.status()['scenario'] == 'WAITING_FOR_KEY')
        stalled = state.status()
        self.assertEqual(stalled['key_pool']['keys_available'], 0)
        self.assertEqual(stalled['gateway']['connection_state'], 'DISCONNECTED')
        wait_for(lambda: state.status()['twin']['freshness'] == 'DELAYED')
        wait_for(lambda: state.status()['twin']['freshness'] == 'MISSING')
        missing = state.status()
        self.assertEqual(missing['readings_delivered'], stalled['readings_delivered'])
        self.assertGreater(missing['readings_generated'], stalled['readings_generated'])
        self.assertGreaterEqual(missing['key_pool']['keys_consumed'], 1)
        state.apply({'action': 'resume_supply'})
        wait_for(lambda: state.status()['readings_delivered'] > missing['readings_delivered'])
        recovered = state.status()
        self.assertEqual(recovered['twin']['freshness'], 'CURRENT')
        self.assertNotEqual(recovered['gateway']['connection_epoch'], epoch)
        self.assertTrue(recovered['monitoring']['running'])

    def test_stop_pauses_delivery_but_clock_and_age_continue_then_start_recovers(self):
        state = self.runner()
        wait_for(lambda: state.status()['readings_delivered'] >= 1)
        stopped = state.apply({'action': 'stop_monitoring'})
        self.assertFalse(stopped['monitoring']['running'])
        self.assertEqual(stopped['gateway']['connection_state'], 'DISCONNECTED')
        wait_for(lambda: state.status()['twin']['freshness'] == 'MISSING')
        aged = state.status()
        self.assertEqual(aged['readings_generated'], stopped['readings_generated'])
        self.assertEqual(aged['readings_delivered'], stopped['readings_delivered'])
        self.assertGreater(aged['clock']['elapsed_seconds'], stopped['clock']['elapsed_seconds'])
        state.apply({'action': 'start_monitoring'})
        wait_for(lambda: state.status()['readings_delivered'] > aged['readings_delivered'])

    def test_reset_keeps_one_scheduler_and_configuration_and_close_stops_workers(self):
        state = self.runner()
        wait_for(lambda: state.status()['readings_delivered'] >= 1)
        worker = state._worker
        old_pool = state.key_pool
        reset = state.apply({'action': 'reset'})
        self.assertEqual(reset['readings_delivered'], 0)
        self.assertEqual(reset['readings_rejected'], 0)
        self.assertIsNone(reset['twin']['timestamp'])
        self.assertEqual(reset['twin']['current_threshold'], 0.15)
        self.assertEqual(reset['key_pool']['capacity'], 1)
        self.assertEqual(state._worker, worker)
        self.assertFalse(old_pool._worker.is_alive())
        wait_for(lambda: state.status()['readings_delivered'] >= 1)
        state.close()
        self.assertFalse(worker.is_alive())
        self.assertFalse(state.key_pool._worker.is_alive())
        self.assertIsNone(state._device_key)

    def test_auto_owned_actions_rejected_from_api_layer(self):
        state = self.runner()
        for action in ('generate_keys', 'start_epoch', 'end_epoch', 'send_reading', 'advance_time'):
            payload = {'action': action}
            if action == 'generate_keys':
                payload['count'] = 1
            if action == 'advance_time':
                payload['seconds'] = 1
            with self.subTest(action=action), self.assertRaises(ActionError):
                state.apply(payload)

    def test_tampering_never_updates_twin_and_scheduler_recovers(self):
        state = self.runner(epoch_duration=5)
        wait_for(lambda: state.status()['readings_delivered'] >= 1)
        def tamper(reading, key):
            envelope = encrypt_reading(reading, key)
            data = bytearray(base64.b64decode(envelope['ciphertext']))
            data[0] ^= 1
            envelope['ciphertext'] = base64.b64encode(data).decode()
            return envelope
        with state._lock:
            before = state.status()
            with patch('main.encrypt_reading', side_effect=tamper):
                # Direct tick under the scheduler lock gives deterministic tamper injection.
                state._next_reading = 0
                state._automatic_tick()
            after = state.status()
            self.assertEqual(after['readings_delivered'], before['readings_delivered'])
            self.assertEqual(after['twin']['timestamp'], before['twin']['timestamp'])
            self.assertEqual(after['readings_rejected'], before['readings_rejected'] + 1)
            self.assertEqual(after['gateway']['verification'], 'REJECTED')
        wait_for(lambda: state.status()['readings_delivered'] > before['readings_delivered'])

    def test_unexpected_worker_error_stops_visibly_and_reset_recovers(self):
        state = self.runner()
        with patch.object(state, '_automatic_tick', side_effect=RuntimeError('private-test-payload')):
            wait_for(lambda: state.status()['monitoring']['error'])
        status = state.status()
        self.assertFalse(status['monitoring']['running'])
        self.assertEqual(status['gateway']['connection_state'], 'DISCONNECTED')
        self.assertNotIn('private-test-payload', json.dumps(status))
        state.apply({'action': 'reset'})
        wait_for(lambda: state.status()['readings_delivered'] >= 1)

    def test_invalid_configuration_rejected_and_manual_clock_still_paused(self):
        for field in ('reading_interval', 'epoch_duration', 'generation_interval'):
            for value in (0, -1, math.inf, math.nan, True):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    RunnerState(automatic=True, **{field: value})
        state = RunnerState()
        self.addCleanup(state.close)
        time.sleep(0.03)
        self.assertEqual(state.status()['clock']['elapsed_seconds'], 0)
        self.assertEqual(state.status()['readings_generated'], 0)

    def test_http_automatic_flow_and_stop_start_actions(self):
        server = create_server(0, automatic=True, reading_interval=0.06,
                               generation_interval=0.03, epoch_duration=0.5, pool_capacity=1)
        thread = Thread(target=server.serve_forever)
        thread.start()
        try:
            def request(payload=None):
                connection = HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                try:
                    connection.request('GET' if payload is None else 'POST',
                        '/api/status' if payload is None else '/api/actions',
                        body=None if payload is None else json.dumps(payload),
                        headers={} if payload is None else {'Content-Type': 'application/json'})
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    return json.loads(response.read())
                finally:
                    connection.close()
            wait_for(lambda: request()['readings_delivered'] >= 1)
            self.assertFalse(request({'action': 'stop_monitoring'})['monitoring']['running'])
            self.assertTrue(request({'action': 'start_monitoring'})['monitoring']['running'])
            wait_for(lambda: request()['gateway']['connection_state'] == 'CONNECTED')
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
        self.assertFalse(server.state._worker.is_alive())


if __name__ == '__main__':
    unittest.main()
