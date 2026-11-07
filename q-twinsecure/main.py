"""Integrated local sensor-to-Twin demonstration with presenter-controlled time."""
import argparse
from collections import deque
from datetime import datetime, timezone, timedelta
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from gateway.crypto import encrypt_reading
from gateway.status import GatewayStatus
from cryptography.exceptions import InvalidTag
from qkd import QKDKeyPool, KeyRecord
from sensor import CO2SensorSimulator
from digital_twin import TwinMonitor

WEB = Path(__file__).resolve().parent / "web"
ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8"),
          "/gateway-panel.js": ("gateway-panel.js", "text/javascript; charset=utf-8"),
          "/key-panel.js": ("key-panel.js", "text/javascript; charset=utf-8"),
          "/sensor-panel.js": ("sensor-panel.js", "text/javascript; charset=utf-8"),
          "/sensor-panel.css": ("sensor-panel.css", "text/css; charset=utf-8"),
          "/twin-panel.js": ("twin-panel.js", "text/javascript; charset=utf-8")}
ACTIONS = ("reset", "generate_keys", "interrupt_supply", "resume_supply",
           "start_epoch", "end_epoch", "send_reading", "advance_time")
MAX_STEP_SECONDS = 3600
MAX_ELAPSED_SECONDS = 86400
MAX_EVENTS = 100


class ActionError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class RunnerState:
    """Own one deterministic demonstration and serialize only safe state."""
    def __init__(self, key_pool=None):
        self.key_pool = key_pool if key_pool is not None else QKDKeyPool(auto_generate=False)
        self.gateway = GatewayStatus()
        self._device_key = None
        self._twin_key = None
        self.elapsed_seconds = 0
        self._origin = datetime.now(timezone.utc)
        self.events = deque(maxlen=MAX_EVENTS)
        self.sensor = CO2SensorSimulator(values=[650, 700, 680], clock=self.now)
        self.twin = TwinMonitor(clock=self.now)
        self.readings_generated = 0
        self.readings_delivered = 0
        self.scenario = "READY"

    def now(self):
        return self._origin + timedelta(seconds=self.elapsed_seconds)

    def start_epoch(self):
        if self._device_key is not None:
            raise ActionError("End the active epoch before starting another.", 409)
        record = self.key_pool.consume_key()
        if record is None:
            raise ActionError("No key available for a new epoch.", 409)
        if (not isinstance(record, KeyRecord) or not record.key_id or
                not isinstance(record.device_key, bytes) or len(record.device_key) != 32 or
                not isinstance(record.twin_key, bytes) or record.device_key != record.twin_key):
            raise ActionError("Key provider returned an invalid matching key pair.", 409)
        self.gateway.start_epoch(str(uuid4()))
        self._device_key, self._twin_key = record.device_key, record.twin_key

    def end_epoch(self):
        self.gateway.end_epoch()
        self._device_key = self._twin_key = None

    def protect_reading(self, reading):
        if self._device_key is None:
            raise ActionError("No active connection epoch.", 409)
        return encrypt_reading(reading, self._device_key)

    def verify_reading(self, envelope):
        if self._twin_key is None:
            raise ActionError("No active connection epoch.", 409)
        return self.gateway.verify_reading(envelope, self._twin_key)

    def accept_envelope(self, envelope):
        """Authentication and Twin acceptance must both succeed before counting delivery."""
        reading = self.verify_reading(envelope)
        self.twin.update_observation(reading, received_at=self.now())
        self.readings_delivered += 1
        return reading

    def record(self, action, outcome, message):
        self.events.append({"timestamp": self.now().isoformat(),
                            "elapsed_seconds": self.elapsed_seconds, "action": action,
                            "outcome": outcome, "message": message})

    def status(self):
        connected = self._device_key is not None
        available = {action: {"enabled": True, "reason": None} for action in ACTIONS}
        for action in ("end_epoch", "send_reading"):
            available[action] = {"enabled": connected,
                                 "reason": None if connected else "No active connection epoch."}
        available["start_epoch"] = {"enabled": not connected,
                                    "reason": "End the active epoch first." if connected else None}
        return {"api_version": 1, "phase": 3, "scenario": self.scenario,
                "integration_ready": True, "key_pool": self.key_pool.get_status(),
                "sensor": self.sensor.get_status(), "gateway": self.gateway.get_status(),
                "twin": self.twin.get_status(self.now()),
                "readings_generated": self.readings_generated,
                "readings_delivered": self.readings_delivered, "events": list(self.events),
                "clock": {"elapsed_seconds": self.elapsed_seconds,
                          "timestamp": self.now().isoformat(), "mode": "manual",
                          "max_step_seconds": MAX_STEP_SECONDS,
                          "max_elapsed_seconds": MAX_ELAPSED_SECONDS},
                "actions": available}

    def apply(self, payload):
        if not isinstance(payload, dict) or not isinstance(payload.get("action"), str):
            raise ActionError("A JSON object with a string action is required.")
        action = payload["action"]
        if action not in ACTIONS:
            raise ActionError("Unknown action.")
        fields = {"action"}
        if action == "advance_time":
            fields.add("seconds")
        if action == "generate_keys":
            fields.add("count")
        if set(payload) != fields:
            raise ActionError("Missing or unexpected action fields.")
        if action == "advance_time":
            seconds = payload["seconds"]
            if type(seconds) is not int or not 1 <= seconds <= MAX_STEP_SECONDS:
                raise ActionError("seconds must be an integer from 1 to 3600.")
            if self.elapsed_seconds + seconds > MAX_ELAPSED_SECONDS:
                raise ActionError("Clock limit of 86400 seconds reached; reset to restart.")
        if action == "generate_keys":
            count = payload["count"]
            if type(count) is not int or not 1 <= count <= 100:
                raise ActionError("count must be an integer from 1 to 100.")
        try:
            if action == "reset":
                capacity = self.key_pool.get_status()["capacity"]
                self.end_epoch()
                self.key_pool.close()
                self.__init__(QKDKeyPool(capacity=capacity, auto_generate=False))
                message = "All demo components reset; pool empty, no epoch or observation."
            elif action == "generate_keys":
                added = self.key_pool.generate_keys(count)
                if added == 0:
                    raise ActionError("No keys generated: supply interrupted or pool full.", 409)
                message = f"Generated {added} matching key pairs."
            elif action == "interrupt_supply":
                self.key_pool.interrupt_supply()
                self.scenario = "SUPPLY_INTERRUPTED"
                message = "Supply interrupted; active epoch and buffered keys remain usable."
            elif action == "resume_supply":
                self.key_pool.resume_supply()
                self.scenario = "SUPPLY_AVAILABLE"
                message = "Supply resumed; generate keys to replenish the manual pool."
            elif action == "start_epoch":
                self.start_epoch()
                self.scenario = "EPOCH_ACTIVE"
                message = "Connection epoch started using one matching key pair."
            elif action == "end_epoch":
                if self._device_key is None:
                    raise ActionError("No active connection epoch.", 409)
                self.end_epoch()
                self.scenario = "EPOCH_ENDED"
                message = "Connection epoch ended."
            elif action == "send_reading":
                if self._device_key is None:
                    raise ActionError("No active connection epoch.", 409)
                reading = self.sensor.read()
                self.readings_generated += 1
                self.accept_envelope(self.protect_reading(reading))
                self.scenario = ("DELIVERING" if self.key_pool.get_status()["supply_enabled"]
                                 else "DELIVERING_WITH_SUPPLY_INTERRUPTED")
                message = "Reading authenticated and accepted by the Twin."
            else:
                self.elapsed_seconds += seconds
                message = "Experiment clock advanced; Twin freshness recalculated."
        except ActionError as error:
            self.record(action, "failure", str(error))
            raise
        except (InvalidTag, ValueError):
            message = "Reading rejected; Twin observation and delivered count unchanged."
            self.record(action, "failure", message)
            raise ActionError(message, 409) from None
        self.record(action, "success", message)
        return self.status()

