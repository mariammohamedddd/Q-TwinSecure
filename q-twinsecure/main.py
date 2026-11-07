"""Local sensor-to-Twin demonstration with manual and fully automatic real-time modes."""
import argparse
from collections import deque
from datetime import datetime, timezone, timedelta
import json
import math
import time
from threading import Event, RLock, Thread, current_thread
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
from presentation import PresentationSequence

WEB = Path(__file__).resolve().parent / "web"
ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8"),
          "/gateway-panel.js": ("gateway-panel.js", "text/javascript; charset=utf-8"),
          "/key-panel.js": ("key-panel.js", "text/javascript; charset=utf-8"),
          "/sensor-panel.js": ("sensor-panel.js", "text/javascript; charset=utf-8"),
          "/sensor-panel.css": ("sensor-panel.css", "text/css; charset=utf-8"),
          "/twin-panel.js": ("twin-panel.js", "text/javascript; charset=utf-8"),
          "/twin-panel.css": ("twin-panel.css", "text/css; charset=utf-8"),
          "/twin-live.css": ("twin-live.css", "text/css; charset=utf-8"),
          "/twin": ("twin-live.html", "text/html; charset=utf-8")}
ACTIONS = ("reset", "generate_keys", "interrupt_supply", "resume_supply",
           "start_epoch", "end_epoch", "send_reading", "advance_time",
           "start_monitoring", "stop_monitoring", "replay_presentation")
MAX_STEP_SECONDS = 3600
MAX_ELAPSED_SECONDS = 86400
MAX_EVENTS = 100


