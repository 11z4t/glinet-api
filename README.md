# GL.iNet Router — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Local integration for GL.iNet routers. Monitors status and controls Wi-Fi and Tailscale VPN directly from Home Assistant — no cloud required.

## Features

- **Sensors**: uptime, CPU load, memory, SoC temperature, cellular signal (RSRP/RSRQ/SINR/RSSI), carrier, APN, WAN IP, Tailscale IP, Wi-Fi client count, firmware version, battery (for mobile routers)
- **Binary sensors**: WAN connected, Tailscale connected, 2.4 GHz / 5 GHz Wi-Fi enabled, charging, firmware safe
- **Switches**: toggle 2.4 GHz Wi-Fi, 5 GHz Wi-Fi, Tailscale VPN

## Tested devices

| Model | Notes |
|-------|-------|
| GL-XE3000 (Puli AX) | Full support including cellular + battery |
| Other GL.iNet routers | Basic support (cellular/battery sensors unavailable) |

## Installation

### Via HACS (recommended)

1. In HACS → **Custom repositories** → add `https://github.com/11z4t/glinet-api` → category **Integration**
2. Install **GL.iNet Router**
3. Restart Home Assistant

### Manual

Copy `custom_components/glinet_api/` to your HA `config/custom_components/` directory and restart.

## Configuration

**Settings → Devices & Services → Add Integration → GL.iNet Router**

| Field | Description |
|-------|-------------|
| Host/IP | Router LAN address (default: `192.168.8.1`) |
| Admin password | Same as the router web UI password |

## Authentication

Uses GL.iNet's local JSON-RPC 2.0 API with challenge-response authentication (MD5/SHA256/SHA512 depending on firmware). No credentials are stored in plaintext.

## Update intervals

- Fast poll (30 s): connectivity, Wi-Fi, Tailscale, cellular signal, battery
- Slow poll (6 h): firmware version and safety check

## License

MIT
