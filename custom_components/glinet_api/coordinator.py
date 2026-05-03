"""Data update coordinators for GL.iNet integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, SLOW_SCAN_INTERVAL
from .glinet_client import GlinetAuthError, GlinetClient, GlinetConnectionError, GlinetFastData, GlinetRouterInfo

_LOGGER = logging.getLogger(__name__)


class GlinetFastCoordinator(DataUpdateCoordinator[GlinetFastData]):
    """Coordinator for fast-poll data (every 30s)."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: GlinetClient,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"GL.iNet fast ({entry.data.get('host', 'unknown')})",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> GlinetFastData:
        """Fetch fast-poll data."""
        try:
            await self.client.keepalive()
            return await self.client.get_fast_data()
        except GlinetAuthError as err:
            raise ConfigEntryAuthFailed(f"Auth error: {err}") from err
        except GlinetConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err


class GlinetSlowCoordinator(DataUpdateCoordinator[GlinetRouterInfo]):
    """Coordinator for slow-poll data (every 6 hours): firmware, MAC, SIM."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: GlinetClient,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"GL.iNet slow ({entry.data.get('host', 'unknown')})",
            update_interval=timedelta(seconds=SLOW_SCAN_INTERVAL),
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> GlinetRouterInfo:
        """Fetch static router info."""
        try:
            return await self.client.get_router_info()
        except GlinetAuthError as err:
            raise ConfigEntryAuthFailed(f"Auth error: {err}") from err
        except GlinetConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err
