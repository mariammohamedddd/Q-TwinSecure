"""Print five sample readings: python -m sensor.demo."""

import json

from .co2_simulator import CO2SensorSimulator


def main() -> None:
    sensor = CO2SensorSimulator(values=[450, 550, 650, 750, 850])
    for reading in sensor.read_many(5):
        print(json.dumps(reading, allow_nan=False))


if __name__ == "__main__":
    main()
