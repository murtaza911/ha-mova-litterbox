import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import MovaApiError, MovaAuthError
from .const import CONF_DID
from .coordinator import MovaLitterboxCoordinator
from .entity import MovaBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MovaLitterboxCoordinator = entry.runtime_data
    did = entry.data[CONF_DID]

    async_add_entities([
        MovaDelayCleaningNumber(coordinator, did),
        MovaDeodorizingSprayDurationNumber(coordinator, did),
    ])


class MovaDelayCleaningNumber(MovaBaseEntity, NumberEntity):
    _attr_icon = "mdi:timer-sand"
    _attr_native_min_value = 0
    _attr_native_max_value = 30
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: MovaLitterboxCoordinator,
        did: str,
    ) -> None:
        super().__init__(coordinator, did, "delay_cleaning", "Delay Cleaning")

    @property
    def native_value(self) -> float | None:
        props = self.coordinator.data.get("properties", {})
        value = props.get((3, 11))
        if value is None:
            return None
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        try:
            await self.coordinator.client.set_property(3, 11, int(value))
        except MovaAuthError as err:
            raise HomeAssistantError(f"Authentication failed while setting delay cleaning: {err}") from err
        except MovaApiError as err:
            raise HomeAssistantError(f"Failed to set delay cleaning: {err}") from err
        await self.coordinator.async_request_refresh()


class MovaDeodorizingSprayDurationNumber(MovaBaseEntity, NumberEntity):
    _attr_icon = "mdi:spray"
    _attr_native_min_value = 1
    _attr_native_max_value = 60
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: MovaLitterboxCoordinator,
        did: str,
    ) -> None:
        super().__init__(
            coordinator, did, "deodorizing_spray_duration", "Deodorizing Spray Duration"
        )

    @property
    def native_value(self) -> float | None:
        props = self.coordinator.data.get("properties", {})
        value = props.get((3, 18))
        if value is None:
            return None
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        try:
            await self.coordinator.client.set_property(3, 18, int(value))
        except MovaAuthError as err:
            raise HomeAssistantError(f"Authentication failed while setting spray duration: {err}") from err
        except MovaApiError as err:
            raise HomeAssistantError(f"Failed to set spray duration: {err}") from err
        await self.coordinator.async_request_refresh()
