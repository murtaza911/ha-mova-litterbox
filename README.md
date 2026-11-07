# MOVA Smart Litter Box for Home Assistant

![Illustration of a smart litter box and Home Assistant activity data](assets/mova-litter-box-cover.svg)

An unofficial cloud integration for the MOVA MeowgicPod LB10 Prime (`mova.litterbox.q2504w`). This is a fork of [knowald/ha-mova-litterbox](https://github.com/knowald/ha-mova-litterbox), with expanded controls and a locally tracked waste bag reminder. The [ha-mova-lr10](https://github.com/marcschwaiger/ha-mova-lr10) project also informed the expanded device support; see [Credits and license](#credits-and-license).

## Features

- Device status, warnings, faults, firmware, consumables, and visit statistics
- Per-pet visits, last visit, and weight
- On-demand clean, empty, level, pause, resume, and stop actions
- Air purification and deodorizing liquid controls, plus automatic modes
- Cleaning mode and delay, litter type, leveling angle, child mode, quiet mode, lights, and sounds
- Waste bag replacement date, visits since replacement, and an estimated replacement countdown
- Automatic bag reminder based on 30 visits and the previous 14 complete days of visit history, or manual reminder using a visit limit and optional day limit

The bag reminder is an estimate based on recorded visits. The integration does not have a verified sensor that detects a physically full waste bag. If you enter only a replacement date, visits for that entire date are included.

## Install

In HACS, add `https://github.com/murtaza911/ha-mova-litterbox` as a **custom integration repository**, install **MOVA Smart Litter Box**, and restart Home Assistant. Or copy `custom_components/mova_litterbox` into your Home Assistant configuration and restart.

Then go to **Settings → Devices & services → Add integration → MOVA Smart Litter Box**. Sign in with your MOVAhome account and select the country and cloud region used by the app. This fork has been verified with a Canada account on the Americas region and Home Assistant 2026.11.0; other combinations are not yet verified here.

If your MOVAhome account uses Google sign-in, set an email and password in the MOVAhome app before configuring this integration.

## Waste bag reminders

Enter the day you last changed the bag through the **Bag Replacement Date** entity, or press **Bag Replaced** when you change it now. The integration backfills visit totals from the selected date and keeps counting future visits.

**Automatic** projects the remaining days from visits since replacement and the recent 14-day visit pace. It uses 30 visits as the initial replacement target and marks the reminder due when that count is reached. **Manual** uses the **Bag Reminder Visits** and **Bag Reminder Days** entities; whichever limit is reached first marks it due. Set days to `0` for visits only. The **Bag Reminder Due** binary sensor can drive a dashboard alert or automation, and Home Assistant also creates a persistent notification when it becomes due.

## Dashboard

This repository provides Home Assistant entities. The custom popup and Basement tile in my own Nightfall dashboard are separate, home-specific dashboard code and are not bundled with this integration.

## API reference

The device uses MIoT commands through the MOVA cloud. See the original [cloud API reference](docs/api-reference.md) for protocol details. The integration uses the account region selected during setup and polls the cloud; it requires an internet connection.

## Credits and license

This fork retains the Git history and MIT license of Kevin Nowald's [ha-mova-litterbox](https://github.com/knowald/ha-mova-litterbox). Marc Schwaiger's MIT-licensed [ha-mova-lr10](https://github.com/marcschwaiger/ha-mova-lr10) was a reference for additional device controls; its license notice is preserved in [LICENSES/MIT-marcschwaiger.txt](LICENSES/MIT-marcschwaiger.txt).

This is a community project and is not affiliated with MOVA or Dreame. Product names and trademarks belong to their owners.
