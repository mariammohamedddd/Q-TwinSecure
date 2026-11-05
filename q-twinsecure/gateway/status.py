"""Gateway status and verification adapter for the future demo runner."""

from cryptography.exceptions import InvalidTag

from gateway.crypto import decrypt_reading


class GatewayStatus:
    """Track non-secret state; the runner owns keys and epoch lifecycle."""

    def __init__(self):
        self._epoch_id = None
        self._verification = None

    def start_epoch(self, epoch_id: str) -> None:
        if not isinstance(epoch_id, str) or not epoch_id.strip():
            raise ValueError("epoch_id must be a non-empty, non-secret string")
        if self._epoch_id is not None:
            raise ValueError("an epoch is already active")
        self._epoch_id = epoch_id
        self._verification = None

    def end_epoch(self) -> None:
        self._epoch_id = None
        self._verification = None

    def verify_reading(self, envelope: dict, key: bytes) -> dict:
        """Return an authenticated reading or raise; never forward it to the Twin."""
        if self._epoch_id is None:
            raise ValueError("no active connection epoch")
        try:
            reading = decrypt_reading(envelope, key)
        except (InvalidTag, ValueError):
            self._verification = "REJECTED"
            raise
        self._verification = "VERIFIED"
        return reading

    def get_status(self) -> dict:
        """Return a fresh JSON-compatible snapshot without key or message data."""
        return {
            "connection_state": "CONNECTED" if self._epoch_id is not None else "DISCONNECTED",
            "connection_epoch": self._epoch_id,
            "verification": self._verification,
        }
