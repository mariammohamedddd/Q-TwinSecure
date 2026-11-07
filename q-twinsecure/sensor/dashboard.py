"""Standalone sensor panel preview, independent of the shared experiment runner."""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import time

from .co2_simulator import CO2SensorSimulator


WEB = Path(__file__).resolve().parents[1] / "web"
ASSETS = {
    "/": ("sensor-preview.html", "text/html"),
    "/sensor-panel.js": ("sensor-panel.js", "text/javascript"),
    "/sensor-panel.css": ("sensor-panel.css", "text/css"),
}


def make_handler(sensor: CO2SensorSimulator):
    """Poll at most one new sample per two seconds; static routes are allowlisted."""
    last_sample = None

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal last_sample
            path = self.path.split("?", 1)[0]
            if path == "/api/status":
                now = time.monotonic()
                if last_sample is None or now - last_sample >= 2:
                    sensor.read()
                    last_sample = now
                body = json.dumps({"sensor": sensor.get_status()}).encode()
                content_type = "application/json"
            elif path in ASSETS:
                filename, content_type = ASSETS[path]
                body = (WEB / filename).read_bytes()
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = HTTPServer(("127.0.0.1", args.port), make_handler(CO2SensorSimulator(seed=42)))
    print(f"Sensor dashboard: http://127.0.0.1:{server.server_port}", flush=True)
    print("Standalone software sensor preview. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
