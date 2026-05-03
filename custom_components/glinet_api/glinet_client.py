"""
GL.iNet JSON-RPC 2.0 client — async, non-blocking.

Security notes (as of 2026-05-03):
- CVE-2024-39225 (CRITICAL): SID brute-force RCE — never expose router WAN admin port!
- CVE-2025-2851 (8.0 HIGH): Buffer overflow in plugins.so — minimum safe firmware: 4.7.4
- CVE-2023-33620 (UNPATCHED): Shared SSL cert key across ALL devices until 2039
- No rate limiting on /rpc — protect with firewall (WAN→admin blocked)
- All processes run as root on router
- Nonce window: 2000ms — auth sequence must be atomic and fast

Authentication flow:
1. POST /rpc → challenge → {alg, nonce, salt}
2. crypt(password, salt, alg) → crypt_pw  (MD5/SHA256/SHA512)
3. MD5("root:" + crypt_pw + ":" + nonce) → hash
4. POST /rpc → login {hash} → {sid}
5. All calls: params=[sid, module, method, {}]
6. Keepalive: POST /rpc → alive every 30s (SID expires ~5 min)
"""
from __future__ import annotations

import asyncio
import crypt  # Deprecated in Python 3.13; works in 3.12 (current HA minimum)
import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Auth algorithm codes
_ALG_PREFIX = {1: "$1$", 5: "$5$", 6: "$6$"}


class GlinetAuthError(Exception):
    """Authentication failed."""


class GlinetConnectionError(Exception):
    """Cannot reach router."""


class GlinetApiError(Exception):
    """API returned an error code."""


@dataclass
class GlinetRouterInfo:
    """Static info collected at setup / slow poll."""

    mac: str = ""
    model: str = ""
    firmware_version: str = ""
    firmware_is_safe: bool = False
    imei: str = ""
    iccid: str = ""
    imsi: str = ""


@dataclass
class GlinetFastData:
    """Fast-poll data (every 30s)."""

    # Battery (MCU)
    battery_percent: int | None = None
    charging_status: int | None = None  # 0=not charging, 1=charging, 2=charged, 3=discharging
    battery_temperature: float | None = None
    charge_cycles: int | None = None

    # System
    uptime: int | None = None          # seconds
    load_1min: float | None = None
    memory_total: int | None = None    # kB
    memory_free: int | None = None     # kB
    temperature: float | None = None   # °C (SoC temperature)

    # Cellular
    carrier: str | None = None
    network_type: str | None = None    # "5G NR", "4G LTE", etc.
    rsrp: int | None = None            # dBm
    rsrq: int | None = None            # dB
    sinr: float | None = None          # dB
    rssi: int | None = None            # dBm
    signal_level: int | None = None    # 0-5
    apn: str | None = None

    # Connectivity
    wan_connected: bool = False
    wan_ip: str | None = None
    dns: str | None = None
    tailscale_connected: bool = False
    tailscale_ip: str | None = None

    # WiFi
    wifi_2g_enabled: bool | None = None
    wifi_5g_enabled: bool | None = None
    wifi_clients: int | None = None


