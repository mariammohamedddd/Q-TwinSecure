"""Exercise the standalone preview through real local HTTP requests."""

from http.server import HTTPServer
import json
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from sensor import CO2SensorSimulator
from sensor.dashboard import make_handler


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.sensor = CO2SensorSimulator(values=[500, 600])
        self.server = HTTPServer(("127.0.0.1", 0), make_handler(self.sensor))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_status_matches_actual_sensor_and_does_not_oversample(self):
        with urlopen(self.url + "/api/status") as response:
            first = json.load(response)
        self.assertEqual(first, {"sensor": self.sensor.get_status()})
        self.assertEqual(first["sensor"]["value_ppm"], 500)
        with urlopen(self.url + "/api/status") as response:
            self.assertEqual(json.load(response), first)

    def test_page_and_assets(self):
        for path, content_type in (("/", "text/html"), ("/sensor-panel.js", "text/javascript"),
                                   ("/sensor-panel.css", "text/css")):
            with self.subTest(path=path), urlopen(self.url + path) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(content_type, response.headers["Content-Type"])
                self.assertGreater(len(response.read()), 100)

    def test_unknown_paths_cannot_read_project_files(self):
        for path in ("/../main.py", "/main.py", "/api/actions"):
            with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                urlopen(self.url + path)
            self.assertEqual(error.exception.code, 404)
            error.exception.close()


if __name__ == "__main__":
    unittest.main()
