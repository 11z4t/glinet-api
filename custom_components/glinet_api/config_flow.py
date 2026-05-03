"""Config flow for GL.iNet integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.components.dhcp import DhcpServiceInfo
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac

from .const import CONF_HOST, CONF_MAC, CONF_PASSWORD, DEFAULT_HOST, DOMAIN
from .glinet_client import GlinetAuthError, GlinetClient, GlinetConnectionError

_LOGGER = logging.getLogger(__name__)


def _schema(host: str = DEFAULT_HOST, password: str = "") -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=host): str,
            vol.Required(CONF_PASSWORD, default=password): str,
        }
    )


async def _test_connection(
    hass: Any, host: str, password: str
) -> tuple[str | None, str | None]:
    """Try auth and return (mac, error_key) tuple."""
    session = async_get_clientsession(hass)
    client = GlinetClient(host=host, password=password, session=session)
    try:
        info = await client.test_connection()
        return info["mac"], None
    except GlinetAuthError:
        return None, "invalid_auth"
    except GlinetConnectionError:
        return None, "cannot_connect"
    except Exception:
        _LOGGER.exception("Unexpected error connecting to GL.iNet %s", host)
        return None, "unknown"


class GlinetConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for GL.iNet."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str = DEFAULT_HOST
        self._discovered_mac: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            password = user_input[CONF_PASSWORD]
            mac_raw, err = await _test_connection(self.hass, host, password)

            if err:
                errors["base"] = err
            elif mac_raw:
                mac = format_mac(mac_raw)
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: host}, reload_on_update=True
                )
                return self.async_create_entry(
                    title=f"GL.iNet {host}",
                    data={CONF_HOST: host, CONF_PASSWORD: password, CONF_MAC: mac},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(self._host),
            errors=errors,
        )

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        mac = format_mac(discovery_info.macaddress)
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: discovery_info.ip}, reload_on_update=True
        )
        self._host = discovery_info.ip
        self._discovered_mac = mac
        self.context["title_placeholders"] = {"host": discovery_info.ip}
        return await self.async_step_user()

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-auth."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = entry.data[CONF_HOST]
            password = user_input[CONF_PASSWORD]
            _, err = await _test_connection(self.hass, host, password)
            if err:
                errors["base"] = err
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_PASSWORD: password},
                    reason="reauth_successful",
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"host": entry.data[CONF_HOST]},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            password = user_input[CONF_PASSWORD]
            mac_raw, err = await _test_connection(self.hass, host, password)

            if err:
                errors["base"] = err
            elif mac_raw:
                mac = format_mac(mac_raw)
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: host}, reload_on_update=True
                )
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_HOST: host, CONF_PASSWORD: password, CONF_MAC: mac},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(
                host=entry.data[CONF_HOST],
                password=entry.data[CONF_PASSWORD],
            ),
            description_placeholders={"host": entry.data[CONF_HOST]},
            errors=errors,
        )
