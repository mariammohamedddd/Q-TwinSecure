import json
from http.server import HTTPServer
from threading import Thread
import unittest
from urllib.request import Request, urlopen

from digital_twin import TwinMonitor
from digital_twin.preview import make_handler


class PreviewTests(unittest.TestCase):
    def test_live_backend_updates_are_exposed(self):
        server = HTTPServer(('127.0.0.1', 0), make_handler(TwinMonitor()))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base + '/api/status') as response:
                self.assertEqual(json.load(response)['twin']['freshness'], 'MISSING')
            with urlopen(Request(base + '/sample', method='POST')) as response:
                self.assertTrue(json.load(response)['accepted'])
            with urlopen(base + '/api/status') as response:
                status = json.load(response)['twin']
                self.assertEqual(status['freshness'], 'CURRENT')
                self.assertEqual(status['value_ppm'], 650)
            for path, expected in [('/', b'Local sample data'), ('/twin-panel.js', b'mountTwinPanel')]:
                with urlopen(base + path) as response:
                    self.assertIn(expected, response.read())
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