class DashboardHandler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def json_response(self, status, payload):
        self.respond(status, json.dumps(payload, allow_nan=False).encode())

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/status":
            self.json_response(200, self.server.state.status())
        elif path in ASSETS:
            name, content_type = ASSETS[path]
            self.respond(200, (WEB / name).read_bytes(), content_type)
        else:
            self.json_response(404, {"error": "Not found"})

    def do_POST(self):
        self.close_connection = True
        # Read small requests before rejecting them: closing with unread bytes can
        # reset the socket on Windows and hide the JSON error from the client.
        self.connection.settimeout(3)
        try:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise ActionError("Invalid Content-Length.") from None
            raw = self.rfile.read(length) if 0 < length <= 8192 else b""
            if urlsplit(self.path).path != "/api/actions":
                self.json_response(404, {"error": "Not found"})
                return
            expected_origin = f"http://127.0.0.1:{self.server.server_port}"
            origin = self.headers.get("Origin")
            if origin is not None and origin != expected_origin:
                raise ActionError("Use the local dashboard origin.", 403)
            if self.headers.get_content_type() != "application/json":
                raise ActionError("Content-Type must be application/json.", 415)
            if self.headers.get("Transfer-Encoding") is not None:
                raise ActionError("Transfer encoding is unsupported.")
            if not 1 <= length <= 4096:
                raise ActionError("Request body must be between 1 and 4096 bytes.", 413)
            if len(raw) != length:
                raise ActionError("Incomplete request body.")
            try:
                payload = json.loads(raw)
            except (ValueError, UnicodeError):
                raise ActionError("Invalid JSON body.") from None
            self.json_response(200, self.server.state.apply(payload))
        except ActionError as error:
            self.json_response(error.status, {"error": str(error), "status": self.server.state.status()})
        except TimeoutError:
            self.json_response(408, {"error": "Request body timed out."})

    def log_message(self, format, *args):
        # Do not log untrusted request data or future payloads.
        pass


def create_server(port=8000):
    server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    server.state = RunnerState()
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    with create_server(args.port) as server:
        print(f"Q-TwinSecure integrated demo: http://127.0.0.1:{server.server_port}")
        print("Manual clock and key generation. Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Dashboard stopped.")
        finally:
            server.state.end_epoch()
            server.state.key_pool.close()


if __name__ == "__main__":
    main()
