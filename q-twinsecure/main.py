"""Local component integration API with authenticated Digital Twin delivery."""
import argparse
from collections import deque
from datetime import datetime, timezone
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from digital_twin.integration import TwinPipeline

WEB = Path(__file__).resolve().parent / "web"
ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8"),
          "/twin": ("twin-live.html", "text/html; charset=utf-8"),
          "/twin-live.css": ("twin-live.css", "text/css; charset=utf-8"),
          "/twin-panel.css": ("twin-panel.css", "text/css; charset=utf-8"),
          "/twin-panel.js": ("twin-panel.js", "text/javascript; charset=utf-8"),
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
    """Single-server state; only safe snapshots cross the public API boundary."""
    def __init__(self, *, auto_generate=True, current_threshold=5, missing_threshold=15):
        self.pipeline = TwinPipeline(auto_generate=auto_generate,
                                     current_threshold=current_threshold,
                                     missing_threshold=missing_threshold)
        self.events = deque(maxlen=MAX_EVENTS)

    @property
    def elapsed_seconds(self):
        return self.pipeline.elapsed_seconds

    def close(self):
        self.pipeline.close()

    def record(self, action, outcome, message):
        self.events.append({"timestamp": datetime.now(timezone.utc).isoformat(),
                            "elapsed_seconds": self.elapsed_seconds, "action": action,
                            "outcome": outcome, "message": message})

    def status(self):
        components = self.pipeline.status()
        connected = components['gateway']['connection_state'] == 'CONNECTED'
        keys = components['key_pool']
        reasons = {
            'start_epoch': ('End the active epoch first.' if connected else
                            'No key available.' if not keys['keys_available'] else None),
            'end_epoch': None if connected else 'No active epoch.',
            'send_reading': None if connected else 'Start an epoch first.',
            'generate_keys': ('Supply is interrupted.' if not keys['supply_enabled'] else
                              'Key pool is full.' if keys['keys_available'] >= keys['capacity'] else None),
            'interrupt_supply': None if keys['supply_enabled'] else 'Supply already interrupted.',
            'resume_supply': None if not keys['supply_enabled'] else 'Supply already enabled.',
        }
        available = {action: {'enabled': reasons.get(action) is None,
                              'reason': reasons.get(action)} for action in ACTIONS}
        return {'api_version': 1, 'phase': 3, 'scenario': 'MANUAL',
                'integration_ready': True, **components, 'events': list(self.events),
                'clock': {'elapsed_seconds': self.elapsed_seconds,
                          'max_step_seconds': MAX_STEP_SECONDS,
                          'max_elapsed_seconds': MAX_ELAPSED_SECONDS,
                          'timestamp': self.pipeline.now().isoformat()},
                'key_supply_mode': 'automatic' if self.pipeline.auto_generate else 'manual',
                'actions': available}

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
        if action == 'reset':
            self.pipeline.reset()
            self.events.clear()
            self.record(action, 'success', 'Runner, clock and Twin reset; no observation available.')
        elif action == 'advance_time':
            self.pipeline.elapsed_seconds += payload['seconds']
            self.record(action, 'success', 'Experiment clock advanced; Twin freshness recalculated.')
        else:
            reason = self.status()['actions'][action]['reason']
            if reason:
                self.record(action, 'unavailable', reason)
                raise ActionError(reason, 409)
            try:
                if action == 'generate_keys':
                    self.pipeline.pool.generate_keys(payload['count'])
                elif action == 'interrupt_supply':
                    self.pipeline.pool.interrupt_supply()
                elif action == 'resume_supply':
                    self.pipeline.pool.resume_supply()
                elif action == 'start_epoch':
                    self.pipeline.start_epoch()
                elif action == 'end_epoch':
                    self.pipeline.end_epoch()
                elif action == 'send_reading':
                    self.pipeline.send_reading()
            except ValueError as error:
                self.record(action, 'rejected', str(error))
                raise ActionError(str(error), 409) from None
            messages = {
                'generate_keys': 'Key generation requested; safe pool counts updated.',
                'interrupt_supply': 'Supply interrupted; an existing epoch remains usable.',
                'resume_supply': 'Supply resumed; automatic generation restarts.',
                'start_epoch': 'Epoch established using one matching key allocation.',
                'end_epoch': 'Epoch ended; next connection requires another key.',
                'send_reading': 'Authenticated reading accepted by the Twin.',
            }
            self.record(action, 'success', messages[action])
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
        if urlsplit(self.path).path != "/api/actions":
            self.json_response(404, {"error": "Not found"})
            return
        expected_origin = f"http://127.0.0.1:{self.server.server_port}"
        origin = self.headers.get("Origin")
        if origin is not None and origin != expected_origin:
            self.json_response(403, {"error": "Use the local dashboard origin."})
            return
        if self.headers.get_content_type() != "application/json":
            self.json_response(415, {"error": "Content-Type must be application/json."})
            return
        if self.headers.get("Transfer-Encoding") is not None:
            self.json_response(400, {"error": "Transfer encoding is unsupported."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= 4096:
                raise ActionError("Request body must be between 1 and 4096 bytes.", 413)
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


class DashboardServer(HTTPServer):
    def server_close(self):
        if hasattr(self, 'state'):
            self.state.close()
        super().server_close()


def create_server(port=8000, *, auto_generate=True, current_threshold=5, missing_threshold=15):
    state = RunnerState(auto_generate=auto_generate, current_threshold=current_threshold,
                        missing_threshold=missing_threshold)
    try:
        server = DashboardServer(('127.0.0.1', port), DashboardHandler)
    except OSError:
        state.close()
        raise
    server.state = state
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument('--manual-key-supply', action='store_true',
                        help='Disable automatic generation for a repeatable seeded experiment.')
    parser.add_argument('--current-threshold', type=float, default=5)
    parser.add_argument('--missing-threshold', type=float, default=15)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        server = create_server(args.port, auto_generate=not args.manual_key_supply,
                               current_threshold=args.current_threshold,
                               missing_threshold=args.missing_threshold)
    except ValueError as error:
        parser.error(str(error))
    with server:
        print(f"Q-TwinSecure integrated demo: http://127.0.0.1:{server.server_port}")
        print("Real components connected. Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Dashboard stopped.")


if __name__ == "__main__":
    main()
