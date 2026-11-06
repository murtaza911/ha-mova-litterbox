"""On-demand cycle controls confirmed for the MOVA q2504w litter box."""

from homeassistant.components.button import ButtonEntity
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
    coordinator = entry.runtime_data
    async_add_entities(
        MovaCycleButton(coordinator, entry.data["did"], key, name, aiid, icon, statuses)
        for key, name, aiid, icon, statuses in (
            ("start_cleaning", "Start Cleaning", 1, "mdi:broom", {0}),
            ("start_emptying", "Start Emptying", 2, "mdi:delete-empty", {0}),
            ("start_leveling", "Start Leveling", 3, "mdi:format-line-spacing", {0}),
            ("pause", "Pause", 5, "mdi:pause", {1, 3, 5}),
            ("resume", "Resume", 6, "mdi:play", {2, 4, 6}),
            ("stop", "Stop", 4, "mdi:stop", {1, 2, 3, 4, 5, 6}),
        )
    )


class MovaCycleButton(MovaBaseEntity, ButtonEntity):
    """Start a confirmed litter-box cycle on demand."""

    def __init__(self, coordinator, did: str, key: str, name: str, aiid: int,
                 icon: str, statuses: set[int]) -> None:
        super().__init__(coordinator, did, key, name)
        self._aiid = aiid
        self._statuses = statuses
        self._attr_icon = icon

    @property
    def available(self) -> bool:
        status = (self.coordinator.data or {}).get("properties", {}).get((2, 1))
        return super().available and status in self._statuses

    async def async_press(self) -> None:
        if not self.available:
            raise HomeAssistantError(f"{self.name} is unavailable in the current device state")
        try:
            await self.coordinator.client.call_action(3, self._aiid)
        except (MovaApiError, MovaAuthError) as err:
            raise HomeAssistantError(f"Could not run {self.name}: {err}") from err
        await self.coordinator.async_request_refresh()
