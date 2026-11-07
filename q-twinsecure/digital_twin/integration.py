"""Small runner adapter joining existing components; no component internals replaced."""

from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidTag
from digital_twin import TwinMonitor
from gateway.crypto import encrypt_reading
from gateway.status import GatewayStatus
from qkd import QKDKeyPool
from sensor import CO2SensorSimulator


class TwinPipeline:
    """Own secrets internally; expose only component status dictionaries.

    Observation time follows a paused experiment clock. Automatic key supply
    follows wall time, as specified by the key-pool owner; tests disable it.
    """

    def __init__(self, *, auto_generate=True, current_threshold=5, missing_threshold=15):
        self.auto_generate = auto_generate
        self.current_threshold = current_threshold
        self.missing_threshold = missing_threshold
        # Validate before starting a supply worker.
        TwinMonitor(current_threshold, missing_threshold)
        self.reset()

    def reset(self):
        if hasattr(self, 'pool'):
            self.pool.close()
        self.elapsed_seconds = 0
        self.anchor = datetime.now(timezone.utc)
        self.pool = QKDKeyPool(auto_generate=self.auto_generate)
        self.sensor = CO2SensorSimulator(values=[650, 675, 660], clock=self.now)
        self.gateway = GatewayStatus()
        self.twin = TwinMonitor(self.current_threshold, self.missing_threshold, clock=self.now)
        self._allocation = None
        self.generated = self.delivered = self.rejected = 0

    def now(self):
        return self.anchor + timedelta(seconds=self.elapsed_seconds)

    def close(self):
        self.pool.close()
        self._allocation = None

    def start_epoch(self):
        if self._allocation is not None:
            raise ValueError('End the active epoch before starting a new one.')
        allocation = self.pool.consume_key()
        if allocation is None:
            raise ValueError('No key available; new epoch could not be established.')
        self.gateway.start_epoch(allocation.key_id)
        self._allocation = allocation

    def end_epoch(self):
        self.gateway.end_epoch()
        self._allocation = None

    def accept_envelope(self, envelope):
        """Authenticate before validation/storage; rejection never counts as delivery."""
        if self._allocation is None:
            raise ValueError('No active epoch; reading was not delivered.')
        try:
            reading = self.gateway.verify_reading(envelope, self._allocation.twin_key)
            self.twin.update_observation(reading, received_at=self.now())
        except (InvalidTag, ValueError):
            self.rejected += 1
            raise ValueError('Reading rejected; previous Twin observation retained.') from None
        self.delivered += 1

    def send_reading(self):
        if self._allocation is None:
            raise ValueError('No active epoch; reading was not generated or delivered.')
        reading = self.sensor.read()
        self.generated += 1
        self.accept_envelope(encrypt_reading(reading, self._allocation.device_key))

    def status(self):
        return {'key_pool': self.pool.get_status(), 'sensor': self.sensor.get_status(),
                'gateway': self.gateway.get_status(), 'twin': self.twin.get_status(),
                'readings_generated': self.generated, 'readings_delivered': self.delivered,
                'readings_rejected': self.rejected}
