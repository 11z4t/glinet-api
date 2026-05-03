"""GL.iNet Router integration."""
from __future__ import annotations

import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_HOST, CONF_PASSWORD, RUNTIME_API, RUNTIME_FAST_COORDINATOR, RUNTIME_SLOW_COORDINATOR
from .coordinator import GlinetFastCoordinator, GlinetSlowCoordinator
from .glinet_client import GlinetAuthError, GlinetClient, GlinetConnectionError

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GL.iNet from a config entry."""
    session = async_get_clientsession(hass)
    client = GlinetClient(
        host=entry.data[CONF_HOST],
        password=entry.data[CONF_PASSWORD],
        session=session,
    )

    try:
        await client.authenticate()
    except GlinetAuthError as err:
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
    except GlinetConnectionError as err:
        raise ConfigEntryNotReady(f"Cannot connect to router: {err}") from err

    fast_coordinator = GlinetFastCoordinator(hass, client, entry)
    slow_coordinator = GlinetSlowCoordinator(hass, client, entry)

    await fast_coordinator.async_config_entry_first_refresh()
    await slow_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = {
        RUNTIME_API: client,
        RUNTIME_FAST_COORDINATOR: fast_coordinator,
        RUNTIME_SLOW_COORDINATOR: slow_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a GL.iNet config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options — reload entry."""
    await hass.config_entries.async_reload(entry.entry_id)
