# A minimal example of controlling a Sonoff Switch via the EweLink api in Python

This is a simple example that shows you how to login into Ewelink,
discover your device and turn a switch on/off. The functionality is
wrapped into a handy `SonoffManager` class.

```
import asyncio
import logging

from sonoff_manager import SonoffManager

# Optional: set logger to DEBUG level for more verbosity
logging.basicConfig(level=logging.DEBUG)

async def main():
    manager = SonoffManager()

    username="...@email.com"
    password="..."
    country_code="+1"

    try:
        # 1) Log into eWeLink Cloud
        await manager.login(
            username=username,
            password=password,
            country_code=country_code
        )

        # 2) Discover all devices that appear to be "switch-like"
        switches = await manager.discover_switches()
        print(f"Discovered {len(switches)} switches.")

        if not switches:
            print("No switch devices found. Exiting.")
            return

        for dev in switches:
            print(
                f"Name: {dev['name']}, "
                f"ID: {dev['deviceid']}, "
                f"Online: {dev.get('online', '?')}, "
                f"Switch State: {dev['params'].get('switch', '?')}"
            )

        # 3) Attempt to pick the first *online* device to toggle
        online_switches = [d for d in switches if d.get("online")]
        if not online_switches:
            print("No online switches found. Exiting.")
            return

        device = online_switches[0]
        device_id = device["deviceid"]
        device_name = device["name"]

        print(f"\nToggling device: {device_name} (ID={device_id})")

        # 4) Turn ON
        print("Turning ON...")
        result_on = await manager.turn_on(device_id)
        print(f"Turn ON result: {result_on}")

        # Wait a moment so you can observe the ON state
        await asyncio.sleep(20)

        # 5) Turn OFF
        print("Turning OFF...")
        result_off = await manager.turn_off(device_id)
        print(f"Turn OFF result: {result_off}")

    finally:
        # 6) Cleanly close tasks and HTTP session
        await manager.close()

if __name__ == "__main__":
    asyncio.run(main())
```

This relies on two files which have been copied from AlexxIt's
HomeAssistant Sonoff integration, `base.py` and `cloud.py`.

The code snippet above and `SonoffManager` was written by OpenAI's O1
with a some assistance from me.
