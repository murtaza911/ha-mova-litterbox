import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import MovaApiError, MovaAuthError
from .const import CONF_DID, PROPERTY_DEFINITIONS, SWITCH_ICONS, SWITCH_PROPERTIES
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

    entities = [
        MovaSettingSwitch(coordinator, did, siid, piid)
        for siid, piid in SWITCH_PROPERTIES
    ]
    async_add_entities(entities)


class MovaSettingSwitch(MovaBaseEntity, SwitchEntity):
    def __init__(
        self,
        coordinator: MovaLitterboxCoordinator,
        did: str,
        siid: int,
        piid: int,
    ) -> None:
        prop_def = PROPERTY_DEFINITIONS[(siid, piid)]
        super().__init__(coordinator, did, prop_def[0], prop_def[1])
        self._siid = siid
        self._piid = piid
        self._attr_icon = SWITCH_ICONS.get((siid, piid))

    @property
    def is_on(self) -> bool | None:
        props = self.coordinator.data.get("properties", {})
        value = props.get((self._siid, self._piid))
        if value is None:
            return None
        return bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.client.set_property(self._siid, self._piid, 1)
        except MovaAuthError as err:
            raise HomeAssistantError(f"Authentication failed while turning on {self.name}: {err}") from err
        except MovaApiError as err:
            raise HomeAssistantError(f"Failed to turn on {self.name}: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.client.set_property(self._siid, self._piid, 0)
        except MovaAuthError as err:
            raise HomeAssistantError(f"Authentication failed while turning off {self.name}: {err}") from err
        except MovaApiError as err:
            raise HomeAssistantError(f"Failed to turn off {self.name}: {err}") from err
        await self.coordinator.async_request_refresh()
