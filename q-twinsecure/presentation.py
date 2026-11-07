"""Presenter-paced real-component scenarios; no fabricated readings or status."""
import base64
from uuid import uuid4

from cryptography.exceptions import InvalidTag


STEPS = (
    ("POOL_FULL", "Bounded key supply", "One matching pair fills the pool. Additional generation is refused at capacity."),
    ("NORMAL", "Normal protected delivery", "Multiple sensor readings reach the Twin using one epoch allocation. Freshness stays CURRENT."),
    ("TAMPER_REJECTED", "Tampered message rejected", "The runner modifies a real encrypted message. Authentication rejects it; the accepted Twin observation is retained."),
    ("INTERRUPTED_ACTIVE", "Supply interrupted · epoch survives", "New generation is paused. The established epoch continues delivering readings without consuming another pair."),
    ("NO_KEY", "New epoch cannot start", "The previous epoch is explicitly ended. The empty pool prevents a replacement; delivery stops."),
    ("DELAYED", "The Twin becomes DELAYED", "Real time keeps passing without delivery. The last accepted observation remains visible as its age increases."),
    ("MISSING", "The Twin becomes MISSING", "Observation age has crossed the missing threshold. The last value is retained, not replaced by an invented reading."),
    ("RECOVERY", "Supply and delivery recover", "Supply resumes, a fresh pair establishes a new epoch, and a verified reading returns the Twin to CURRENT."),
    ("COMPLETE", "Demonstration complete", "All scenario checks passed. Recovered readings continue; replay whenever you are ready."),
)


