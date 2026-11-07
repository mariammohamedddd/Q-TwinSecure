"""Phase 2 local control API with sensor integration; protected delivery pending."""
import argparse
from collections import deque
from datetime import datetime, timedelta, timezone
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from sensor import CO2SensorSimulator

WEB = Path(__file__).resolve().parent / "web"
ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8"),
          "/gateway-panel.js": ("gateway-panel.js", "text/javascript; charset=utf-8"),
          "/sensor-panel.js": ("sensor-panel.js", "text/javascript; charset=utf-8"),
          "/sensor-panel.css": ("sensor-panel.css", "text/css; charset=utf-8")}
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
    """Single-server in-memory state. Never contains component secrets."""
    def __init__(self):
        self.elapsed_seconds = 0
        self.events = deque(maxlen=MAX_EVENTS)
        self._reset_sensor()

    def _reset_sensor(self):
        self.clock_origin = datetime.now(timezone.utc)
        self.sensor = CO2SensorSimulator(
            seed=42, clock=lambda: self.clock_origin + timedelta(seconds=self.elapsed_seconds))
        self.readings_generated = 0

    def record(self, action, outcome, message):
        self.events.append({"timestamp": datetime.now(timezone.utc).isoformat(),
                            "elapsed_seconds": self.elapsed_seconds, "action": action,
                            "outcome": outcome, "message": message})

    def status(self):
        available = {action: {"enabled": action in ("reset", "advance_time"),
                     "reason": None if action in ("reset", "advance_time") else
                     "Component integration pending; action unavailable in Phase 2."}
                     for action in ACTIONS}
        return {"api_version": 1, "phase": 2, "scenario": "NOT_STARTED",
                "integration_ready": False, "key_pool": None, "sensor": self.sensor.get_status(),
                "gateway": None, "twin": None, "readings_generated": self.readings_generated,
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
        if action not in ("reset", "advance_time"):
            message = "Component integration pending; action unavailable in Phase 2."
            self.record(action, "unavailable", message)
            raise ActionError(message, 409)
        if action == "reset":
            self.elapsed_seconds = 0
            self.events.clear()
            self._reset_sensor()
            self.record(action, "success", "Runner and sensor reset; protected delivery remains unavailable.")
        else:
            self.elapsed_seconds += payload["seconds"]
            self.sensor.read()
            self.readings_generated += 1
            self.record(action, "success", "Clock advanced and one sensor reading generated; not delivered.")
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

    def reject_request(self, status, payload):
        """Drain a bounded rejected body so Windows can receive the HTTP error."""
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 0:
                self.connection.settimeout(3)
                self.rfile.read(min(length, 4097))
        except (ValueError, OSError):
            # Invalid/incomplete bodies still receive the original rejection.
            pass
        self.json_response(status, payload)

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
        if urlsplit(self.path).path != "/api/actions":
            self.reject_request(404, {"error": "Not found"})
            return
        expected_origin = f"http://127.0.0.1:{self.server.server_port}"
        origin = self.headers.get("Origin")
        if origin is not None and origin != expected_origin:
            self.reject_request(403, {"error": "Use the local dashboard origin."})
            return
        if self.headers.get_content_type() != "application/json":
            self.reject_request(415, {"error": "Content-Type must be application/json."})
            return
        if self.headers.get("Transfer-Encoding") is not None:
            self.reject_request(400, {"error": "Transfer encoding is unsupported."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= 4096:
                self.reject_request(413, {"error": "Request body must be between 1 and 4096 bytes.",
                                          "status": self.server.state.status()})
                return
            self.connection.settimeout(3)
            raw = self.rfile.read(length)
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
