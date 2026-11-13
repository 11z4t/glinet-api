# GL.iNet Router – integration för Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Lokal integration för GL.iNet-routrar. Övervaka status och styr wifi och Tailscale VPN direkt från Home Assistant, utan molntjänst.

## Funktioner

- **Sensorer:** drifttid, processorbelastning, minne, systemkretsens temperatur, mobilsignal (RSRP, RSRQ, SINR och RSSI), operatör, APN, WAN-IP, Tailscale-IP, antal wifi-klienter, version av den inbyggda programvaran och batteristatus för mobila routrar.
- **Binära sensorer:** WAN-anslutning, Tailscale-anslutning, aktivering av wifi på 2,4 respektive 5 GHz, laddning och säkerhetsstatus för den inbyggda programvaran.
- **Strömbrytare:** aktivera eller avaktivera wifi på 2,4 GHz, wifi på 5 GHz och Tailscale VPN.

## Testade enheter

| Modell | Kommentar |
|---|---|
| GL-XE3000 (Puli AX) | Fullständigt stöd, inklusive mobilanslutning och batteri |
| Andra GL.iNet-routrar | Grundläggande stöd; sensorer för mobilanslutning och batteri är inte tillgängliga |

## Installation

### Via HACS, rekommenderad metod

1. Öppna **Custom repositories** i HACS, lägg till `https://github.com/11z4t/glinet-api` och välj kategorin **Integration**.
2. Installera **GL.iNet Router**.
3. Starta om Home Assistant.

### Manuell installation

Kopiera `custom_components/glinet_api/` till katalogen `config/custom_components/` i din Home Assistant-installation och starta om.

## Konfiguration

Öppna **Inställningar → Enheter och tjänster → Lägg till integration → GL.iNet Router**.

| Fält | Beskrivning |
|---|---|
| Värd/IP | Routerns LAN-adress; standardvärdet är `192.168.8.1` |
| Administratörslösenord | Samma lösenord som används i routerns webbgränssnitt |

## Autentisering

Integrationen använder GL.iNets lokala JSON-RPC 2.0-API med utmaning–svar-autentisering (MD5, SHA256 eller SHA512 beroende på versionen av den inbyggda programvaran). Inga autentiseringsuppgifter lagras i klartext.

## Uppdateringsintervall

- **Var 30:e sekund:** anslutningar, wifi, Tailscale, mobilsignal och batteri.
- **Var sjätte timme:** version av den inbyggda programvaran och säkerhetskontroll.

## Licens

MIT
