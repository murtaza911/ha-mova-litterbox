"""Local waste bag replacement date for the MOVA litter box."""

from datetime import date

from homeassistant.components.date import DateEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MovaConfigEntry
from .api import MovaApiError, MovaAuthError
from .entity import MovaBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MovaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([MovaBagReplacementDate(entry.runtime_data, entry.data["did"])])


class MovaBagReplacementDate(MovaBaseEntity, DateEntity):
    """The day the current bag was installed, entered by the user."""

    _attr_icon = "mdi:calendar-check-outline"

    def __init__(self, coordinator, did: str) -> None:
        super().__init__(coordinator, did, "bag_replacement_date", "Bag Replacement Date")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> date | None:
        return self.coordinator.bag_replaced_date

    async def async_set_value(self, value: date) -> None:
        try:
            await self.coordinator.async_set_bag_replacement_date(value)
        except (ValueError, MovaApiError, MovaAuthError) as err:
            raise HomeAssistantError(f"Could not set waste bag replacement date: {err}") from err
