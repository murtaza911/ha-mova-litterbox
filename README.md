# MOVA Smart Litter Box - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Custom [Home Assistant](https://www.home-assistant.io/) integration for the MOVA MeowgicPod LB10 Prime self-cleaning smart litter box.

Reverse-engineered from the MOVAhome Android app.

## Supported Devices

| Model                      | Identifier              |
| -------------------------- | ----------------------- |
| MOVA MeowgicPod LB10 Prime | `mova.litterbox.q2504w` |

## Features

**Sensors:**

- Total visits today, yesterday comparison
- Average visit duration
- Per-pet: visit count (today + yesterday), weight (from scale), last visit details
- Pet photos as entity pictures
- Consumable remaining days
- Device status and error code
- Firmware version, serial number

**Controls:**

- Cleaning mode (auto / scheduled / manual)
- Delay cleaning (0-30 minutes)
- Deodorizing spray duration (seconds)
- Switches: soft stool mode, DND mode, child mode, key light, key tone, auto air purification, deodorizing auto spray

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right > Custom repositories
3. Add `https://github.com/knowald/mova-litterbox` as an Integration
4. Install "MOVA Smart Litter Box"
5. Restart Home Assistant

### Manual

Copy `custom_components/mova_litterbox/` to your Home Assistant `custom_components/` directory and restart.

## Configuration

Add via **Settings > Devices & Services > Add Integration > MOVA Smart Litter Box**.

| Field    | Description                                      |
| -------- | ------------------------------------------------ |
| Email    | Your MOVAhome account email                      |
| Password | Your MOVAhome account password                   |
| Country  | Your country (used for initial region detection) |

If your MOVAhome account uses Google sign-in, you must also set an email/password in the MOVAhome app under account settings.

## Device Property Reference

The litter box uses the MIoT protocol with service IDs (siid) and property IDs (piid), routed through Dreame's cloud.

### Service 1: Device Info

| piid | Name             | Type   | R/W |
| ---- | ---------------- | ------ | --- |
| 4    | Firmware version | string | R   |
| 5    | Serial number    | string | R   |

### Service 2: Device Status

| piid | Name          | Type | R/W | Values       |
| ---- | ------------- | ---- | --- | ------------ |
| 1    | Device status | int  | R   | 0 = idle     |
| 2    | Error code    | int  | R   | 0 = no error |
| 5    | Timestamp     | int  | R   | Unix epoch   |
| 6    | Unknown       | int  | R   |              |
| 10   | Unknown       | int  | R   |              |

### Service 3: Settings

| piid | Name                       | Type   | R/W | Values                              |
| ---- | -------------------------- | ------ | --- | ----------------------------------- |
| 1    | Cleaning mode              | int    | RW  | 0 = auto, 1 = scheduled, 2 = manual |
| 2    | Unknown                    | int    | R   |                                     |
| 4    | Soft stool mode            | int    | RW  | 0 = off, 1 = on                     |
| 5    | DND mode                   | int    | RW  | 0 = off, 1 = on                     |
| 6    | DND schedule               | hex    | RW  | See format below                    |
| 7    | Unknown                    | string | R   |                                     |
| 8    | Child mode                 | int    | RW  | 0 = off, 1 = on                     |
| 9    | Key light                  | int    | RW  | 0 = off, 1 = on                     |
| 10   | Key tone                   | int    | RW  | 0 = off, 1 = on                     |
| 11   | Delay cleaning             | int    | RW  | 0-30 minutes                        |
| 12   | Unknown                    | int    | R   |                                     |
| 13   | Unknown toggle             | int    | RW  | 0/1                                 |
| 14   | Unknown                    | int    | R   |                                     |
| 15   | Auto air purification      | int    | RW  | 0 = off, 1 = on                     |
| 16   | Deodorizing auto spray     | int    | RW  | 0 = off, 1 = on                     |
| 17   | Unknown                    | int    | R   |                                     |
| 18   | Deodorizing spray duration | int    | RW  | Seconds                             |
| 19   | Unknown                    | int    | R   |                                     |
| 20   | Hex config                 | hex    | R   |                                     |

### DND Schedule Encoding

The DND schedule (piid 3.6) is a hex string. Each time slot is 5 bytes:

```
[start_hour] [start_min] [end_hour] [end_min] [enabled]
```

`enabled`: `FF` = on, `7F` = off. Multiple entries are concatenated.

Example: `FF0600080CFF13000700FF16000100`

| Start | End   | Enabled |
| ----- | ----- | ------- |
| 06:00 | 08:12 | on      |
| 19:00 | 07:00 | on      |
| 22:00 | 01:00 | on      |

## API Documentation

For full REST API details including authentication, endpoints, and visit data fields, see [docs/api-reference.md](docs/api-reference.md).

## Contributing

Contributions welcome. Several properties (piid 2, 7, 12, 13, 14, 17, 19) are still unmapped. If you can identify what they control in the MOVAhome app, please open an issue or PR.

## Disclaimer

This is an unofficial community project. It is not affiliated with, endorsed by, or supported by MOVA, Dreame Technology, or any of their subsidiaries. All product names, trademarks, and registered trademarks are property of their respective owners.

This integration was built for personal use and interoperability purposes under the principle that device owners should be able to access their own data and control their own devices. Use at your own risk.

## License

MIT
