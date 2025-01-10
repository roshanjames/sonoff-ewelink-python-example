import asyncio
import logging
from typing import Optional

from aiohttp import ClientSession

# Make sure cloud.py and base.py are in your project and importable
from cloud import XRegistryCloud, XDevice

_LOGGER = logging.getLogger(__name__)


class SonoffManager:
    """
    A convenient class that:
      1. Logs into eWeLink Cloud via XRegistryCloud.
      2. Starts the background WS (run_forever) for Cloud commands.
      3. Discovers switch-type devices (has 'switch' or 'switches' in params).
      4. Turns them ON/OFF using registry.send().
      5. Cleans up tasks upon close().
    """

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.registry: Optional[XRegistryCloud] = None
        self.devices: list[dict] = []  # store discovered devices here

    async def login(self, username: str, password: str, country_code: str = "+1") -> None:
        """
        1) Create the session + registry
        2) Log in to eWeLink Cloud
        3) Start the background WebSocket connection
        """
        _LOGGER.debug("Creating ClientSession...")
        self.session = ClientSession()

        _LOGGER.debug("Initializing XRegistryCloud...")
        self.registry = XRegistryCloud(session=self.session)

        # 1) Log into eWeLink Cloud
        #    If you have a token, call:
        #      await self.registry.login("token", "us:YOUR_TOKEN_HERE")
        #
        _LOGGER.debug("Logging in to eWeLink Cloud...")
        await self.registry.login(
            username=username,
            password=password,
            country_code=country_code
        )

        # 2) Start the registry's background task that opens and maintains
        #    the WebSocket to the eWeLink Cloud. This is critical for .send() calls.
        _LOGGER.debug("Starting eWeLink WebSocket connection (registry.run_forever).")
        self.registry.start()

        # Optionally wait a short time to let the WS fully connect.
        await asyncio.sleep(2)

    async def discover_switches(self) -> list[dict]:
        """
        Discover your eWeLink "homes," list all devices, and store only
        those that appear to be "switch-like."

        Returns:
            A list of discovered devices with "switch"/"switches" in their params.
        """
        if not self.registry:
            _LOGGER.error("Cannot discover devices; registry not initialized!")
            return []

        _LOGGER.debug("Fetching homes from eWeLink Cloud...")
        homes = await self.registry.get_homes()
        _LOGGER.debug(f"Homes found: {homes}")

        home_ids = list(homes.keys())  # collect all family IDs

        _LOGGER.debug("Fetching devices for discovered homes...")
        all_devices = await self.registry.get_devices(home_ids)
        _LOGGER.debug(f"All devices: {all_devices}")

        def is_switch(dev: dict) -> bool:
            params = dev.get("params", {})
            return ("switch" in params) or ("switches" in params)

        # Keep only devices that appear to be switches
        self.devices = [dev for dev in all_devices if is_switch(dev)]
        return self.devices

    async def turn_on(self, device_id: str) -> str:
        """
        Turn ON a discovered device by its deviceid.
        Returns: The short status from registry.send(), e.g. "online", "offline", "timeout", or "E#??"
        """
        if not self.registry:
            return "E#NoRegistry"

        device = self._find_device(device_id)
        if not device:
            return f"E#DeviceNotFound:{device_id}"

        # Single-channel example: just send {"switch": "on"}
        _LOGGER.debug(f"Turning ON: {device['name']} (deviceid={device_id})")
        return await self.registry.send(device, {"switch": "on"})

    async def turn_off(self, device_id: str) -> str:
        """
        Turn OFF a discovered device by its deviceid.
        Returns: The short status from registry.send().
        """
        if not self.registry:
            return "E#NoRegistry"

        device = self._find_device(device_id)
        if not device:
            return f"E#DeviceNotFound:{device_id}"

        _LOGGER.debug(f"Turning OFF: {device['name']} (deviceid={device_id})")
        return await self.registry.send(device, {"switch": "off"})

    async def close(self):
        """
        Stops the registry's run_forever task and closes the session.
        """
        if not self.registry:
            return
        _LOGGER.debug("Stopping eWeLink Cloud WS task...")
        await self.registry.stop()

        if self.session and not self.session.closed:
            _LOGGER.debug("Closing HTTP session...")
            await self.session.close()

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _find_device(self, device_id: str) -> Optional[XDevice]:
        """Utility to locate a device by deviceid in self.devices."""
        return next((d for d in self.devices if d["deviceid"] == device_id), None)