class GlinetClient:
    """Async GL.iNet JSON-RPC 2.0 client."""

    def __init__(
        self,
        host: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._url = f"http://{host}/rpc"
        self._password = password
        self._session = session
        self._sid: str | None = None
        self._sid_time: float = 0.0
        self._req_id: int = 1
        self._lock = asyncio.Lock()

    # ─── Low-level RPC ────────────────────────────────────────────────────────

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        """Raw JSON-RPC call. Returns result or raises."""
        req_id = self._req_id
        self._req_id += 1
        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        try:
            async with self._session.post(
                self._url, json=payload, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 401:
                    raise GlinetAuthError("HTTP 401 — session expired or wrong password")
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise GlinetConnectionError(f"Cannot reach {self._url}: {err}") from err

        if "error" in data:
            code = data["error"].get("code", 0)
            msg = data["error"].get("message", "unknown")
            if code == -32001:
                # Session invalid — force re-auth on next call
                self._sid = None
                raise GlinetAuthError(f"Session invalid (code {code}): {msg}")
            raise GlinetApiError(f"RPC error {code}: {msg}")

        return data.get("result")

    # ─── Authentication ───────────────────────────────────────────────────────

    async def authenticate(self) -> None:
        """Full challenge-response authentication. Thread-safe."""
        async with self._lock:
            await self._do_authenticate()

    async def _do_authenticate(self) -> None:
        """Internal: perform full auth (must hold _lock)."""
        _LOGGER.debug("GL.iNet: starting authentication")

        # Step 1: challenge
        challenge = await self._rpc("challenge", [{"username": "root"}])
        if not challenge:
            raise GlinetAuthError("Empty challenge response")

        alg = challenge.get("alg", 5)
        nonce = challenge.get("nonce", "")
        salt = challenge.get("salt", "")

        if not nonce or not salt:
            raise GlinetAuthError(f"Invalid challenge: alg={alg} nonce={nonce!r} salt={salt!r}")

        # Step 2: compute crypt_pw using the specified algorithm
        alg_prefix = _ALG_PREFIX.get(alg, "$5$")
        try:
            crypt_pw = crypt.crypt(self._password, f"{alg_prefix}{salt}$")
        except Exception as err:
            raise GlinetAuthError(f"crypt failed (alg={alg}): {err}") from err

        # Step 3: MD5("root:" + crypt_pw + ":" + nonce)
        combined = f"root:{crypt_pw}:{nonce}"
        hash_val = hashlib.md5(combined.encode()).hexdigest()

        # Step 4: login → SID
        # Note: nonce window is 2000ms — steps 2-4 must complete within that window
        login_result = await self._rpc("login", [{"username": "root", "hash": hash_val}])
        if not login_result or "sid" not in login_result:
            raise GlinetAuthError(f"Login failed — no SID in response: {login_result}")

        self._sid = login_result["sid"]
        self._sid_time = time.monotonic()
        _LOGGER.debug("GL.iNet: authenticated, SID obtained")

    async def _ensure_auth(self) -> str:
        """Return valid SID, re-authenticating if needed."""
        # SID expires ~5 min; re-auth if older than 4.5 min
        if self._sid is None or (time.monotonic() - self._sid_time) > 270:
            async with self._lock:
                if self._sid is None or (time.monotonic() - self._sid_time) > 270:
                    await self._do_authenticate()
        return self._sid  # type: ignore[return-value]

    # ─── API calls ────────────────────────────────────────────────────────────

    async def _call(self, module: str, method: str, args: dict | None = None) -> Any:
        """Authenticated API call with automatic re-auth on session expiry."""
        sid = await self._ensure_auth()
        try:
            return await self._rpc("call", [sid, module, method, args or {}])
        except GlinetAuthError:
            # Re-authenticate once and retry
            _LOGGER.debug("GL.iNet: session expired, re-authenticating")
            async with self._lock:
                await self._do_authenticate()
            return await self._rpc("call", [self._sid, module, method, args or {}])

    async def keepalive(self) -> None:
        """Send keepalive to prevent SID expiry. Call every 30s."""
        if self._sid:
            try:
                await self._rpc("alive", [self._sid])
            except Exception:
                self._sid = None  # Will re-auth on next call

    async def get_router_info(self) -> GlinetRouterInfo:
        """Collect static router info (model, firmware, MAC, SIM)."""
        info = GlinetRouterInfo()

        # System info (model, firmware)
        try:
            sys_info = await self._call("system", "get_info")
            if sys_info:
                info.model = sys_info.get("model", "")
                fw = sys_info.get("firmware_version", "") or sys_info.get("firmware", "")
                info.firmware_version = fw
                info.firmware_is_safe = _check_firmware_safe(fw)
        except Exception as err:
            _LOGGER.debug("GL.iNet: get_info error: %s", err)

        # MAC address (unique_id source)
        try:
            mac_info = await self._call("network", "get_mac")
            if mac_info:
                info.mac = mac_info.get("mac", "")
        except Exception as err:
            _LOGGER.debug("GL.iNet: get_mac error: %s", err)

        # Modem info (IMEI, SIM ICCID, IMSI)
        try:
            modem_info = await self._call("modem", "get_info")
            if modem_info:
                info.imei = modem_info.get("imei", "")
                info.iccid = modem_info.get("sim_iccid", "") or modem_info.get("iccid", "")
                info.imsi = modem_info.get("imsi", "")
        except Exception as err:
            _LOGGER.debug("GL.iNet: modem get_info error: %s", err)

        return info

    async def get_fast_data(self) -> GlinetFastData:
        """Collect all fast-poll data (30s interval)."""
        data = GlinetFastData()

        # Battery (MCU status)
        try:
            status = await self._call("system", "get_status")
            mcu = (status or {}).get("system", {}).get("mcu", {})
            if mcu:
                data.battery_percent = mcu.get("charge_percent")
                data.charging_status = mcu.get("charging_status")
                data.battery_temperature = mcu.get("temperature")
                data.charge_cycles = mcu.get("charge_cnt")
        except Exception as err:
            _LOGGER.debug("GL.iNet: get_status/battery error: %s", err)

        # System load + memory
        try:
            sysinfo = await self._call("system", "get_info")
            if sysinfo:
                data.uptime = sysinfo.get("uptime")
                load = sysinfo.get("load_average", [None, None, None])
                if load:
                    data.load_1min = load[0]
                mem = sysinfo.get("memory", {})
                data.memory_total = mem.get("total")
                data.memory_free = mem.get("free")
        except Exception as err:
            _LOGGER.debug("GL.iNet: sysinfo error: %s", err)

        # Cellular
        try:
            modem = await self._call("modem", "get_status")
            if modem:
                data.carrier = modem.get("operator") or modem.get("carrier")
                data.network_type = modem.get("network_type")
                data.rsrp = modem.get("rsrp")
                data.rsrq = modem.get("rsrq")
                data.sinr = modem.get("sinr")
                data.rssi = modem.get("rssi")
                data.signal_level = modem.get("signal")
                data.apn = modem.get("apn")
        except Exception as err:
            _LOGGER.debug("GL.iNet: modem status error: %s", err)

        # WAN connectivity
        try:
            wan = await self._call("network", "get_wan_state")
            if wan:
                data.wan_connected = wan.get("connected", False)
                data.wan_ip = wan.get("ip")
                data.dns = wan.get("dns")
        except Exception as err:
            _LOGGER.debug("GL.iNet: wan status error: %s", err)

        # Tailscale
        try:
            ts = await self._call("tailscale", "get_status")
            if ts:
                data.tailscale_connected = ts.get("connected", False)
                data.tailscale_ip = ts.get("ip")
        except Exception as err:
            _LOGGER.debug("GL.iNet: tailscale error: %s", err)

        # WiFi (batch to reduce round-trips)
        try:
            wifi = await self._call("wifi", "get_status")
            if wifi:
                data.wifi_2g_enabled = wifi.get("2g_enable", wifi.get("radio0_enable"))
                data.wifi_5g_enabled = wifi.get("5g_enable", wifi.get("radio1_enable"))
        except Exception as err:
            _LOGGER.debug("GL.iNet: wifi status error: %s", err)

        return data

    async def get_firmware_version(self) -> str:
        """Get firmware version (use in slow coordinator only)."""
        try:
            info = await self._call("system", "get_info")
            return (info or {}).get("firmware_version", "")
        except Exception as err:
            _LOGGER.debug("GL.iNet: firmware version error: %s", err)
            return ""

    async def set_wifi_enabled(self, band: str, enabled: bool) -> None:
        """Enable or disable WiFi band. band = '2.4g' or '5g'."""
        method = "set_wifi_enable" if enabled else "disable_wifi"
        await self._call("wifi", method, {"band": band, "enable": enabled})

    async def set_tailscale_enabled(self, enabled: bool) -> None:
        """Enable or disable Tailscale VPN."""
        method = "start" if enabled else "stop"
        await self._call("tailscale", method)

    async def test_connection(self) -> dict[str, str]:
        """Test connection and auth. Returns {'mac': ..., 'model': ...}."""
        await self.authenticate()
        info = await self.get_router_info()
        return {"mac": info.mac, "model": info.model, "firmware": info.firmware_version}


def _check_firmware_safe(fw_string: str) -> bool:
    """Check if firmware version meets minimum safe version (4.7.4)."""
    if not fw_string:
        return False
    # Parse version like "4.7.4 build 240601" or "4.7.4-release1"
    import re
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", fw_string)
    if not m:
        return False
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return (major, minor, patch) >= (4, 7, 4)
