import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MovaApiClient, MovaApiError, MovaAuthError
from .const import CONF_REFRESH_TOKEN, READABLE_PROPERTIES, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class MovaLitterboxCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: MovaApiClient,
        entry: ConfigEntry,
        timezone: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="MOVA Litter Box",
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client
        self._entry = entry
        self.timezone = timezone
        self.device_info: dict[str, Any] = {}
        self.pet_info: list[dict[str, Any]] = []

    async def async_setup(self) -> None:
        """Fetch device and pet info once during setup."""
        self.device_info = await self.client.get_device_info()
        self.pet_info = await self.client.get_pet_info()

    def _today_str(self) -> str:
        return datetime.now(tz=ZoneInfo(self.timezone)).strftime("%Y/%m/%d")

    def _persist_refresh_token(self) -> None:
        """Save the current refresh token to config entry if it changed."""
        current = self._entry.data.get(CONF_REFRESH_TOKEN)
        if self.client.refresh_token_value and self.client.refresh_token_value != current:
            new_data = {**self._entry.data, CONF_REFRESH_TOKEN: self.client.refresh_token_value}
            self.hass.config_entries.async_update_entry(self._entry, data=new_data)

    def _build_pet_avatar_map(self) -> dict[str, str]:
        """Build a mapping of pet_id -> avatar URL from pet_info."""
        avatars: dict[str, str] = {}
        for pet in self.pet_info:
            pet_id = str(pet.get("id", ""))
            avatar = pet.get("petAvatar", "")
            if pet_id and avatar:
                avatars[pet_id] = avatar
        return avatars

    @staticmethod
    def _extract_latest_weights(
        visit_details: list[dict[str, Any]],
    ) -> dict[str, int]:
        """Get the most recent weight per pet from visit details.

        Visit details are ordered newest-first, so the first occurrence
        of each petId with a weight value is the latest.
        """
        weights: dict[str, int] = {}
        for visit in visit_details:
            pet_id = str(visit.get("petId", ""))
            weight = visit.get("weight")
            if pet_id and weight is not None and pet_id not in weights:
                weights[pet_id] = weight
        return weights

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            self.pet_info = await self.client.get_pet_info()

            properties = await self.client.get_properties(READABLE_PROPERTIES)
            visit_summary = await self.client.get_visit_summary(
                self._today_str(), self.timezone
            )
            consumables = await self.client.get_consumables()
            visit_details = await self.client.get_visit_details(
                self._today_str(), self.timezone, page=1, page_size=50
            )

            last_visit = visit_details[0] if visit_details else None
            latest_weights = self._extract_latest_weights(visit_details)
            pet_avatars = self._build_pet_avatar_map()

            self._persist_refresh_token()

            return {
                "properties": properties,
                "visit_summary": visit_summary,
                "consumables": consumables,
                "last_visit": last_visit,
                "visit_details": visit_details,
                "latest_weights": latest_weights,
                "pet_avatars": pet_avatars,
            }
        except MovaAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except MovaApiError as err:
            raise UpdateFailed(f"API error: {err}") from err
