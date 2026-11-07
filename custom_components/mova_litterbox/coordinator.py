import logging
import math
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store

from .api import MovaApiClient, MovaApiError, MovaAuthError
from .const import CONF_REFRESH_TOKEN, READABLE_PROPERTIES, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)
AUTO_BAG_VISIT_TARGET = 30


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
        self._update_count = 0
        self._bag_store = Store(hass, 1, f"mova_litterbox_bag_{entry.data['did']}")
        self.bag_replaced_at: datetime | None = None
        self.bag_reminder_days = 15
        self.bag_reminder_visits = 30
        self.bag_reminder_mode = "Automatic"
        self.bag_visits: int | None = None
        self._bag_observed_date: date | None = None
        self._bag_observed_daily_count: int | None = None
        self._bag_notified = False
        self.recent_visits_per_day: float | None = None
        self._visit_rate_date: date | None = None

    async def async_load_bag_tracker(self) -> None:
        """Restore the locally tracked bag replacement date and reminder."""
        saved = await self._bag_store.async_load() or {}
        raw_date = saved.get("replaced_at")
        if raw_date:
            try:
                parsed = datetime.fromisoformat(raw_date)
                if parsed.tzinfo is not None and parsed <= datetime.now(UTC):
                    self.bag_replaced_at = parsed
            except (TypeError, ValueError):
                _LOGGER.warning("Ignoring invalid stored bag replacement date")
        days = saved.get("reminder_days", 15)
        if isinstance(days, int) and 0 <= days <= 90:
            self.bag_reminder_days = days
        visits = saved.get("reminder_visits", 30)
        if isinstance(visits, int) and 1 <= visits <= 200:
            self.bag_reminder_visits = visits
        if saved.get("reminder_mode") in ("Automatic", "Manual"):
            self.bag_reminder_mode = saved["reminder_mode"]
        count = saved.get("visits")
        if self.bag_replaced_at and isinstance(count, int) and count >= 0:
            self.bag_visits = count
        raw_observed_date = saved.get("observed_date")
        if raw_observed_date:
            try:
                self._bag_observed_date = date.fromisoformat(raw_observed_date)
            except (TypeError, ValueError):
                _LOGGER.warning("Ignoring invalid stored bag visit date")
        daily_count = saved.get("observed_daily_count")
        if isinstance(daily_count, int) and daily_count >= 0:
            self._bag_observed_daily_count = daily_count
        self._bag_notified = saved.get("notified", False) is True

    async def _async_save_bag_tracker(self) -> None:
        await self._bag_store.async_save({
            "replaced_at": self.bag_replaced_at.isoformat() if self.bag_replaced_at else None,
            "reminder_days": self.bag_reminder_days,
            "reminder_visits": self.bag_reminder_visits,
            "reminder_mode": self.bag_reminder_mode,
            "visits": self.bag_visits,
            "observed_date": self._bag_observed_date.isoformat() if self._bag_observed_date else None,
            "observed_daily_count": self._bag_observed_daily_count,
            "notified": self._bag_notified,
        })

    @property
    def bag_age_days(self) -> int | None:
        if self.bag_replaced_at is None:
            return None
        return max(0, (datetime.now(ZoneInfo(self.timezone)).date()
                       - self.bag_replaced_at.astimezone(ZoneInfo(self.timezone)).date()).days)

    @property
    def bag_replaced_date(self) -> date | None:
        if self.bag_replaced_at is None:
            return None
        return self.bag_replaced_at.astimezone(ZoneInfo(self.timezone)).date()

    @property
    def bag_reminder_due(self) -> bool | None:
        age = self.bag_age_days
        if age is None:
            return None
        if self.bag_reminder_mode == "Automatic":
            return self.bag_visits >= AUTO_BAG_VISIT_TARGET if self.bag_visits is not None else None
        if self.bag_reminder_days > 0 and age >= self.bag_reminder_days:
            return True
        if self.bag_visits is None:
            return None
        return self.bag_visits >= self.bag_reminder_visits

    @property
    def bag_estimated_days_remaining(self) -> int | None:
        """Estimate remaining calendar days for the selected reminder mode."""
        age = self.bag_age_days
        if age is None or self.bag_visits is None:
            return None
        if self.bag_reminder_due:
            return 0
        if self.bag_reminder_mode == "Automatic":
            if not self.recent_visits_per_day or self.recent_visits_per_day <= 0:
                return None
            return math.ceil(max(0, AUTO_BAG_VISIT_TARGET - self.bag_visits)
                             / self.recent_visits_per_day)
        candidates: list[int] = []
        if self.bag_reminder_days > 0:
            candidates.append(max(0, self.bag_reminder_days - age))
        if self.recent_visits_per_day and self.recent_visits_per_day > 0:
            remaining_visits = max(0, self.bag_reminder_visits - self.bag_visits)
            candidates.append(math.ceil(remaining_visits / self.recent_visits_per_day))
        return min(candidates) if candidates else None

    @property
    def bag_typical_cycle_days(self) -> int | None:
        """Expected interval for a fresh bag at the recent visit pace."""
        candidates: list[int] = []
        if self.bag_reminder_days > 0:
            candidates.append(self.bag_reminder_days)
        if self.recent_visits_per_day and self.recent_visits_per_day > 0:
            candidates.append(math.ceil(self.bag_reminder_visits / self.recent_visits_per_day))
        return min(candidates) if candidates else None

    @property
    def bag_estimated_date(self) -> str | None:
        remaining = self.bag_estimated_days_remaining
        if remaining is None:
            return None
        today = datetime.now(ZoneInfo(self.timezone)).date()
        return (today + timedelta(days=remaining)).isoformat()

    async def _async_refresh_visit_rate(self, today: date) -> None:
        """Read the last 14 complete days once per day for the bag estimate."""
        if self._visit_rate_date == today:
            return
        total = 0
        for days_ago in range(1, 15):
            day = today - timedelta(days=days_ago)
            summary = await self.client.get_visit_summary(day.strftime("%Y/%m/%d"), self.timezone)
            count = summary.get("toiletsCount") if isinstance(summary, dict) else None
            if not isinstance(count, int) or count < 0:
                raise MovaApiError(f"No visit total for {day.isoformat()}")
            total += count
        self.recent_visits_per_day = round(total / 14, 2)
        self._visit_rate_date = today

    async def async_mark_bag_replaced(self) -> None:
        self.bag_replaced_at = datetime.now(UTC)
        today = datetime.now(ZoneInfo(self.timezone)).date()
        summary = (self.data or {}).get("visit_summary", {}) if self.last_update_success else {}
        try:
            summary = await self.client.get_visit_summary(today.strftime("%Y/%m/%d"), self.timezone)
        except (MovaApiError, ClientError, TimeoutError) as err:
            _LOGGER.warning("Could not read visit baseline at bag replacement: %s", err)
        current = summary.get("toiletsCount") if isinstance(summary, dict) else None
        self._bag_observed_date = today
        self._bag_observed_daily_count = current if isinstance(current, int) and current >= 0 else None
        self.bag_visits = 0 if self._bag_observed_daily_count is not None else None
        self._bag_notified = False
        await self._async_save_bag_tracker()
        await self.hass.services.async_call(
            "persistent_notification", "dismiss",
            {"notification_id": f"mova_litterbox_bag_{self._entry.data['did']}"},
        )
        if self.data:
            self.async_update_listeners()

    async def async_set_bag_replacement_date(self, replaced_on: date) -> None:
        """Backfill visits from a user supplied local replacement date."""
        today = datetime.now(ZoneInfo(self.timezone)).date()
        if replaced_on > today or (today - replaced_on).days > 90:
            raise ValueError("Replacement date must be within the last 90 days")
        total = 0
        current = None
        for offset in range((today - replaced_on).days + 1):
            day = replaced_on + timedelta(days=offset)
            summary = await self.client.get_visit_summary(day.strftime("%Y/%m/%d"), self.timezone)
            count = summary.get("toiletsCount") if isinstance(summary, dict) else None
            if not isinstance(count, int) or count < 0:
                raise MovaApiError(f"No visit total for {day.isoformat()}")
            total += count
            if day == today:
                current = count
        self.bag_replaced_at = datetime(replaced_on.year, replaced_on.month, replaced_on.day,
                                        tzinfo=ZoneInfo(self.timezone)).astimezone(UTC)
        self.bag_visits = total
        self._bag_observed_date = today
        self._bag_observed_daily_count = current
        self._bag_notified = False
        await self._async_save_bag_tracker()
        await self._async_clear_bag_notification()
        if self.data:
            self.async_update_listeners()
        await self._async_notify_bag_due()

    async def _async_clear_bag_notification(self) -> None:
        await self.hass.services.async_call(
            "persistent_notification", "dismiss",
            {"notification_id": f"mova_litterbox_bag_{self._entry.data['did']}"},
        )

    async def async_set_bag_reminder_mode(self, mode: str) -> None:
        if mode not in ("Automatic", "Manual"):
            raise ValueError("Unsupported bag reminder mode")
        if mode == self.bag_reminder_mode:
            return
        self.bag_reminder_mode = mode
        self._bag_notified = False
        await self._async_save_bag_tracker()
        await self._async_clear_bag_notification()
        if self.data:
            self.async_update_listeners()
        await self._async_notify_bag_due()

    async def async_set_bag_reminder_days(self, days: int) -> None:
        self.bag_reminder_days = days
        self._bag_notified = False
        await self._async_save_bag_tracker()
        await self._async_clear_bag_notification()
        if self.data:
            self.async_update_listeners()
        await self._async_notify_bag_due()

    async def async_set_bag_reminder_visits(self, visits: int) -> None:
        self.bag_reminder_visits = visits
        self._bag_notified = False
        await self._async_save_bag_tracker()
        await self._async_clear_bag_notification()
        if self.data:
            self.async_update_listeners()
        await self._async_notify_bag_due()

    async def _async_update_bag_visits(self, today: date, summary: dict[str, Any]) -> None:
        """Reconcile daily cloud totals, including any days missed while offline."""
        if self.bag_replaced_at is None:
            return
        current = summary.get("toiletsCount") if isinstance(summary, dict) else None
        if not isinstance(current, int) or current < 0:
            return
        observed = self._bag_observed_date
        previous = self._bag_observed_daily_count
        if observed is None or previous is None or observed > today:
            self._bag_observed_date = today
            self._bag_observed_daily_count = current
            self.bag_visits = self.bag_visits or 0
            await self._async_save_bag_tracker()
            return
        added = 0
        if observed == today:
            added = max(0, current - previous)
        else:
            cursor = observed
            while cursor < today:
                final = await self.client.get_visit_summary(cursor.strftime("%Y/%m/%d"), self.timezone)
                final_count = final.get("toiletsCount") if isinstance(final, dict) else None
                if not isinstance(final_count, int) or final_count < 0:
                    raise MovaApiError(f"No visit total for {cursor.isoformat()}")
                added += max(0, final_count - previous) if cursor == observed else final_count
                cursor += timedelta(days=1)
            added += current
        if added or observed != today or previous != current:
            self.bag_visits = (self.bag_visits or 0) + added
            self._bag_observed_date = today
            self._bag_observed_daily_count = current
            await self._async_save_bag_tracker()

    async def _async_notify_bag_due(self) -> None:
        if self.bag_reminder_due is not True or self._bag_notified:
            return
        visits_text = f"{self.bag_visits} visits" if self.bag_visits is not None else "visit count unavailable"
        await self.hass.services.async_call(
            "persistent_notification", "create",
            {
                "title": "Litter box bag reminder",
                "message": f"Replace the MOVA waste bag. It has {visits_text} over {self.bag_age_days} days since the last change ({self.bag_reminder_mode.lower()} reminder).",
                "notification_id": f"mova_litterbox_bag_{self._entry.data['did']}",
            },
        )
        self._bag_notified = True
        await self._async_save_bag_tracker()

    async def async_check_bag_reminder(self, _: datetime) -> None:
        """Refresh local reminder state even when MOVA cloud polling fails."""
        if self.data:
            self.async_update_listeners()
        await self._async_notify_bag_due()

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
            try:
                await self._async_update_bag_visits(
                    datetime.now(ZoneInfo(self.timezone)).date(), visit_summary
                )
            except (MovaApiError, ClientError, TimeoutError) as err:
                _LOGGER.warning("Could not reconcile bag visit count; will retry: %s", err)
            consumables = await self.client.get_consumables()
            visit_details = await self.client.get_visit_details(
                self._today_str(), self.timezone, page=1, page_size=50
            )
            try:
                await self._async_refresh_visit_rate(datetime.now(ZoneInfo(self.timezone)).date())
            except (MovaApiError, ClientError, TimeoutError) as err:
                _LOGGER.debug("Could not refresh recent MOVA visit rate: %s", err)

            abnormalities = self.data.get("abnormalities") if self.data else None
            model = self.device_info.get("model")
            if model and self._update_count % 5 == 0:
                try:
                    abnormalities = await self.client.get_abnormalities(model)
                except (MovaApiError, ClientError, TimeoutError) as err:
                    _LOGGER.debug("Could not read MOVA pet abnormalities: %s", err)
            self._update_count += 1

            last_visit = visit_details[0] if visit_details else None
            latest_weights = self._extract_latest_weights(visit_details)
            pet_avatars = self._build_pet_avatar_map()

            self._persist_refresh_token()
            await self._async_notify_bag_due()

            return {
                "properties": properties,
                "visit_summary": visit_summary,
                "consumables": consumables,
                "last_visit": last_visit,
                "visit_details": visit_details,
                "latest_weights": latest_weights,
                "pet_avatars": pet_avatars,
                "abnormalities": abnormalities,
            }
        except MovaAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except MovaApiError as err:
            raise UpdateFailed(f"API error: {err}") from err
