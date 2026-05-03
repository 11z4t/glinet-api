"""Base entity for GL.iNet integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GlinetFastCoordinator, GlinetSlowCoordinator
from .glinet_client import GlinetFastData, GlinetRouterInfo


class GlinetEntity(CoordinatorEntity[GlinetFastCoordinator]):
    """Base class for GL.iNet entities using the fast coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GlinetFastCoordinator,
        slow_coordinator: GlinetSlowCoordinator,
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._slow_coordinator = slow_coordinator
        mac = coordinator.entry.data.get("mac", "")
        host = coordinator.entry.data.get("host", "unknown")
        self._attr_unique_id = f"{mac}_{unique_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=f"GL.iNet {host}",
            manufacturer="GL.iNet",
            model=slow_coordinator.data.model if slow_coordinator.data else None,
            sw_version=slow_coordinator.data.firmware_version if slow_coordinator.data else None,
        )

    @property
    def fast_data(self) -> GlinetFastData | None:
        return self.coordinator.data

    @property
    def slow_data(self) -> GlinetRouterInfo | None:
        return self._slow_coordinator.data


class GlinetSlowEntity(CoordinatorEntity[GlinetSlowCoordinator]):
    """Base class for GL.iNet entities using the slow coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        fast_coordinator: GlinetFastCoordinator,
        slow_coordinator: GlinetSlowCoordinator,
        unique_suffix: str,
    ) -> None:
        super().__init__(slow_coordinator)
        self._fast_coordinator = fast_coordinator
        mac = fast_coordinator.entry.data.get("mac", "")
        host = fast_coordinator.entry.data.get("host", "unknown")
        self._attr_unique_id = f"{mac}_{unique_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=f"GL.iNet {host}",
            manufacturer="GL.iNet",
            model=slow_coordinator.data.model if slow_coordinator.data else None,
            sw_version=slow_coordinator.data.firmware_version if slow_coordinator.data else None,
        )

    @property
    def slow_data(self) -> GlinetRouterInfo | None:
        return self.coordinator.data
