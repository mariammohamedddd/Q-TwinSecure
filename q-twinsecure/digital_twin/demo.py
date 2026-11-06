"""Run from the project folder with: python -m digital_twin.demo"""

from datetime import datetime, timedelta, timezone
import json

from . import TwinMonitor


def main() -> None:
    now = datetime(2026, 11, 5, 12, 30, tzinfo=timezone.utc)
    monitor = TwinMonitor(clock=lambda: now)
    print("No observation:", json.dumps(monitor.get_status()))
    monitor.update_observation({
        "sensor_id": "co2-simulator-01", "value_ppm": 650.0,
        "timestamp": now.isoformat(),
    })
    for elapsed in (0, 6, 16):
        print(f"After {elapsed}s:", json.dumps(
            monitor.get_status(now + timedelta(seconds=elapsed))))
    now += timedelta(seconds=17)
    monitor.update_observation({
        "sensor_id": "co2-simulator-01", "value_ppm": 660.0,
        "timestamp": now.isoformat(),
    })
    print("Recovery:", json.dumps(monitor.get_status()))


if __name__ == "__main__":
    main()
