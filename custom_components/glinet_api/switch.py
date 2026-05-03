"""Switch platform for GL.iNet integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import RUNTIME_API, RUNTIME_FAST_COORDINATOR, RUNTIME_SLOW_COORDINATOR
from .coordinator import GlinetFastCoordinator, GlinetSlowCoordinator
from .entity import GlinetEntity
from .glinet_client import GlinetClient

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class GlinetSwitchDescription(SwitchEntityDescription):
    """Describes a GL.iNet switch."""


SWITCHES: tuple[GlinetSwitchDescription, ...] = (
    GlinetSwitchDescription(
        key="wifi_2g",
        translation_key="wifi_2g",
        icon="mdi:wifi",
    ),
    GlinetSwitchDescription(
        key="wifi_5g",
        translation_key="wifi_5g",
        icon="mdi:wifi",
    ),
    GlinetSwitchDescription(
        key="tailscale",
        translation_key="tailscale",
        icon="mdi:vpn",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GL.iNet switches."""
    fast_coordinator: GlinetFastCoordinator = entry.runtime_data[RUNTIME_FAST_COORDINATOR]
    slow_coordinator: GlinetSlowCoordinator = entry.runtime_data[RUNTIME_SLOW_COORDINATOR]
    client: GlinetClient = entry.runtime_data[RUNTIME_API]

    async_add_entities(
        GlinetSwitch(fast_coordinator, slow_coordinator, client, desc)
        for desc in SWITCHES
    )


class GlinetSwitch(GlinetEntity, SwitchEntity):
    """A GL.iNet toggleable switch."""

    entity_description: GlinetSwitchDescription

    def __init__(
        self,
        coordinator: GlinetFastCoordinator,
        slow_coordinator: GlinetSlowCoordinator,
        client: GlinetClient,
        description: GlinetSwitchDescription,
    ) -> None:
        super().__init__(coordinator, slow_coordinator, description.key)
        self.entity_description = description
        self._client = client

    @property
    def is_on(self) -> bool | None:
        if not self.fast_data:
            return None
        if self.entity_description.key == "wifi_2g":
            return self.fast_data.wifi_2g_enabled
        if self.entity_description.key == "wifi_5g":
            return self.fast_data.wifi_5g_enabled
        if self.entity_description.key == "tailscale":
            return self.fast_data.tailscale_connected
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self._toggle(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self._toggle(False)

    async def _toggle(self, enabled: bool) -> None:
        key = self.entity_description.key
        if key == "wifi_2g":
            await self._client.set_wifi_enabled("2.4g", enabled)
        elif key == "wifi_5g":
            await self._client.set_wifi_enabled("5g", enabled)
        elif key == "tailscale":
            await self._client.set_tailscale_enabled(enabled)
        await self.coordinator.async_request_refresh()