class PresentationSequence:
    def __init__(self, runner, hold_seconds):
        self.runner = runner
        self.hold = hold_seconds
        self.run_id = str(uuid4())
        self.index = 0
        self.entered_at = runner.elapsed_seconds
        self.initialized = False
        self.results = []
        self.next_sample = 0
        self.original_epoch = None
        self.interrupted_count = 0

    def _check(self, label, condition):
        if not condition:
            raise RuntimeError("Presentation scenario check failed")
        self.results.append({"label": label, "passed": True,
                             "elapsed_seconds": self.runner.elapsed_seconds})

    def _sample(self):
        runner = self.runner
        reading = runner.sensor.read()
        runner.readings_generated += 1
        runner.accept_envelope(runner.protect_reading(reading))
        self.next_sample = runner.elapsed_seconds + runner.reading_interval
        runner.record("presentation", "success", "Scenario reading authenticated and accepted by the Twin.")

    def _enter(self, index):
        self.index = index
        runner = self.runner
        self.entered_at = runner.elapsed_seconds
        code, title, _ = STEPS[index]
        runner.scenario = code
        runner.record("presentation", "step", title)
        if code == "POOL_FULL":
            runner.key_pool.generate_keys(1)
            before = runner.key_pool.get_status()
            added = runner.key_pool.generate_keys(1)
            self._check("Capacity enforced without replacing stored keys",
                        before["keys_available"] == before["capacity"] == 1 and added == 0
                        and runner.key_pool.get_status() == before)
        elif code == "NORMAL":
            runner.start_epoch()
            self.original_epoch = runner.gateway.get_status()["connection_epoch"]
            self._sample()
        elif code == "TAMPER_REJECTED":
            # Refresh once, then hold REJECTED visibly without replacing it with a valid result.
            self._sample()
            before = runner.twin.get_status()
            delivered = runner.readings_delivered
            reading = runner.sensor.read()
            runner.readings_generated += 1
            envelope = runner.protect_reading(reading)
            corrupted = bytearray(base64.b64decode(envelope["ciphertext"]))
            corrupted[0] ^= 1
            envelope["ciphertext"] = base64.b64encode(corrupted).decode()
            rejected = False
            try:
                runner.accept_envelope(envelope)
            except InvalidTag:
                rejected = True
            after = runner.twin.get_status()
            self._check("Tampering rejected; Twin value and delivery count unchanged",
                        rejected and runner.readings_delivered == delivered
                        and before["timestamp"] == after["timestamp"]
                        and before["value_ppm"] == after["value_ppm"]
                        and runner.gateway.get_status()["verification"] == "REJECTED")
            runner.record("presentation", "rejected", "Modified ciphertext rejected; accepted observation retained.")
        elif code == "INTERRUPTED_ACTIVE":
            runner.key_pool.interrupt_supply()
            self.interrupted_count = runner.readings_delivered
            self._sample()
        elif code == "NO_KEY":
            runner.end_epoch()
            failed = False
            try:
                runner.start_epoch()
            except ValueError:
                failed = True
            self._check("Empty pool prevents a new epoch after explicit closure",
                        failed and runner._device_key is None
                        and runner.key_pool.get_status()["keys_available"] == 0)
            self.blocked_delivery_count = runner.readings_delivered
            self.blocked_observation = runner.twin.get_status()["timestamp"]
            runner.record("start_epoch", "failure", "Expected scenario: no key available for a new epoch.")
        elif code == "DELAYED":
            self._check("Delivery gap produces DELAYED from real observation age",
                        runner.twin.get_freshness() == "DELAYED"
                        and runner.readings_delivered == self.blocked_delivery_count
                        and runner.twin.get_status()["timestamp"] == self.blocked_observation)
        elif code == "MISSING":
            self._check("Delivery gap produces MISSING without changing the last observation",
                        runner.twin.get_freshness() == "MISSING"
                        and runner.readings_delivered == self.blocked_delivery_count
                        and runner.twin.get_status()["timestamp"] == self.blocked_observation)
        elif code == "RECOVERY":
            runner.key_pool.resume_supply()
            runner.key_pool.generate_keys(1)
            runner.start_epoch()
            self._sample()
            self._check("Fresh allocation restores delivery and CURRENT freshness",
                        runner.twin.get_freshness() == "CURRENT"
                        and runner.readings_delivered > self.blocked_delivery_count
                        and runner.gateway.get_status()["connection_epoch"] != self.original_epoch)
        elif code == "COMPLETE":
            self._check("Complete real-component presentation sequence passed", True)

    def tick(self):
        runner = self.runner
        if not self.initialized:
            self.initialized = True
            self._enter(0)
            return
        code = STEPS[self.index][0]
        elapsed = runner.elapsed_seconds - self.entered_at
        if code in ("NORMAL", "INTERRUPTED_ACTIVE", "RECOVERY", "COMPLETE"):
            if runner.elapsed_seconds >= self.next_sample:
                self._sample()
        if code == "POOL_FULL" and elapsed >= self.hold:
            self._enter(1)
        elif code == "NORMAL" and elapsed >= max(self.hold * 2, runner.reading_interval * 2):
            self._check("Multiple readings share exactly one epoch key allocation",
                        runner.readings_delivered >= 2
                        and runner.key_pool.get_status()["keys_consumed"] == 1)
            self._enter(2)
        elif code == "TAMPER_REJECTED" and elapsed >= min(self.hold, runner.current_threshold * 0.8):
            self._enter(3)
        elif code == "INTERRUPTED_ACTIVE" and elapsed >= max(self.hold * 2, runner.reading_interval * 2):
            self._check("Interrupted supply preserves the active epoch and repeated delivery",
                        runner.readings_delivered > self.interrupted_count
                        and runner.gateway.get_status()["connection_epoch"] == self.original_epoch
                        and runner.key_pool.get_status()["keys_consumed"] == 1
                        and runner.key_pool.generate_keys(1) == 0)
            self._enter(4)
        elif code == "NO_KEY" and runner.twin.get_freshness() == "DELAYED":
            self._enter(5)
        elif code == "DELAYED" and runner.twin.get_freshness() == "MISSING":
            self._enter(6)
        elif code == "MISSING" and elapsed >= self.hold:
            self._enter(7)
        elif code == "RECOVERY" and elapsed >= self.hold * 2:
            self._enter(8)

    def status(self):
        code, title, description = STEPS[self.index]
        return {"run_id": self.run_id, "step": self.index + 1, "total_steps": len(STEPS),
                "stage": code, "title": title, "description": description,
                "complete": code == "COMPLETE" and not self.runner.automation_error,
                "error": self.runner.automation_error,
                "steps": [{"title": step[1], "state": "passed" if index < self.index else
                           "active" if index == self.index else "pending"}
                          for index, step in enumerate(STEPS)],
                "results": [dict(result) for result in self.results]}
