[![GitHub Release](https://img.shields.io/github/release/carnei-ro/ragtech-hass-integration.svg?style=flat-square)](https://github.com/carnei-ro/ragtech-hass-integration/releases)
[![License](https://img.shields.io/github/license/carnei-ro/ragtech-hass-integration.svg?style=flat-square)](https://github.com/carnei-ro/ragtech-hass-integration/blob/main/LICENSE)
[![hacs](https://img.shields.io/badge/HACS-default-orange.svg?style=flat-square)](https://hacs.xyz)

# Ragtech UPS Home Assistant Integration

This custom integration provides monitoring for **Ragtech Uninterruptible Power Supplies (UPS)** connected over a USB/serial port.

It talks to the UPS directly over serial (using [`pyserial`](https://pypi.org/project/pyserial/)), polling it on an interval and exposing the readings as Home Assistant sensors. Unlike the original shell-script based approach, the serial port, baud rate, timeout and polling interval are all **configurable through the UI** — nothing is hardcoded.

![usage screenshot](https://raw.githubusercontent.com/carnei-ro/ragtech-hass-integration/main/screenshot.png)

### Exposed sensors

| Sensor | Unit | Description |
| --- | --- | --- |
| Battery Charge | % | Estimated battery charge level |
| Battery Voltage | V | Battery voltage |
| Battery Status | — | `FULL` / `CHARGING` / `DISCHARGING` |
| Input Voltage | V | Mains input voltage |
| Input Current | A | Estimated input current |
| Input Frequency | Hz | Mains input frequency |
| Output Voltage | V | Output voltage |
| Output Current | A | Output current |
| Output Power | W | Output (apparent) power |
| Output Apparent Power | VA | Output (real) power estimate |
| Temperature | °C | UPS temperature |
| Load | % | UPS load |
| Status | — | NUT-style status (`OL`, `OB`, `LB`, `RB` + `CHRG`/`DISCHRG`) |

## Installation

The recommended installation method is via [HACS](https://hacs.xyz/):

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=carnei-ro&repository=ragtech-hass-integration&category=integration)

Notes:

- HACS only installs the files; you still need to go to `Settings → Devices & Services` and add the integration manually.
- For manual installation (advanced users), copy `custom_components/ragtech` to your Home Assistant `custom_components` directory.

## Configuration

After restarting, add the integration via the **Home Assistant UI**:

1. Go to **Settings → Devices & Services → Add Integration → Ragtech UPS**.

2. Provide the required information:

     - **Name**: Friendly name for your UPS
     - **Serial Port**: Path to the serial device (e.g. `/dev/ttyACM0`)
     - **Baud Rate**: Serial baud rate (default `2560`)
     - **Timeout**: Serial read timeout in seconds (default `5`)
     - **Polling Interval**: How often (in seconds) the UPS is queried (default `30`)

All of these can be changed later through the integration's **Configure** (options) dialog.

> **Note:** Home Assistant must have access to the serial device. When running in a
> container, make sure the device is passed through to the container.

## Credits

The serial protocol decoding is based on reverse engineering of the Ragtech serial
output, calibrated against a multimeter and the official Ragtech app.

Heavily inspired by [this thread](https://community.home-assistant.io/t/home-assistant-ragtech-nobreak-easy-pro-ups-monitoring/678828/55)
