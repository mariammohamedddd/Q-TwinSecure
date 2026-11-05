"""Independent owner preview, NOT Nancy's integrated runner.

Run: python -m digital_twin.preview, then open http://127.0.0.1:8765.
Uses local sample readings, no sensor/gateway/key-pool integration.
"""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path

from . import TwinMonitor


PAGE = b'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Q-TwinSecure | Twin Monitor</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f7f9;color:#162b36;font:15px system-ui,sans-serif}
.topbar{background:#102d38;color:white;padding:20px max(24px,calc((100vw - 1540px)/2));display:flex;align-items:center;justify-content:space-between;gap:16px}.brand{font-size:17px;font-weight:750;letter-spacing:-.5px}.brand span{color:#72d2ba}.mode{font-size:11px;border:1px solid #48636d;border-radius:30px;padding:6px 12px;color:#d5e5e8}
main{max-width:1540px;margin:0 auto;padding:44px 24px}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:#557b7b;font-weight:700}h1{font-size:36px;letter-spacing:-1.4px;line-height:1.2;margin:12px 0}.intro{color:#607581;line-height:1.8;max-width:660px;margin-bottom:30px}.layout{display:grid;grid-template-columns:minmax(0,1fr) 250px;gap:24px;align-items:start}.aside{background:#fff;border:1px solid #e0e7ed;border-radius:20px;padding:24px}.aside h2{font-size:17px;margin:0 0 12px}.aside p,.step{font-size:13px;line-height:1.8;color:#607581}button{width:100%;border:0;background:#126f64;color:white;font:600 14px system-ui;padding:14px 16px;border-radius:10px;cursor:pointer;margin:10px 0}button:hover{background:#095b52}button:focus-visible{outline:3px solid #65bbae;outline-offset:3px}button:disabled{opacity:.55;cursor:wait}.steps{border-top:1px solid #edf1f4;margin-top:18px;padding-top:18px}.step{margin:0 0 14px}.step strong{display:block;color:#263f49}.footer{font-size:12px;color:#6c818c;margin:22px 0}.error{color:#a62e2e;font-size:13px}
@media(max-width:1250px){.layout{grid-template-columns:1fr}.aside{order:-1}main{padding:28px 18px}h1{font-size:29px}.topbar{padding:18px}.mode{font-size:10px}}

body{background:#0c253c;overflow:hidden}.topbar{position:fixed;top:0;left:0;right:0;z-index:10;background:#102d38dd;padding:17px 26px;border-bottom:1px solid #44607166;pointer-events:none}
main{margin:0;padding:0;max-width:none}.eyebrow,h1,.intro,.footer,.aside h2,.aside>p,.steps{display:none}.layout{display:block}
.aside{position:static;width:100%;padding:0 0 18px;margin:0 0 18px;background:transparent;border:0;border-bottom:1px solid #dce5e9;border-radius:0}.aside button{margin:0;padding:12px}.aside #error:not(:empty){display:block;color:#a62e2e;margin:8px 0 0}.aside #error:empty{display:none}
@media(max-width:700px){.topbar{padding:15px}.brand{font-size:15px}.mode{font-size:9px}.aside{padding:0 0 12px;margin-bottom:12px}.aside button{font-size:11px;padding:10px}}
</style>
<body>
<header class="topbar"><div class="brand">Q-Twin<span>Secure</span></div><span class="mode">LOCAL DEMO / SAMPLE DATA</span></header>
<main><div class="eyebrow">Digital Twin / Observation monitor</div>
<h1>Your factory. A clearer view.</h1>
<p class="intro">Locate the sample sensor on an illustrative 3D factory model. Read its latest measurement, timing and freshness alongside the model.</p>
<div class="layout"><div id="twin"></div>
<aside class="aside"><h2>Try the monitor</h2>
<p>Send a sample, then watch its age increase. Send another at any time to restore a fresh reading.</p>
<button id="sample">+ Send sample reading</button>
<p id="error" class="error" role="alert"></p>
<div class="steps"><div class="step"><strong>01 &nbsp; Current</strong>Up to 5 seconds old. Your data is recent.</div>
<div class="step"><strong>02 &nbsp; Delayed</strong>Over 5 and up to 15 seconds. Waiting for an update.</div>
<div class="step"><strong>03 &nbsp; Missing</strong>Over 15 seconds. The last value is kept for reference.</div></div>
</aside></div><p class="footer">Local sample data through the real Python monitor. Sensor and gateway integration is pending.</p>
</main>
<script src="/twin-panel.js"></script><script>
const panel = mountTwinPanel(document.getElementById('twin'), {fullScreen:true});
// Keep the sample action in normal flow with the information panel.
// The factory legend occupies a separate overlay and cannot be covered by it.
document.querySelector('#twin .twin-reading-details').prepend(document.querySelector('.aside'));
const button = document.getElementById('sample');
async function refresh() {
  try {
    const response = await fetch('/api/status', {cache:'no-store'});
    if (!response.ok) throw new Error('Status request failed');
    panel.update((await response.json()).twin);
  } catch (error) { panel.disconnected(); }
}
button.onclick = async () => {
  button.disabled = true;
  document.getElementById('error').textContent = '';
  try {
    const response = await fetch('/sample', {method:'POST'});
    if (!response.ok) throw new Error('Sample reading was not accepted');
    await refresh();
  } catch (error) { document.getElementById('error').textContent = error.message; }
  finally { button.disabled = false; }
};
refresh(); setInterval(refresh, 500);
</script></body></html>'''


def make_handler(monitor: TwinMonitor):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def respond(self, code, body, content_type):
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == '/':
                self.respond(200, PAGE, 'text/html; charset=utf-8')
            elif self.path == '/twin-panel.js':
                script = Path(__file__).resolve().parents[1] / 'web' / 'twin-panel.js'
                self.respond(200, script.read_bytes(), 'text/javascript; charset=utf-8')
            elif self.path == '/api/status':
                self.respond(200, json.dumps({'twin': monitor.get_status()}).encode(), 'application/json')
            else:
                self.respond(404, b'Not found', 'text/plain')

        def do_POST(self):
            if self.path != '/sample':
                self.respond(404, b'Not found', 'text/plain')
                return
            # Browser requests must originate from this same local preview.
            if self.headers.get('Origin') not in (None, f'http://{self.headers.get("Host")}'):
                self.respond(403, b'Origin rejected', 'text/plain')
                return
            from datetime import datetime, timezone
            monitor.update_observation({
                'sensor_id': 'local-preview-co2', 'value_ppm': 650.0,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })
            self.respond(200, b'{"accepted":true}', 'application/json')
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    with HTTPServer(('127.0.0.1', args.port), make_handler(TwinMonitor())) as server:
        print(f'Local Twin component preview: http://127.0.0.1:{args.port}', flush=True)
        print('Sample data only; press Ctrl+C to stop.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
