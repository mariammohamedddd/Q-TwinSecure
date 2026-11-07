"""Nancy's Phase 2 local control API; domain integration remains pending."""
import argparse
from collections import deque
from datetime import datetime, timezone
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from gateway.crypto import encrypt_reading
from gateway.status import GatewayStatus

WEB = Path(__file__).resolve().parent / "web"
ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8"),
          "/gateway-panel.js": ("gateway-panel.js", "text/javascript; charset=utf-8")}
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
    """Own private epoch keys; serialize only explicit safe status fields."""
    def __init__(self, key_pool=None):
        self.key_pool = key_pool
        self.gateway = GatewayStatus()
        self._device_key = None
        self._twin_key = None
        self.elapsed_seconds = 0
        self.events = deque(maxlen=MAX_EVENTS)

    def start_epoch(self):
        """Consume one matching pair, never one key per reading."""
        if self.gateway.get_status()["connection_state"] == "CONNECTED":
            raise ActionError("End the active epoch before starting another.", 409)
        if self.key_pool is None:
            raise ActionError("Key pool is not connected.", 409)
        record = self.key_pool.consume_key()
        if record is None:
            raise ActionError("No key available for a new epoch.", 409)
        # Proposed internal adapter format; never accepted from HTTP clients.
        if (not isinstance(record, dict) or
                not isinstance(record.get("key_id"), str) or not record["key_id"].strip() or
                not isinstance(record.get("device_key"), bytes) or
                len(record["device_key"]) != 32 or
                not isinstance(record.get("twin_key"), bytes) or
                record["device_key"] != record["twin_key"]):
            raise ActionError("Key provider returned an invalid matching key pair.", 409)
        self.gateway.start_epoch(str(uuid4()))
        self._device_key = record["device_key"]
        self._twin_key = record["twin_key"]

    def end_epoch(self):
        """Release runner references; Python does not guarantee memory erasure."""
        self.gateway.end_epoch()
        self._device_key = None
        self._twin_key = None

    def protect_reading(self, reading):
        """Internal device-side handoff; do not consume another pool key."""
        if self._device_key is None:
            raise ActionError("No active connection epoch.", 409)
        return encrypt_reading(reading, self._device_key)

    def verify_reading(self, envelope):
        """Return only authenticated readings; caller owns Twin acceptance."""
        if self._twin_key is None:
            raise ActionError("No active connection epoch.", 409)
        return self.gateway.verify_reading(envelope, self._twin_key)

    def record(self, action, outcome, message):
        self.events.append({"timestamp": datetime.now(timezone.utc).isoformat(),
                            "elapsed_seconds": self.elapsed_seconds, "action": action,
                            "outcome": outcome, "message": message})

    def status(self):
        available = {action: {"enabled": action in ("reset", "advance_time"),
                     "reason": None if action in ("reset", "advance_time") else
                     "Component integration pending; action unavailable in Phase 2."}
                     for action in ACTIONS}
        connected = self.gateway.get_status()["connection_state"] == "CONNECTED"
        available["start_epoch"] = {
            "enabled": self.key_pool is not None and not connected,
            "reason": "End the active epoch first." if connected else
                      "Key pool is not connected." if self.key_pool is None else None}
        available["end_epoch"] = {
            "enabled": connected, "reason": None if connected else "No active connection epoch."}
        return {"api_version": 1, "phase": 2, "scenario": "NOT_STARTED",
                "integration_ready": False, "key_pool": None, "sensor": None,
                "gateway": self.gateway.get_status(), "twin": None, "readings_generated": None,
                "readings_delivered": None, "events": list(self.events),
                "clock": {"elapsed_seconds": self.elapsed_seconds,
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
        if action in ("start_epoch", "end_epoch"):
            try:
                if action == "start_epoch":
                    self.start_epoch()
                else:
                    if self._device_key is None:
                        raise ActionError("No active connection epoch.", 409)
                    self.end_epoch()
            except ActionError as error:
                self.record(action, "unavailable", str(error))
                raise
            self.record(action, "success", "Connection epoch started." if action == "start_epoch"
                        else "Connection epoch ended.")
            return self.status()
        if action not in ("reset", "advance_time"):
            message = "Component integration pending; action unavailable in Phase 2."
            self.record(action, "unavailable", message)
            raise ActionError(message, 409)
        if action == "reset":
            self.end_epoch()
            self.elapsed_seconds = 0
            self.events.clear()
            self.record(action, "success", "Local runner state reset; components remain unavailable.")
        else:
            self.elapsed_seconds += payload["seconds"]
            self.record(action, "success", "Experiment clock advanced; no component data changed.")
        return self.status()


class DashboardHandler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
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
        print(f"Q-TwinSecure Phase 2: http://127.0.0.1:{server.server_port}")
        print("Component integration pending. Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Dashboard stopped.")


if __name__ == "__main__":
    main()
