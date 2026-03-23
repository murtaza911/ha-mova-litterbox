from homeassistant.const import Platform

DOMAIN = "mova_litterbox"

PASSWORD_SALT = "RAylYC%fmSKp7%Tq"
SIGN_SALT = "gigxlmqwZ]7oWZUF"

BASE_URLS = {
    "eu": "https://eu.iot.mova-tech.com:13267",
    "cn": "https://cn.iot.mova-tech.com:13267",
    "us": "https://us.iot.mova-tech.com:13267",
    "sg": "https://sg.iot.mova-tech.com:13267",
    "in": "https://in.iot.mova-tech.com:13267",
    "ru": "https://ru.iot.mova-tech.com:13267",
}

COUNTRY_CHOICES = {
    "PL": "Poland",
    "DE": "Germany",
    "FR": "France",
    "ES": "Spain",
    "IT": "Italy",
    "NL": "Netherlands",
    "GB": "United Kingdom",
    "US": "United States",
    "CN": "China",
    "SG": "Singapore",
    "IN": "India",
    "RU": "Russia",
    "AU": "Australia",
    "CA": "Canada",
    "BR": "Brazil",
    "JP": "Japan",
    "KR": "South Korea",
}

DEFAULT_COUNTRY = "PL"
DEFAULT_REGION = "eu"

AUTH_HEADER_BASIC = "Basic bW92YV9hcHA6VjdLb0NoTFc4dkhBQ3FHYg=="
TENANT_ID = "000002"

ENDPOINT_AUTH_TOKEN = "/dreame-auth/oauth/token"
ENDPOINT_DEVICE_LIST = "/dreame-user-iot/iotuserbind/device/listV4"
ENDPOINT_SEND_COMMAND = "/dreame-iot-com-20000/device/sendCommand"
ENDPOINT_DEVICE_INFO = "/mova/mova-pet/mova-pet-cat-litter/deviceInfo/query"
ENDPOINT_PET_INFO = "/mova/mova-pet/mova-pet-cat-litter/userPet/info"
ENDPOINT_VISIT_SUMMARY = "/mova/mova-pet/mova-pet-cat-litter/visitToilet/currentInfo"
ENDPOINT_VISIT_DETAIL = "/mova/mova-pet/mova-pet-cat-litter/visitToilet/detail"
ENDPOINT_CONSUMABLES = "/mova/mova-pet/mova-pet-cat-litter/consumeMaterial/getMaterialRemainDays"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_COUNTRY = "country"
CONF_DID = "did"
CONF_UID = "uid"
CONF_REGION = "region"
CONF_REFRESH_TOKEN = "refresh_token"

SCAN_INTERVAL_SECONDS = 60

DEVICE_STATUS_MAP = {
    0: "idle",
}

ERROR_CODE_MAP = {
    0: "none",
}

CLEANING_MODES = {
    0: "Auto",
    1: "Scheduled",
    2: "Manual",
}

CONSUMABLE_TYPE_MAP = {
    1: "Consumable 1",
    2: "Consumable 2",
    3: "Consumable 3",
}

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.SELECT, Platform.NUMBER]

# MIoT property definitions: (siid, piid) -> (key, description, writable)
PROPERTY_DEFINITIONS = {
    # Service 1: Device Info
    (1, 4): ("firmware_version", "Firmware Version", False),
    (1, 5): ("serial_number", "Serial Number", False),
    # Service 2: Device Status
    (2, 1): ("device_status", "Device Status", False),
    (2, 2): ("error_code", "Error Code", False),
    (2, 5): ("timestamp", "Timestamp", False),
    (2, 6): ("status_6", "Status 6", False),
    (2, 10): ("status_10", "Status 10", False),
    # Service 3: Settings
    (3, 1): ("cleaning_mode", "Cleaning Mode", True),
    (3, 2): ("setting_2", "Setting 2", False),
    (3, 4): ("soft_stool_mode", "Soft Stool Mode", True),
    (3, 5): ("dnd_mode", "Do Not Disturb", True),
    (3, 6): ("dnd_schedule", "DND Schedule", True),
    (3, 7): ("setting_7", "Setting 7", False),
    (3, 8): ("child_mode", "Child Mode", True),
    (3, 9): ("key_light", "Key Light", True),
    (3, 10): ("key_tone", "Key Tone", True),
    (3, 11): ("delay_cleaning", "Delay Cleaning", True),
    (3, 12): ("setting_12", "Setting 12", False),
    (3, 13): ("setting_13", "Setting 13", True),
    (3, 14): ("setting_14", "Setting 14", False),
    (3, 15): ("auto_air_purification", "Auto Air Purification", True),
    (3, 16): ("deodorizing_auto_spray", "Deodorizing Auto Spray", True),
    (3, 17): ("setting_17", "Setting 17", False),
    (3, 18): ("deodorizing_spray_duration", "Deodorizing Spray Duration", True),
    (3, 19): ("setting_19", "Setting 19", False),
    (3, 20): ("hex_config", "Hex Config", False),
}

READABLE_PROPERTIES = list(PROPERTY_DEFINITIONS.keys())
WRITABLE_PROPERTIES = [k for k, v in PROPERTY_DEFINITIONS.items() if v[2]]

# Switches: writable boolean properties (0/1 toggle)
SWITCH_PROPERTIES = [
    (3, 4),   # soft_stool_mode
    (3, 5),   # dnd_mode
    (3, 8),   # child_mode
    (3, 9),   # key_light
    (3, 10),  # key_tone
    (3, 13),  # setting_13 (unknown)
    (3, 15),  # auto_air_purification
    (3, 16),  # deodorizing_auto_spray
]

SWITCH_ICONS = {
    (3, 4): "mdi:stomach",
    (3, 5): "mdi:moon-waning-crescent",
    (3, 8): "mdi:account-child",
    (3, 9): "mdi:lightbulb-outline",
    (3, 10): "mdi:volume-high",
    (3, 13): "mdi:toggle-switch-outline",
    (3, 15): "mdi:air-purifier",
    (3, 16): "mdi:spray",
}
