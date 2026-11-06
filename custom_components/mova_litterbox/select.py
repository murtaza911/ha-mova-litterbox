import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import MovaApiError, MovaAuthError
from .const import (
    AIR_PURIFICATION_DURATIONS,
    CLEANING_MODES,
    CONF_DID,
    LEVELING_ANGLES,
    LITTER_TYPES,
)
from .coordinator import MovaLitterboxCoordinator
from .entity import MovaBaseEntity

_LOGGER = logging.getLogger(__name__)

CLEANING_MODE_VALUE_TO_LABEL = CLEANING_MODES
CLEANING_MODE_LABEL_TO_VALUE = {v: k for k, v in CLEANING_MODES.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MovaLitterboxCoordinator = entry.runtime_data
    did = entry.data[CONF_DID]

    async_add_entities([
        MovaCleaningModeSelect(coordinator, did),
        MovaPropertySelect(coordinator, did, "litter_type", "Litter Type", 3, 12, LITTER_TYPES, "mdi:grain"),
        MovaPropertySelect(coordinator, did, "air_purification_duration", "Air Purification Duration", 3, 17, AIR_PURIFICATION_DURATIONS, "mdi:air-filter"),
        MovaPropertySelect(coordinator, did, "leveling_angle", "Leveling Angle", 3, 21, LEVELING_ANGLES, "mdi:format-line-spacing"),
    ])


class MovaCleaningModeSelect(MovaBaseEntity, SelectEntity):
    _attr_icon = "mdi:broom"
    _attr_options = list(CLEANING_MODES.values())

    def __init__(
        self,
        coordinator: MovaLitterboxCoordinator,
        did: str,
    ) -> None:
        super().__init__(coordinator, did, "cleaning_mode", "Cleaning Mode")

    @property
    def current_option(self) -> str | None:
        props = self.coordinator.data.get("properties", {})
        value = props.get((3, 1))
        if value is None:
            return None
        return CLEANING_MODE_VALUE_TO_LABEL.get(value)

    async def async_select_option(self, option: str) -> None:
        value = CLEANING_MODE_LABEL_TO_VALUE.get(option)
        if value is None:
            _LOGGER.warning("Unknown cleaning mode option: %s", option)
            return
        try:
            await self.coordinator.client.set_property(3, 1, value)
        except MovaAuthError as err:
            raise HomeAssistantError(f"Authentication failed while setting cleaning mode: {err}") from err
        except MovaApiError as err:
            raise HomeAssistantError(f"Failed to set cleaning mode: {err}") from err
        await self.coordinator.async_request_refresh()


class MovaPropertySelect(MovaBaseEntity, SelectEntity):
    """A curated, writable enum declared by the LR10 app plugin."""

    def __init__(self, coordinator, did: str, key: str, name: str,
                 siid: int, piid: int, values: dict[int, str], icon: str) -> None:
        super().__init__(coordinator, did, key, name)
        self._siid = siid
        self._piid = piid
        self._values = values
        self._attr_options = list(values.values())
        self._attr_icon = icon

    @property
    def available(self) -> bool:
        value = (self.coordinator.data or {}).get("properties", {}).get((self._siid, self._piid))
        return super().available and value in self._values

    @property
    def current_option(self) -> str | None:
        value = (self.coordinator.data or {}).get("properties", {}).get((self._siid, self._piid))
        return self._values.get(value)

    async def async_select_option(self, option: str) -> None:
        value = next((number for number, label in self._values.items() if label == option), None)
        if value is None:
            raise HomeAssistantError(f"Unsupported {self.name} option")
        try:
            await self.coordinator.client.set_property(self._siid, self._piid, value)
        except (MovaAuthError, MovaApiError) as err:
            raise HomeAssistantError(f"Could not set {self.name}: {err}") from err
        await self.coordinator.async_request_refresh()
