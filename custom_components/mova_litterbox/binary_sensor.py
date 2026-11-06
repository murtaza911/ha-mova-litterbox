"""Device warning and fault indicators from the MOVA LR10 property map."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DID
from .coordinator import MovaLitterboxCoordinator
from .entity import MovaBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MovaLitterboxCoordinator = entry.runtime_data
    did = entry.data[CONF_DID]
    async_add_entities([
        MovaProblemSensor(coordinator, did, "warning", "Warning", 2),
        MovaProblemSensor(coordinator, did, "fault", "Fault", 6),
        MovaProblemSensor(coordinator, did, "additional_warning", "Additional Warning", 11),
    ])


class MovaProblemSensor(MovaBaseEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, did: str, key: str, name: str, piid: int) -> None:
        super().__init__(coordinator, did, key, name)
        self._piid = piid

    @property
    def is_on(self) -> bool | None:
        value = (self.coordinator.data or {}).get("properties", {}).get((2, self._piid))
        return None if value is None else bool(value)

    @property
    def extra_state_attributes(self) -> dict[str, int] | None:
        value = (self.coordinator.data or {}).get("properties", {}).get((2, self._piid))
        return {"mask": value} if isinstance(value, int) else None
