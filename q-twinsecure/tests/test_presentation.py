"""The presentation verifies real scenarios rather than animating sample statuses."""
import json
import time
import unittest
from http.client import HTTPConnection
from threading import Thread

from main import ActionError, RunnerState, create_server


class PresentationTests(unittest.TestCase):
    def runner(self):
        runner = RunnerState(presentation=True, presentation_hold=0.07,
                             reading_interval=0.03, current_threshold=0.15, missing_threshold=0.4)
        self.addCleanup(runner.close)
        return runner

    def wait_complete(self, runner):
        seen = {}
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            status = runner.status()
            presentation = status['presentation']
            self.assertIsNone(presentation['error'], status)
            seen.setdefault(presentation['stage'], status)
            if presentation['complete']:
                return seen, status
            time.sleep(0.005)
        self.fail('Presentation did not complete')

    def test_all_real_scenarios_and_observed_outcomes(self):
        runner = self.runner()
        seen, final = self.wait_complete(runner)
        self.assertEqual(set(seen), {'POOL_FULL', 'NORMAL', 'TAMPER_REJECTED',
            'INTERRUPTED_ACTIVE', 'NO_KEY', 'DELAYED', 'MISSING', 'RECOVERY', 'COMPLETE'})
        self.assertEqual(seen['POOL_FULL']['key_pool']['keys_available'], 1)
        self.assertEqual(seen['POOL_FULL']['key_pool']['keys_generated'], 1)
        self.assertEqual(seen['NORMAL']['gateway']['connection_state'], 'CONNECTED')
        self.assertEqual(seen['TAMPER_REJECTED']['gateway']['verification'], 'REJECTED')
        self.assertEqual(seen['TAMPER_REJECTED']['readings_rejected'], 1)
        interrupted = seen['INTERRUPTED_ACTIVE']
        self.assertFalse(interrupted['key_pool']['supply_enabled'])
        self.assertEqual(interrupted['gateway']['connection_state'], 'CONNECTED')
        self.assertEqual(interrupted['key_pool']['keys_consumed'], 1)
        self.assertEqual(seen['NO_KEY']['gateway']['connection_state'], 'DISCONNECTED')
        self.assertEqual(seen['NO_KEY']['key_pool']['keys_available'], 0)
        self.assertEqual(seen['DELAYED']['twin']['freshness'], 'DELAYED')
        self.assertEqual(seen['MISSING']['twin']['freshness'], 'MISSING')
        self.assertEqual(seen['MISSING']['twin']['timestamp'], seen['NO_KEY']['twin']['timestamp'])
        self.assertEqual(seen['MISSING']['readings_delivered'], seen['NO_KEY']['readings_delivered'])
        self.assertEqual(final['key_pool']['keys_consumed'], 2)
        self.assertEqual(final['twin']['freshness'], 'CURRENT')
        self.assertNotEqual(final['gateway']['connection_epoch'], seen['NORMAL']['gateway']['connection_epoch'])
        self.assertTrue(all(result['passed'] for result in final['presentation']['results']))
        encoded = json.dumps(final)
        for field in ('device_key', 'twin_key', 'ciphertext', 'nonce'):
            self.assertNotIn('"' + field + '":', encoded)
        delivered = final['readings_delivered']
        time.sleep(0.08)
        self.assertGreater(runner.status()['readings_delivered'], delivered)
        self.assertEqual(runner.status()['presentation']['stage'], 'COMPLETE')

    def test_replay_resets_results_observations_and_reuses_one_worker(self):
        runner = self.runner()
        _, final = self.wait_complete(runner)
        worker = runner._worker
        replay = runner.apply({'action': 'replay_presentation'})
        self.assertNotEqual(replay['presentation']['run_id'], final['presentation']['run_id'])
        self.assertEqual(replay['presentation']['stage'], 'POOL_FULL')
        self.assertEqual(len(replay['presentation']['results']), 1)  # New run's capacity check.
        self.assertEqual(replay['readings_delivered'], 0)
        self.assertEqual(replay['readings_rejected'], 0)
        self.assertIsNone(replay['twin']['timestamp'])
        self.assertEqual(worker, runner._worker)
        self.wait_complete(runner)

    def test_sequence_owns_individual_controls_and_config_is_validated(self):
        runner = self.runner()
        for action in ('stop_monitoring', 'interrupt_supply', 'resume_supply', 'start_monitoring'):
            with self.subTest(action=action), self.assertRaises(ActionError):
                runner.apply({'action': action})
            self.assertFalse(runner.status()['actions'][action]['enabled'])
        self.assertTrue(runner.status()['actions']['replay_presentation']['enabled'])
        with self.assertRaises(ValueError):
            RunnerState(presentation=True, current_threshold=1, reading_interval=2)
        manual = RunnerState()
        self.addCleanup(manual.close)
        with self.assertRaises(ActionError):
            manual.apply({'action': 'replay_presentation'})

    def test_http_presentation_is_real_background_state_and_replays(self):
        server = create_server(0, presentation=True, presentation_hold=0.1,
                               reading_interval=0.03, current_threshold=0.15, missing_threshold=0.4)
        thread = Thread(target=server.serve_forever)
        thread.start()
        try:
            time.sleep(0.22)  # The sequence progresses without requests.
            connection = HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            connection.request('GET', '/api/status')
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            status = json.loads(response.read())
            connection.close()
            self.assertGreater(status['presentation']['step'], 1)
            self.assertGreater(status['readings_delivered'], 0)
            connection = HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            connection.request('POST', '/api/actions', json.dumps({'action': 'replay_presentation'}),
                               {'Content-Type': 'application/json'})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            replay = json.loads(response.read())
            connection.close()
            self.assertNotEqual(replay['presentation']['run_id'], status['presentation']['run_id'])
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
        self.assertFalse(server.state._worker.is_alive())


if __name__ == '__main__':
    unittest.main()
