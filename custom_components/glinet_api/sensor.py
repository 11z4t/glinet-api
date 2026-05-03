"""Sensor platform for GL.iNet integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfDataRate,
    UnitOfFrequency,
    UnitOfInformation,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CHARGING_STATUS, RUNTIME_FAST_COORDINATOR, RUNTIME_SLOW_COORDINATOR
from .coordinator import GlinetFastCoordinator, GlinetSlowCoordinator
from .entity import GlinetEntity, GlinetSlowEntity
from .glinet_client import GlinetFastData, GlinetRouterInfo


@dataclass(frozen=True, kw_only=True)
class GlinetSensorDescription(SensorEntityDescription):
    """Describes a GL.iNet sensor."""

    fast: bool = True  # True = from fast coordinator, False = slow


FAST_SENSORS: tuple[GlinetSensorDescription, ...] = (
    GlinetSensorDescription(
        key="battery_percent",
        translation_key="battery_percent",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GlinetSensorDescription(
        key="battery_temperature",
        translation_key="battery_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    GlinetSensorDescription(
        key="charge_cycles",
        translation_key="charge_cycles",
        native_unit_of_measurement="cycles",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-sync",
    ),
    GlinetSensorDescription(
        key="uptime",
        translation_key="uptime",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-outline",
    ),
    GlinetSensorDescription(
        key="load_1min",
        translation_key="load_1min",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cpu-64-bit",
        suggested_display_precision=2,
    ),
    GlinetSensorDescription(
        key="memory_total",
        translation_key="memory_total",
        native_unit_of_measurement=UnitOfInformation.KILOBYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    GlinetSensorDescription(
        key="memory_free",
        translation_key="memory_free",
        native_unit_of_measurement=UnitOfInformation.KILOBYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GlinetSensorDescription(
        key="temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    GlinetSensorDescription(
        key="carrier",
        translation_key="carrier",
        icon="mdi:antenna",
    ),
    GlinetSensorDescription(
        key="network_type",
        translation_key="network_type",
        icon="mdi:signal-5g",
    ),
    GlinetSensorDescription(
        key="rsrp",
        translation_key="rsrp",
        native_unit_of_measurement="dBm",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    GlinetSensorDescription(
        key="rsrq",
        translation_key="rsrq",
        native_unit_of_measurement="dB",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:signal-cellular-3",
        entity_registry_enabled_default=False,
    ),
    GlinetSensorDescription(
        key="sinr",
        translation_key="sinr",
        native_unit_of_measurement="dB",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:signal-cellular-3",
        entity_registry_enabled_default=False,
    ),
    GlinetSensorDescription(
        key="rssi",
        translation_key="rssi",
        native_unit_of_measurement="dBm",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GlinetSensorDescription(
        key="signal_level",
        translation_key="signal_level",
        native_unit_of_measurement="bars",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:signal",
    ),
    GlinetSensorDescription(
        key="apn",
        translation_key="apn",
        icon="mdi:sim",
        entity_registry_enabled_default=False,
    ),
    GlinetSensorDescription(
        key="wan_ip",
        translation_key="wan_ip",
        icon="mdi:ip-network",
    ),
    GlinetSensorDescription(
        key="tailscale_ip",
        translation_key="tailscale_ip",
        icon="mdi:vpn",
    ),
    GlinetSensorDescription(
        key="wifi_clients",
        translation_key="wifi_clients",
        native_unit_of_measurement="clients",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wifi",
    ),
    GlinetSensorDescription(
        key="charging_status",
        translation_key="charging_status",
        icon="mdi:battery-charging",
        device_class=SensorDeviceClass.ENUM,
        options=list(CHARGING_STATUS.values()),
    ),
)

SLOW_SENSORS: tuple[GlinetSensorDescription, ...] = (
    GlinetSensorDescription(
        key="firmware_version",
        translation_key="firmware_version",
        icon="mdi:package-up",
        fast=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GL.iNet sensors."""
    fast_coordinator: GlinetFastCoordinator = entry.runtime_data[RUNTIME_FAST_COORDINATOR]
    slow_coordinator: GlinetSlowCoordinator = entry.runtime_data[RUNTIME_SLOW_COORDINATOR]

    entities: list[SensorEntity] = [
        GlinetFastSensor(fast_coordinator, slow_coordinator, desc)
        for desc in FAST_SENSORS
    ]
    entities += [
        GlinetSlowSensor(fast_coordinator, slow_coordinator, desc)
        for desc in SLOW_SENSORS
    ]
    async_add_entities(entities)


class GlinetFastSensor(GlinetEntity, SensorEntity):
    """Sensor from fast-poll data."""

    entity_description: GlinetSensorDescription

    def __init__(
        self,
        coordinator: GlinetFastCoordinator,
        slow_coordinator: GlinetSlowCoordinator,
        description: GlinetSensorDescription,
    ) -> None:
        super().__init__(coordinator, slow_coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        if not self.fast_data:
            return None
        raw = getattr(self.fast_data, self.entity_description.key, None)
        # Translate charging_status int → string
        if self.entity_description.key == "charging_status" and raw is not None:
            return CHARGING_STATUS.get(raw, str(raw))
        return raw


class GlinetSlowSensor(GlinetSlowEntity, SensorEntity):
    """Sensor from slow-poll data."""

    entity_description: GlinetSensorDescription

    def __init__(
        self,
        fast_coordinator: GlinetFastCoordinator,
        slow_coordinator: GlinetSlowCoordinator,
        description: GlinetSensorDescription,
    ) -> None:
        super().__init__(fast_coordinator, slow_coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        if not self.slow_data:
            return None
        return getattr(self.slow_data, self.entity_description.key, None)