class ActionError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class RunnerState:
    """Own one monitoring state and serialize only safe state."""
    def __init__(self, key_pool=None, *, auto_generate=False, automatic=False, presentation=False,
                 current_threshold=5, missing_threshold=15, reading_interval=2,
                 epoch_duration=10, pool_capacity=10, generation_interval=1, presentation_hold=4):
        # Validate before starting an optional key-supply worker.
        TwinMonitor(current_threshold, missing_threshold)
        for name, value in (("reading_interval", reading_interval),
                            ("epoch_duration", epoch_duration),
                            ("generation_interval", generation_interval),
                            ("presentation_hold", presentation_hold)):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a finite positive number")
        if type(automatic) is not bool:
            raise ValueError("automatic must be a boolean")
        if type(presentation) is not bool:
            raise ValueError("presentation must be a boolean")
        if presentation and (key_pool is not None or current_threshold <= reading_interval):
            raise ValueError("Presentation requires its own one-pair pool and a current threshold greater than the reading interval")
        self.presentation_mode = presentation
        self.presentation_hold = float(presentation_hold)
        self.automatic = automatic or presentation
        # The presentation orchestrates real generation explicitly so failure is reproducible.
        self.auto_generate = (auto_generate or self.automatic) and not presentation
        self.reading_interval = float(reading_interval)
        self.epoch_duration = float(epoch_duration)
        self.generation_interval = float(generation_interval)
        self._lock = RLock()
        self._stop = Event()
        self._worker = None
        self._closed = False
        self.current_threshold = current_threshold
        self.missing_threshold = missing_threshold
        self.key_pool = key_pool if key_pool is not None else QKDKeyPool(
            capacity=1 if presentation else pool_capacity, auto_generate=self.auto_generate,
            generation_interval=self.generation_interval)
        self._reset_components()
        if self.automatic:
            self._worker = Thread(target=self._monitor_loop, daemon=True, name="qts-monitor")
            self._worker.start()

    def _reset_components(self):
        self.gateway = GatewayStatus()
        self._device_key = None
        self._twin_key = None
        self._manual_elapsed = 0
        self._clock_started = time.monotonic()
        self._origin = datetime.now(timezone.utc)
        self.events = deque(maxlen=MAX_EVENTS)
        self.sensor = CO2SensorSimulator(values=[650, 700, 680], clock=self.now)
        self.twin = TwinMonitor(self.current_threshold, self.missing_threshold, clock=self.now)
        self.readings_generated = 0
        self.readings_delivered = 0
        self.readings_rejected = 0
        self.scenario = "READY"
        self.monitoring_running = self.automatic
        self._next_reading = 0
        self._epoch_started = None
        self.automation_error = None
        self.presentation = PresentationSequence(self, self.presentation_hold) if self.presentation_mode else None
        if self.presentation is not None:
            self.presentation.tick()

    @property
    def elapsed_seconds(self):
        if self.automatic:
            return max(0, time.monotonic() - self._clock_started)
        return self._manual_elapsed

    @elapsed_seconds.setter
    def elapsed_seconds(self, value):
        self._manual_elapsed = value

    def close(self):
        self._stop.set()
        if self._worker is not None and self._worker is not current_thread():
            self._worker.join()
        with self._lock:
            self._closed = True
            self.monitoring_running = False
            self.end_epoch()
            self.key_pool.close()

    def _monitor_loop(self):
        while not self._stop.wait(0.02):
            with self._lock:
                if self._closed or not self.monitoring_running:
                    continue
                try:
                    if self.presentation is not None:
                        self.presentation.tick()
                    else:
                        self._automatic_tick()
                except Exception:
                    # Fail visibly and stop sending; never log exception payloads or keys.
                    self.monitoring_running = False
                    self.end_epoch()
                    self.scenario = "AUTOMATION_ERROR"
                    self.automation_error = "Automatic monitoring stopped after an internal error."
                    self.record("monitoring", "failure", self.automation_error)

    def _automatic_tick(self):
        elapsed = self.elapsed_seconds
        if self._device_key is not None and elapsed - self._epoch_started >= self.epoch_duration:
            self.end_epoch()
            self.record("end_epoch", "success", "Epoch lifetime reached; requesting a fresh allocation.")
        if self._device_key is None:
            try:
                self.start_epoch()
                self.scenario = "EPOCH_ACTIVE"
                self.record("start_epoch", "success", "Epoch established automatically using one key pair.")
            except ActionError:
                if self.scenario != "WAITING_FOR_KEY":
                    self.record("start_epoch", "failure", "Waiting for a key; establishment will retry automatically.")
                self.scenario = "WAITING_FOR_KEY"
        if elapsed < self._next_reading:
            return
        # Schedule from the present rather than replaying a backlog after a delay.
        self._next_reading = elapsed + self.reading_interval
        reading = self.sensor.read()
        self.readings_generated += 1
        if self._device_key is None:
            self.record("send_reading", "unavailable", "Sensor sampled; delivery unavailable without an epoch.")
            return
        try:
            self.accept_envelope(self.protect_reading(reading))
        except (InvalidTag, ValueError):
            self.record("send_reading", "rejected", "Reading rejected; previous Twin observation retained.")
            return
        self.scenario = ("DELIVERING" if self.key_pool.get_status()["supply_enabled"]
                         else "DELIVERING_WITH_SUPPLY_INTERRUPTED")
        self.record("send_reading", "success", "Scheduled reading authenticated and accepted by the Twin.")

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
        self._epoch_started = self.elapsed_seconds

    def end_epoch(self):
        self.gateway.end_epoch()
        self._device_key = self._twin_key = None
        self._epoch_started = None

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
        try:
            reading = self.verify_reading(envelope)
            self.twin.update_observation(reading, received_at=self.now())
        except (InvalidTag, ValueError):
            self.readings_rejected += 1
            raise
        self.readings_delivered += 1
        return reading

    def record(self, action, outcome, message):
        self.events.append({"timestamp": self.now().isoformat(),
                            "elapsed_seconds": self.elapsed_seconds, "action": action,
                            "outcome": outcome, "message": message})

    def status(self):
        with self._lock:
            return self._status()

    def _status(self):
        connected = self._device_key is not None
        available = {action: {"enabled": True, "reason": None} for action in ACTIONS}
        for action in ("end_epoch", "send_reading"):
            available[action] = {"enabled": connected,
                                 "reason": None if connected else "No active connection epoch."}
        available["start_epoch"] = {"enabled": not connected,
                                    "reason": "End the active epoch first." if connected else None}
        if self.automatic:
            for action in ("generate_keys", "start_epoch", "end_epoch", "send_reading", "advance_time"):
                available[action] = {"enabled": False, "reason": "Managed by automatic monitoring."}
        available["start_monitoring"] = {
            "enabled": self.automatic and not self.monitoring_running and not self.automation_error,
            "reason": None if self.automatic else "Start the application in automatic mode."}
        available["stop_monitoring"] = {
            "enabled": self.automatic and self.monitoring_running,
            "reason": None if self.automatic else "Start the application in automatic mode."}
        available["replay_presentation"] = {"enabled": self.presentation_mode,
                                             "reason": None if self.presentation_mode else "Run with --presentation."}
        if self.presentation_mode:
            for action in ACTIONS:
                if action not in ("reset", "replay_presentation"):
                    available[action] = {"enabled": False, "reason": "The guided presentation owns this action."}
        return {"api_version": 1, "phase": 3, "scenario": self.scenario,
                "integration_ready": True, "key_pool": self.key_pool.get_status(),
                "sensor": self.sensor.get_status(), "gateway": self.gateway.get_status(),
                "twin": self.twin.get_status(self.now()),
                "readings_generated": self.readings_generated,
                "readings_delivered": self.readings_delivered,
                "readings_rejected": self.readings_rejected,
                "key_supply_mode": "automatic" if self.auto_generate else "manual",
                "monitoring": {"mode": "automatic" if self.automatic else "manual",
                               "running": self.monitoring_running,
                               "reading_interval_seconds": self.reading_interval,
                               "epoch_duration_seconds": self.epoch_duration,
                               "epoch_remaining_seconds": None if self._epoch_started is None else
                                   max(0, self.epoch_duration - (self.elapsed_seconds - self._epoch_started)),
                               "error": self.automation_error},
                "presentation": self.presentation.status() if self.presentation is not None else None,
                "events": list(self.events),
                "clock": {"elapsed_seconds": self.elapsed_seconds,
                          "timestamp": self.now().isoformat(), "mode": "realtime" if self.automatic else "manual",
                          "max_step_seconds": MAX_STEP_SECONDS,
                          "max_elapsed_seconds": MAX_ELAPSED_SECONDS},
                "actions": available}

    def apply(self, payload):
        with self._lock:
            return self._apply(payload)

    def _apply(self, payload):
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
        if self._closed:
            raise ActionError("Runner is closed.", 409)
        if action == "replay_presentation" and not self.presentation_mode:
            raise ActionError("Run with --presentation to replay scenarios.", 409)
        if self.presentation_mode and action not in ("reset", "replay_presentation"):
            raise ActionError("The guided presentation owns this action; use Replay to start again.", 409)
        if self.automatic and action in ("generate_keys", "start_epoch", "end_epoch", "send_reading", "advance_time"):
            raise ActionError("This action is managed by automatic monitoring.", 409)
        if action in ("start_monitoring", "stop_monitoring"):
            if not self.automatic or self.automation_error:
                raise ActionError("Automatic monitoring is unavailable; reset or restart in automatic mode.", 409)
            self.monitoring_running = action == "start_monitoring"
            if self.monitoring_running:
                self._next_reading = self.elapsed_seconds
                self.scenario = "STARTING"
            else:
                self.end_epoch()
                self.scenario = "MONITORING_STOPPED"
            self.record(action, "success", "Monitoring started." if self.monitoring_running else
                        "Monitoring stopped; real-time freshness continues to age.")
            return self.status()
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
            if action in ("reset", "replay_presentation"):
                capacity = self.key_pool.get_status()["capacity"]
                self.end_epoch()
                self.key_pool.close()
                self.key_pool = QKDKeyPool(capacity=capacity, auto_generate=self.auto_generate,
                                           generation_interval=self.generation_interval)
                self._reset_components()
                message = ("Presentation restarted; first capacity checkpoint is ready."
                           if self.presentation_mode else
                           "All demo components reset; pool empty, no epoch or observation.")
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
                message = ("Supply resumed; automatic replenishment and connection retry continue."
                           if self.auto_generate else "Supply resumed; generate keys to replenish the manual pool.")
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
            self.record(action, "rejected", message)
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


