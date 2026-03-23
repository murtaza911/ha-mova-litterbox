# MOVA Litter Box Cloud API Reference

Reverse-engineered from the MOVAhome Android app (`com.dreame.movahome`).

## Server

Base URL: `https://{region}.iot.mova-tech.com:13267`

Known regions: `eu`, `cn`, `us`, `sg`, `in`, `ru`

## Authentication

### Credentials

| Parameter | Value |
|-----------|-------|
| Basic Auth | `mova_app:V7KoChLW8vHACqGb` |
| Tenant ID | `000002` |
| Password salt | `RAylYC%fmSKp7%Tq` |
| Request sign salt | `gigxlmqwZ]7oWZUF` |

Both salts are hardcoded in `libdreame-lib.so` (offsets `0xa51e2` and `0xa51d1`).

### Password Hashing

```
hash = MD5(plaintext_password + "RAylYC%fmSKp7%Tq")
```

### Request Signing

```
sign = MD5(sorted_key=value_pairs + "gigxlmqwZ]7oWZUF")
```

Sort body parameters alphabetically by key (excluding `sign`), concatenate as `key1=value1&key2=value2&...`, append the salt, MD5 the result.

### Login

```
POST /dreame-auth/oauth/token
Content-Type: application/x-www-form-urlencoded
Authorization: Basic bW92YV9hcHA6VjdLb0NoTFc4dkhBQ3FHYg==
tenant-id: 000002

grant_type=password&scope=all&platform=ANDROID&type=account&username={email}&password={hash}&country={country}&lang=en
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 7200,
  "uid": "{uid}",
  "region": "eu",
  "country": "PL"
}
```

Access token expires in 2 hours. Refresh token lasts ~90 days.

### Token Refresh

```
POST /dreame-auth/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&refresh_token={token}
```

### Request Headers

All authenticated requests need:

```
authorization: Basic bW92YV9hcHA6VjdLb0NoTFc4dkhBQ3FHYg==
dreame-auth: {access_token}
tenant-id: 000002
content-type: application/json; charset=utf-8
```

## Device Control (MIoT Protocol)

### Get Properties

```
POST /dreame-iot-com-20000/device/sendCommand

{
  "data": {
    "did": "{device_did}",
    "from": "",
    "id": 1,
    "method": "get_properties",
    "params": [
      {"did": "{device_did}", "siid": 3, "piid": 1}
    ]
  },
  "did": "{device_did}",
  "id": 1,
  "timestamp": 1774199293273
}
```

Response:
```json
{
  "code": 0,
  "data": {
    "result": [
      {"siid": 3, "piid": 1, "code": 0, "value": 0}
    ]
  }
}
```

Result codes: `0` = success, `-4001` = property doesn't exist, `-4003` = device offline.

### Set Properties

Same endpoint, method `set_properties`:
```json
{
  "data": {
    "method": "set_properties",
    "params": [
      {"did": "{device_did}", "siid": 3, "piid": 1, "value": 1}
    ]
  }
}
```

## Pet & Health Endpoints

All under base path `/mova/mova-pet/mova-pet-cat-litter/`.

### Device Info

```
POST /deviceInfo/query
{"did": "{device_did}", "uid": "{uid}", "sign": "...", "timestamp": ...}
```

Returns: `model`, `customName`, `mac`, `sn`, `curVersion`, `timeZone`

### Pet Info

```
POST /userPet/info
{"deviceFlag": 0, "did": "{device_did}", "uid": "{uid}", "sign": "...", "timestamp": ...}
```

Returns `petInfos` array:
```json
{
  "id": 1002,
  "nickName": "Whiskers",
  "varietyName": "Maine Coon",
  "sex": 0,
  "sterilization": 2,
  "birthDate": "2016-03-19",
  "weight": 6100,
  "petAvatar": "https://..."
}
```

### Visit Summary

```
GET /visitToilet/currentInfo?date={date}&zone={timezone}&did={device_did}&uid={uid}
```

Returns:
```json
{
  "toiletsCount": 7,
  "durationAvg": 84048.0,
  "toiletDifferenceCount": 3,
  "currentCountList": [
    {"petId": 1001, "petName": "Mittens", "toiletsCount": 5}
  ],
  "yesterdayCountList": [
    {"petId": 1001, "petName": "Mittens", "toiletsCount": 4}
  ]
}
```

Note: `durationAvg` is in milliseconds.

### Visit Details (paginated)

```
POST /visitToilet/detail
{
  "all": true,
  "date": "{date}",
  "did": "{device_did}",
  "filterType": 0,
  "pageNo": 1,
  "pageSize": 20,
  "petId": "",
  "uid": "{uid}",
  "unknown": false,
  "zone": "{timezone}"
}
```

Returns `toiletDetailInfoRespList` array:
```json
{
  "id": 3702168,
  "petId": 1002,
  "nickName": "Whiskers",
  "weight": 6117,
  "timeDuration": 105251,
  "startTimestamp": "{datetime}",
  "eventType": 1,
  "operationType": 0,
  "pissOrPoop": 2
}
```

| Field | Values |
|-------|--------|
| `eventType` | 1 = cat visit, 2 = cleaning cycle, 10 = other |
| `operationType` | 0 = normal, 2 = system |
| `pissOrPoop` | 0 = unknown, 2 = poop |
| `weight` | Grams |
| `timeDuration` | Milliseconds |

### Consumables

```
POST /consumeMaterial/getMaterialRemainDays?did={device_did}
{"did": "{device_did}", "uid": "{uid}", "sign": "...", "timestamp": ...}
```

Returns array of `{materialType, remainDays}`. Known types: 1, 2, 3 (exact mapping TBD).

### Other Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /visitToilet/info` | Visit details filtered by pet IDs |
| `POST /visitToilet/queryToiletStatus` | Per-pet toilet health status |
| `POST /visitToilet/abnormal` | Abnormal visit alerts |
| `POST /userPet/getAbnormalCollection` | Health abnormalities |
| `POST /noticeSwitch/query` | Notification preferences |

## Device List

```
POST /dreame-user-iot/iotuserbind/device/listV4
{
  "current": 1,
  "size": 200,
  "lang": "en",
  "sharedStatus": 1,
  "sign": "...",
  "timestamp": ...
}
```

Returns `data.page.records` array with device objects including `did`, `model`, `mac`, `ver`, `customName`, `bindDomain`.

## MQTT (not implemented)

Real-time updates go through Alibaba Cloud IoT MQTT with certificate pinning.

EU endpoint: `20000.mt.eu.iot.mova-tech.com:19974`

Endpoint discovery: `GET /dreame-user-iot/iotmqttdomain/v2/list?region=eu`
