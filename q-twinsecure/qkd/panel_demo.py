"""Independent local key-panel preview, not the shared integration runner."""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path

from .key_pool import QKDKeyPool


def create_server(port: int = 8765, capacity: int = 3,
                  generation_interval: float = 1.0) -> HTTPServer:
    """Create a loopback-only, single-threaded preview with a real key pool."""
    # Start the worker only after binding succeeds, so a failed bind leaks none.
    pool = QKDKeyPool(capacity, auto_generate=False)
    module_dir = Path(__file__).resolve().parent
    static_files = {
        "/": (module_dir / "panel_demo.html", "text/html; charset=utf-8"),
        "/key-panel.js": (module_dir.parent / "web/key-panel.js", "text/javascript; charset=utf-8"),
    }

    class Handler(BaseHTTPRequestHandler):
        def respond(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def json_response(self, code: int, **fields) -> None:
            self.respond(code, json.dumps(fields).encode("utf-8"), "application/json")

        def do_GET(self) -> None:
            if self.path == "/api/key-pool":
                self.json_response(200, key_pool=pool.get_status())
            elif self.path in static_files:
                path, content_type = static_files[self.path]
                self.respond(200, path.read_bytes(), content_type)
            else:
                self.json_response(404, error="Not found")

        def do_POST(self) -> None:
            # Drain bounded small requests before early rejection so Windows
            # does not reset the connection while the error response is sent.
            self.close_connection = True
            self.connection.settimeout(3)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if 0 < length <= 2048 else b""
            except (ValueError, OSError):
                self.json_response(400, error="Invalid preview action")
                return
            if self.path != "/api/key-pool/actions":
                self.json_response(404, error="Not found")
                return
            expected_origin = f"http://127.0.0.1:{self.server.server_port}"
            if self.headers.get("Origin") not in (None, expected_origin):
                self.json_response(403, error="Use the local preview origin")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024:
                    raise ValueError
                data = json.loads(raw)
                if not isinstance(data, dict) or set(data) != {"action"}:
                    raise ValueError
                action = data["action"]
                if action == "consume":
                    record = pool.consume_key()
                    result = "Allocated one matching key pair." if record else "Pool empty; allocation failed."
                elif action == "interrupt":
                    pool.interrupt_supply()
                    result = "Supply interrupted; existing allocations are unaffected."
                elif action == "resume":
                    pool.resume_supply()
                    result = "Supply resumed; keys replenish automatically."
                else:
                    raise ValueError
            except (ValueError, TypeError, UnicodeDecodeError):
                self.json_response(400, error="Invalid preview action")
                return
            self.json_response(200, key_pool=pool.get_status(), result=result)

        def log_message(self, format, *args) -> None:
            # Preview output stays concise; never log requests or key records.
            pass

    class PreviewServer(HTTPServer):
        def server_close(self) -> None:
            pool.close()
            super().server_close()

    server = PreviewServer(("127.0.0.1", port), Handler)
    try:
        pool = QKDKeyPool(capacity, generation_interval=generation_interval)
    except (ValueError, TypeError):
        server.server_close()
        raise
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--capacity", type=int, default=3,
                        help="maximum number of keys in each endpoint pool (default: 3)")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="seconds between automatically generated key pairs (default: 1)")
    args = parser.parse_args()
    with create_server(args.port, capacity=args.capacity,
                       generation_interval=args.interval) as server:
        print(f"Independent key-pool panel: http://127.0.0.1:{server.server_port}", flush=True)
        print("Not the integrated dashboard. Stop with Ctrl+C.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
