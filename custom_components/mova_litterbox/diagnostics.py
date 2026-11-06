"""Redacted diagnostics for troubleshooting the MOVA cloud integration."""

from homeassistant.components.diagnostics import async_redact_data

REDACT = {
    "email", "password", "refresh_token", "access_token", "uid", "did",
    "sn", "serial_number", "mac", "masterUid", "petAvatar", "pet_id", "petId",
}


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    properties = (coordinator.data or {}).get("properties", {})
    return async_redact_data({
        "config": dict(entry.data),
        "device": coordinator.device_info,
        "properties": {f"{siid}.{piid}": value for (siid, piid), value in properties.items()},
        "visit_summary": (coordinator.data or {}).get("visit_summary"),
        "consumables": (coordinator.data or {}).get("consumables"),
    }, REDACT)
