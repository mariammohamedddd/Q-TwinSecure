"""Run with python -m qkd.demo; output contains only IDs and safe counts."""

import json
from time import monotonic, sleep

from .key_pool import QKDKeyPool


def main() -> None:
    with QKDKeyPool(capacity=2, generation_interval=0.1) as pool:
        def wait_for_keys(count: int) -> None:
            deadline = monotonic() + 5
            while pool.get_status()["keys_available"] < count:
                if monotonic() >= deadline:
                    raise RuntimeError("demo timed out waiting for automatic supply")
                sleep(0.01)

        print("Software-emulated QKD key supply (classical secure randomness)")
        wait_for_keys(2)
        # Pause before inspecting, so the demonstration counts stay repeatable.
        pool.interrupt_supply()
        print(f"Automatically generated to capacity: {pool.get_status()['keys_generated']}")
        record = pool.consume_key()
        if record is None:
            raise RuntimeError("demo expected an available key")
        print(f"Allocated key ID: {record.key_id}; endpoint material matches: "
              f"{record.device_key == record.twin_key}")
        print(f"Interrupted supply; additional generation: {pool.generate_keys(1)}")
        print(f"Queued allocation while interrupted: {pool.consume_key() is not None}")
        print(f"New epoch allocation with empty pool: {pool.consume_key()}")
        print("Previously allocated material remains available to its connection epoch.")
        pool.resume_supply()
        wait_for_keys(1)
        pool.interrupt_supply()
        print("Resumed supply; automatically replenished one pair.")
        print(f"Recovery allocation succeeded: {pool.consume_key() is not None}")
        print(json.dumps(pool.get_status(), sort_keys=True))


if __name__ == "__main__":
    main()
