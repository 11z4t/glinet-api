"""Constants for the GL.iNet integration."""

DOMAIN = "glinet_api"

# Config entry keys
CONF_HOST = "host"
CONF_PASSWORD = "password"
CONF_MAC = "mac"

# Default values
DEFAULT_HOST = "192.168.8.1"
DEFAULT_SCAN_INTERVAL = 30    # seconds — fast coordinator
SLOW_SCAN_INTERVAL = 21600    # 6 hours — firmware/hardware coordinator

# Runtime data keys
RUNTIME_FAST_COORDINATOR = "fast_coordinator"
RUNTIME_SLOW_COORDINATOR = "slow_coordinator"
RUNTIME_API = "api"

# Connectivity / charging status codes
CHARGING_STATUS = {
    0: "not_charging",
    1: "charging",
    2: "charged",
    3: "discharging",
}

# Network type codes from modem.get_status
NETWORK_TYPE_MAP = {
    "nr": "5G NR",
    "lte": "4G LTE",
    "wcdma": "3G WCDMA",
    "gsm": "2G GSM",
    "none": "No Signal",
}

# Minimal safe firmware version (CVE-2025-2851)
MIN_SAFE_FIRMWARE = (4, 7, 4)

# Auth algorithm codes
AUTH_ALG_MD5 = 1
AUTH_ALG_SHA256 = 5
AUTH_ALG_SHA512 = 6

# Session keepalive interval (router SID expires ~5 min)
KEEPALIVE_INTERVAL = 30   # seconds

# Nonce window — GL.iNet firmware enforces 2000ms
NONCE_WINDOW_MS = 2000
