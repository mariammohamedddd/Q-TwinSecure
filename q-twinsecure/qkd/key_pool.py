"""Bounded software-emulated QKD key supply using classical randomness."""

from collections import deque
from dataclasses import dataclass, field
import secrets
from threading import Condition, Thread, TIMEOUT_MAX
from uuid import uuid4


@dataclass(frozen=True)
class KeyRecord:
    """One allocation for two endpoints; secret fields are excluded from repr.

    Pass device_key and twin_key internally to the endpoints. Never serialize
    this record into API responses or logs; use QKDKeyPool.get_status() there.
    """

    key_id: str
    device_key: bytes = field(repr=False)
    twin_key: bytes = field(repr=False)


def _check_integer(value: int, name: str, minimum: int) -> None:
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


class QKDKeyPool:
    """Matching FIFO endpoint pools with automatic, rate-limited supply.

    Generate one pair per interval, allocate once per new epoch, and reuse that
    allocation for readings within the epoch. Pausing supply only prevents new
    generation: queued keys can still be allocated and previous allocations
    remain usable. Public operations are synchronized with the supply worker.
    Use as a context manager or call close() to stop the worker. Deterministic
    experiments can disable the worker with auto_generate=False.
    """

    def __init__(self, capacity: int = 10, *, generation_interval: float = 1.0,
                 auto_generate: bool = True) -> None:
        _check_integer(capacity, "capacity", 1)
        if (type(generation_interval) not in (int, float)
                or not 0 < generation_interval <= TIMEOUT_MAX):
            raise ValueError("generation_interval must be a finite positive number within the timer limit")
        if type(auto_generate) is not bool:
            raise TypeError("auto_generate must be a boolean")
        self._capacity = capacity
        self._device_pool: deque[tuple[str, bytes]] = deque()
        self._twin_pool: deque[tuple[str, bytes]] = deque()
        self._supply_enabled = True
        self._generated = 0
        self._consumed = 0
        self._pool_id = uuid4().hex
        self._condition = Condition()
        self._closed = False
        self._worker: Thread | None = None
        self._generation_interval = float(generation_interval)
        if auto_generate:
            self._worker = Thread(target=self._supply_loop, daemon=True,
                                  name="qkd-key-supply")
            self._worker.start()

    def _supply_loop(self) -> None:
        with self._condition:
            while not self._closed:
                self._condition.wait_for(lambda: self._closed or (
                    self._supply_enabled and len(self._device_pool) < self._capacity))
                if self._closed:
                    return
                # Full/paused periods earn no accumulated generation credit.
                interrupted = self._condition.wait_for(
                    lambda: self._closed or not self._supply_enabled
                    or len(self._device_pool) >= self._capacity,
                    timeout=self._generation_interval)
                if not interrupted:
                    self.generate_keys(1)

    def close(self) -> None:
        """Stop supply and join the worker; allocated and queued keys survive."""
        with self._condition:
            self._closed = True
            self._supply_enabled = False
            self._condition.notify_all()
        if self._worker is not None:
            self._worker.join()

    def __enter__(self) -> "QKDKeyPool":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def generate_keys(self, count: int) -> int:
        """Return the number added, limited by capacity; return 0 if paused."""
        _check_integer(count, "count", 0)
        with self._condition:
            if not self._supply_enabled:
                return 0
            added = min(count, self._capacity - len(self._device_pool))
            for _ in range(added):
                material = secrets.token_bytes(32)
                key_id = f"{self._pool_id}-{self._generated + 1}"
                self._device_pool.append((key_id, material))
                self._twin_pool.append((key_id, material))
                self._generated += 1
            self._condition.notify_all()
            return added

    def consume_key(self) -> KeyRecord | None:
        """Allocate and remove one matching pair, or return None when empty."""
        with self._condition:
            if not self._device_pool:
                return None
            key_id, device_key = self._device_pool.popleft()
            _, twin_key = self._twin_pool.popleft()
            self._consumed += 1
            self._condition.notify_all()
            return KeyRecord(key_id, device_key, twin_key)

    def interrupt_supply(self) -> None:
        """Stop generation without removing queued or already allocated keys."""
        with self._condition:
            self._supply_enabled = False
            self._condition.notify_all()

    def resume_supply(self) -> None:
        """Resume supply; the worker generates again after one interval."""
        with self._condition:
            if self._closed:
                raise RuntimeError("Cannot resume a closed key pool")
            self._supply_enabled = True
            self._condition.notify_all()

    def get_status(self) -> dict[str, bool | int]:
        """Return a fresh JSON-safe status dictionary containing no key bytes."""
        with self._condition:
            return {
                "supply_enabled": self._supply_enabled,
                "keys_available": len(self._device_pool),
                "keys_generated": self._generated,
                "keys_consumed": self._consumed,
                "capacity": self._capacity,
            }
