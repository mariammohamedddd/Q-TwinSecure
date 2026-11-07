"""Independent tests using only the Python standard library."""

from dataclasses import FrozenInstanceError
import json
from threading import Thread
from time import monotonic, sleep
import unittest
from unittest.mock import patch

from qkd import QKDKeyPool


class KeyPoolTests(unittest.TestCase):
    def test_initial_state_and_empty_consumption(self):
        pool = QKDKeyPool(capacity=2, auto_generate=False)
        expected = {"supply_enabled": True, "keys_available": 0,
                    "keys_generated": 0, "keys_consumed": 0, "capacity": 2}
        self.assertEqual(pool.get_status(), expected)
        self.assertIsNone(pool.consume_key())
        self.assertEqual(pool.get_status(), expected)

    def test_capacity_and_refill(self):
        pool = QKDKeyPool(capacity=2, auto_generate=False)
        self.assertEqual(pool.generate_keys(10), 2)
        self.assertEqual(pool.generate_keys(1), 0)
        pool.consume_key()
        self.assertEqual(pool.generate_keys(10), 1)
        self.assertEqual(pool.get_status()["keys_available"], 2)
        self.assertEqual(pool.get_status()["keys_generated"], 3)
        self.assertEqual(pool.get_status()["keys_consumed"], 1)

    def test_matching_32_byte_material_and_unique_fifo_ids(self):
        pool = QKDKeyPool(capacity=3, auto_generate=False)
        pool.generate_keys(3)
        records = [pool.consume_key() for _ in range(3)]
        self.assertEqual(len({record.key_id for record in records}), 3)
        for index, record in enumerate(records, start=1):
            self.assertTrue(record.key_id.endswith(f"-{index}"))
            # Avoid printing key material even if a comparison fails.
            self.assertTrue(record.device_key == record.twin_key,
                            "endpoint key material must match")
            self.assertIsInstance(record.device_key, bytes)
            self.assertEqual(len(record.device_key), 32)
        self.assertIsNone(pool.consume_key())

    def test_full_pool_rejects_additions_without_displacing_records(self):
        with QKDKeyPool(capacity=3, auto_generate=False) as pool:
            self.assertEqual(pool.generate_keys(3), 3)
            full_status = pool.get_status()
            with patch("qkd.key_pool.secrets.token_bytes") as random:
                self.assertEqual(pool.generate_keys(100), 0)
                self.assertEqual(pool.generate_keys(1), 0)
                random.assert_not_called()
            self.assertEqual(pool.get_status(), full_status)
            records = [pool.consume_key() for _ in range(3)]
            self.assertEqual([record.key_id.rsplit("-", 1)[1] for record in records],
                             ["1", "2", "3"])
            self.assertTrue(all(record.device_key == record.twin_key for record in records))
            self.assertIsNone(pool.consume_key())

    def test_generation_uses_secrets_and_only_free_slots(self):
        pool = QKDKeyPool(capacity=2, auto_generate=False)
        with patch("qkd.key_pool.secrets.token_bytes", return_value=b"x" * 32) as random:
            self.assertEqual(pool.generate_keys(10), 2)
            pool.generate_keys(10)
            pool.generate_keys(0)
            self.assertEqual(random.call_count, 2)
            random.assert_called_with(32)

    def test_interruption_preserves_queued_and_allocated_keys(self):
        pool = QKDKeyPool(capacity=2, auto_generate=False)
        pool.generate_keys(2)
        active = pool.consume_key()
        pool.interrupt_supply()
        pool.interrupt_supply()
        with patch("qkd.key_pool.secrets.token_bytes") as random:
            self.assertEqual(pool.generate_keys(2), 0)
            random.assert_not_called()
        self.assertIsNotNone(pool.consume_key())
        self.assertIsNone(pool.consume_key())
        self.assertTrue(active.device_key == active.twin_key)
        self.assertEqual(len(active.device_key), 32)
        self.assertEqual(pool.get_status(), {
            "supply_enabled": False, "keys_available": 0,
            "keys_generated": 2, "keys_consumed": 2, "capacity": 2})

    def test_manual_mode_recovery(self):
        pool = QKDKeyPool(capacity=1, auto_generate=False)
        pool.generate_keys(1)
        previous = pool.consume_key()
        pool.interrupt_supply()
        pool.resume_supply()
        pool.resume_supply()
        self.assertIsNone(pool.consume_key())
        self.assertEqual(pool.generate_keys(1), 1)
        self.assertNotEqual(pool.consume_key().key_id, previous.key_id)
        self.assertEqual(pool.get_status()["keys_consumed"], 2)

    def test_zero_count_and_invalid_arguments(self):
        pool = QKDKeyPool(auto_generate=False)
        self.assertEqual(pool.generate_keys(0), 0)
        for value in (True, False, 1.5, "2", None):
            with self.subTest(value=value), self.assertRaises(TypeError):
                QKDKeyPool(value)
            with self.subTest(value=value), self.assertRaises(TypeError):
                pool.generate_keys(value)
        for value in (0, -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                QKDKeyPool(value)
        for interrupted in (False, True):
            if interrupted:
                pool.interrupt_supply()
            with self.assertRaises(ValueError):
                pool.generate_keys(-1)

    def test_status_is_safe_and_cannot_mutate_pool(self):
        pool = QKDKeyPool(capacity=1, auto_generate=False)
        pool.generate_keys(1)
        record = pool.consume_key()
        status = pool.get_status()
        self.assertEqual(set(status), {"supply_enabled", "keys_available",
                                      "keys_generated", "keys_consumed", "capacity"})
        self.assertTrue(all(type(value) in (bool, int) for value in status.values()))
        json.dumps(status)
        self.assertEqual(repr(record), f"KeyRecord(key_id='{record.key_id}')")
        with self.assertRaises(FrozenInstanceError):
            record.key_id = "changed"
        status["keys_available"] = 999
        self.assertEqual(pool.get_status()["keys_available"], 0)

    def test_separate_pools_and_repeated_cycles(self):
        first = QKDKeyPool(1, auto_generate=False)
        second = QKDKeyPool(1, auto_generate=False)
        first.generate_keys(1)
        second.generate_keys(1)
        self.assertNotEqual(first.consume_key().key_id, second.consume_key().key_id)
        for _ in range(20):
            first.generate_keys(1)
            record = first.consume_key()
            self.assertTrue(record.device_key == record.twin_key)
            state = first.get_status()
            self.assertEqual(state["keys_generated"],
                             state["keys_available"] + state["keys_consumed"])


class AutomaticSupplyTests(unittest.TestCase):
    def wait_for(self, predicate):
        deadline = monotonic() + 3
        while not predicate():
            if monotonic() >= deadline:
                self.fail("Automatic supply did not reach the expected state")
            sleep(0.005)

    def test_fills_and_refills_without_generation_calls(self):
        with QKDKeyPool(2, generation_interval=0.02) as pool:
            self.wait_for(lambda: pool.get_status()["keys_available"] == 2)
            sleep(0.08)
            self.assertEqual(pool.get_status()["keys_generated"], 2)
            record = pool.consume_key()
            self.assertTrue(record.device_key == record.twin_key)
            self.wait_for(lambda: pool.get_status()["keys_available"] == 2)
            self.assertEqual(pool.get_status()["keys_generated"], 3)

    def test_interruption_and_automatic_recovery(self):
        with QKDKeyPool(1, generation_interval=0.02) as pool:
            self.wait_for(lambda: pool.get_status()["keys_available"] == 1)
            pool.interrupt_supply()
            active = pool.consume_key()
            before = pool.get_status()
            sleep(0.08)
            self.assertEqual(pool.get_status(), before)
            self.assertIsNone(pool.consume_key())
            self.assertEqual(len(active.device_key), 32)
            pool.resume_supply()
            self.wait_for(lambda: pool.get_status()["keys_available"] == 1)
            self.assertNotEqual(pool.consume_key().key_id, active.key_id)

    def test_generation_waits_for_configured_interval(self):
        with QKDKeyPool(1, generation_interval=0.15) as pool:
            self.assertEqual(pool.get_status()["keys_generated"], 0)
            sleep(0.03)
            self.assertEqual(pool.get_status()["keys_generated"], 0)
            self.wait_for(lambda: pool.get_status()["keys_generated"] == 1)

    def test_close_stops_worker_while_waiting_paused_or_full(self):
        for mode in ("waiting", "paused", "full"):
            with self.subTest(mode=mode):
                pool = QKDKeyPool(1, generation_interval=0.02)
                try:
                    if mode == "paused":
                        pool.interrupt_supply()
                    elif mode == "full":
                        self.wait_for(lambda: pool.get_status()["keys_available"] == 1)
                finally:
                    pool.close()
                pool.close()
                self.assertFalse(pool._worker.is_alive())
                self.assertEqual(pool.generate_keys(1), 0)
                with self.assertRaises(RuntimeError):
                    pool.resume_supply()

    def test_concurrent_allocations_keep_ids_and_counters_consistent(self):
        with QKDKeyPool(5, generation_interval=0.005) as pool:
            self.wait_for(lambda: pool.get_status()["keys_available"] == 5)
            records = []

            def consume():
                for _ in range(10):
                    record = pool.consume_key()
                    if record is not None:
                        records.append(record)
                    sleep(0.002)

            threads = [Thread(target=consume) for _ in range(3)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(len({record.key_id for record in records}), len(records))
            self.assertTrue(all(record.device_key == record.twin_key for record in records))
            state = pool.get_status()
            self.assertEqual(state["keys_consumed"], len(records))
            self.assertEqual(state["keys_generated"],
                             state["keys_consumed"] + state["keys_available"])
            self.assertLessEqual(state["keys_available"], 5)

    def test_invalid_automatic_configuration(self):
        for interval in (0, -1, True, None, "1", float("nan"), float("inf"), 10**1000):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                QKDKeyPool(generation_interval=interval)
        with self.assertRaises(TypeError):
            QKDKeyPool(auto_generate="yes")


if __name__ == "__main__":
    unittest.main()