class DashboardServer(HTTPServer):
    def server_close(self):
        if hasattr(self, "state"):
            self.state.close()
        super().server_close()


def create_server(port=8000, *, auto_generate=False, automatic=False, presentation=False,
                  current_threshold=5, missing_threshold=15, reading_interval=2,
                  epoch_duration=10, pool_capacity=10, generation_interval=1, presentation_hold=4):
    state = RunnerState(auto_generate=auto_generate, automatic=automatic, presentation=presentation,
                        current_threshold=current_threshold, missing_threshold=missing_threshold,
                        reading_interval=reading_interval, epoch_duration=epoch_duration,
                        pool_capacity=pool_capacity, generation_interval=generation_interval,
                        presentation_hold=presentation_hold)
    try:
        server = DashboardServer(("127.0.0.1", port), DashboardHandler)
    except OSError:
        state.close()
        raise
    server.state = state
    return server

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument('--automatic', '--automatic-key-supply', dest='automatic', action='store_true',
                        help='Run real-time keys, scheduled readings, epoch renewal and recovery automatically.')
    parser.add_argument('--presentation', action='store_true',
                        help='Walk through real normal, tampering, interruption, stale-data and recovery scenarios.')
    parser.add_argument('--presentation-hold', type=float, default=4,
                        help='Display pacing for pool, delivery, interruption and recovery checkpoints.')
    parser.add_argument('--reading-interval', type=float, default=2)
    parser.add_argument('--epoch-duration', type=float, default=10)
    parser.add_argument('--pool-capacity', type=int, default=None)
    parser.add_argument('--key-interval', type=float, default=1)
    parser.add_argument('--current-threshold', type=float, default=5)
    parser.add_argument('--missing-threshold', type=float, default=15)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        server = create_server(args.port, automatic=args.automatic, presentation=args.presentation,
                               presentation_hold=args.presentation_hold,
                               reading_interval=args.reading_interval,
                               epoch_duration=args.epoch_duration,
                               pool_capacity=args.pool_capacity if args.pool_capacity is not None else
                                   (3 if args.automatic else 10),
                               generation_interval=args.key_interval,
                               current_threshold=args.current_threshold,
                               missing_threshold=args.missing_threshold)
    except (ValueError, TypeError) as error:
        parser.error(str(error))
    with server:
        print(f"Q-TwinSecure integrated demo: http://127.0.0.1:{server.server_port}")
        print("Guided scenario presentation started." if args.presentation else
              "Automatic real-time monitoring started." if args.automatic else
              "Manual demonstration: use the experiment controls.")
        print("Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Dashboard stopped.")


if __name__ == "__main__":
    main()
