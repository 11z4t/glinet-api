"""Binary sensor platform for GL.iNet integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import RUNTIME_FAST_COORDINATOR, RUNTIME_SLOW_COORDINATOR
from .coordinator import GlinetFastCoordinator, GlinetSlowCoordinator
from .entity import GlinetEntity, GlinetSlowEntity


@dataclass(frozen=True, kw_only=True)
class GlinetBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a GL.iNet binary sensor."""

    fast: bool = True


FAST_BINARY_SENSORS: tuple[GlinetBinarySensorDescription, ...] = (
    GlinetBinarySensorDescription(
        key="wan_connected",
        translation_key="wan_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    GlinetBinarySensorDescription(
        key="tailscale_connected",
        translation_key="tailscale_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:vpn",
    ),
    GlinetBinarySensorDescription(
        key="wifi_2g_enabled",
        translation_key="wifi_2g_enabled",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:wifi",
    ),
    GlinetBinarySensorDescription(
        key="wifi_5g_enabled",
        translation_key="wifi_5g_enabled",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:wifi",
    ),
    GlinetBinarySensorDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
    ),
)

SLOW_BINARY_SENSORS: tuple[GlinetBinarySensorDescription, ...] = (
    GlinetBinarySensorDescription(
        key="firmware_safe",
        translation_key="firmware_safe",
        device_class=BinarySensorDeviceClass.UPDATE,
        icon="mdi:shield-check",
        fast=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GL.iNet binary sensors."""
    fast_coordinator: GlinetFastCoordinator = entry.runtime_data[RUNTIME_FAST_COORDINATOR]
    slow_coordinator: GlinetSlowCoordinator = entry.runtime_data[RUNTIME_SLOW_COORDINATOR]

    entities: list[BinarySensorEntity] = [
        GlinetFastBinarySensor(fast_coordinator, slow_coordinator, desc)
        for desc in FAST_BINARY_SENSORS
    ]
    entities += [
        GlinetSlowBinarySensor(fast_coordinator, slow_coordinator, desc)
        for desc in SLOW_BINARY_SENSORS
    ]
    async_add_entities(entities)


class GlinetFastBinarySensor(GlinetEntity, BinarySensorEntity):
    """Binary sensor from fast-poll data."""

    entity_description: GlinetBinarySensorDescription

    def __init__(
        self,
        coordinator: GlinetFastCoordinator,
        slow_coordinator: GlinetSlowCoordinator,
        description: GlinetBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, slow_coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        if not self.fast_data:
            return None
        if self.entity_description.key == "charging":
            return self.fast_data.charging_status == 1
        return getattr(self.fast_data, self.entity_description.key, None)


class GlinetSlowBinarySensor(GlinetSlowEntity, BinarySensorEntity):
    """Binary sensor from slow-poll data."""

    entity_description: GlinetBinarySensorDescription

    def __init__(
        self,
        fast_coordinator: GlinetFastCoordinator,
        slow_coordinator: GlinetSlowCoordinator,
        description: GlinetBinarySensorDescription,
    ) -> None:
        super().__init__(fast_coordinator, slow_coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        if not self.slow_data:
            return None
        if self.entity_description.key == "firmware_safe":
            return self.slow_data.firmware_is_safe
        return getattr(self.slow_data, self.entity_description.key, None)
