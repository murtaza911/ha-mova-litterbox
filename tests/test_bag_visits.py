"""Bag visit accounting across ordinary polls and missed cloud days."""

import unittest
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from custom_components.mova_litterbox.coordinator import MovaLitterboxCoordinator


class FakeClient:
    def __init__(self, totals):
        self.totals = totals
        self.queried = []

    async def get_visit_summary(self, day, timezone):
        self.queried.append(day)
        return {"toiletsCount": self.totals[day]}


class FakeTracker:
    def __init__(self, observed, daily_count, visits, history):
        self.bag_replaced_at = datetime(2026, 11, 4, tzinfo=UTC)
        self._bag_observed_date = observed
        self._bag_observed_daily_count = daily_count
        self.bag_visits = visits
        self.timezone = "America/Toronto"
        self.client = FakeClient(history)
        self.saves = 0

    async def _async_save_bag_tracker(self):
        self.saves += 1


class BagVisitTests(unittest.IsolatedAsyncioTestCase):
    async def test_recent_rate_uses_complete_days_and_caches(self):
        today = date(2026, 11, 6)
        totals = {(today - timedelta(days=offset)).strftime("%Y/%m/%d"): 3
                  for offset in range(1, 15)}
        tracker = SimpleNamespace(client=FakeClient(totals), timezone="America/Toronto",
                                  _visit_rate_date=None, recent_visits_per_day=None)
        await MovaLitterboxCoordinator._async_refresh_visit_rate(tracker, today)
        await MovaLitterboxCoordinator._async_refresh_visit_rate(tracker, today)
        self.assertEqual(tracker.recent_visits_per_day, 3)
        self.assertEqual(len(tracker.client.queried), 14)

    async def test_estimate_uses_earlier_limit(self):
        tracker = SimpleNamespace(bag_age_days=4, bag_visits=10, bag_reminder_days=15,
                                  bag_reminder_visits=30, recent_visits_per_day=2.86,
                                  bag_reminder_due=False, bag_reminder_mode="Manual")
        estimate = MovaLitterboxCoordinator.bag_estimated_days_remaining.fget
        self.assertEqual(estimate(tracker), 7)
        tracker.bag_reminder_days = 9
        self.assertEqual(estimate(tracker), 5)
        tracker.bag_reminder_due = True
        self.assertEqual(estimate(tracker), 0)

    async def test_automatic_estimate_uses_actual_visits_and_recent_pace(self):
        tracker = SimpleNamespace(bag_age_days=3, bag_visits=9, bag_reminder_days=1,
                                  bag_reminder_visits=5, recent_visits_per_day=2.86,
                                  bag_reminder_due=False, bag_reminder_mode="Automatic")
        estimate = MovaLitterboxCoordinator.bag_estimated_days_remaining.fget
        self.assertEqual(estimate(tracker), 8)
        tracker.bag_visits = 30
        self.assertTrue(MovaLitterboxCoordinator.bag_reminder_due.fget(tracker))
        tracker.bag_reminder_due = True
        self.assertEqual(estimate(tracker), 0)

    async def test_replacement_date_backfills_each_day_once(self):
        today = datetime.now(ZoneInfo("America/Toronto")).date()
        replaced = today - timedelta(days=3)
        totals = {(replaced + timedelta(days=i)).strftime("%Y/%m/%d"): i + 1
                  for i in range(4)}

        class BackdatedTracker:
            timezone = "America/Toronto"
            data = None
            client = FakeClient(totals)
            saves = 0
            clears = 0
            notifications = 0

            async def _async_save_bag_tracker(self):
                self.saves += 1

            async def _async_clear_bag_notification(self):
                self.clears += 1

            async def _async_notify_bag_due(self):
                self.notifications += 1

        tracker = BackdatedTracker()
        await MovaLitterboxCoordinator.async_set_bag_replacement_date(tracker, replaced)
        self.assertEqual(tracker.bag_visits, 10)
        self.assertEqual(tracker._bag_observed_date, today)
        self.assertEqual(tracker._bag_observed_daily_count, 4)
        self.assertEqual(tracker.saves, 1)
        self.assertEqual(tracker.clears, 1)
        self.assertEqual(tracker.notifications, 1)
        self.assertEqual(len(tracker.client.queried), 4)

    async def test_typical_cycle_uses_visit_pace(self):
        tracker = SimpleNamespace(bag_reminder_days=15, bag_reminder_visits=30,
                                  recent_visits_per_day=2.86)
        estimate = MovaLitterboxCoordinator.bag_typical_cycle_days.fget
        self.assertEqual(estimate(tracker), 11)
        tracker.bag_reminder_days = 0
        self.assertEqual(estimate(tracker), 11)

    async def test_same_day_updates_only_new_visits(self):
        tracker = FakeTracker(date(2026, 11, 6), 4, 2, {})
        await MovaLitterboxCoordinator._async_update_bag_visits(
            tracker, date(2026, 11, 6), {"toiletsCount": 6}
        )
        self.assertEqual(tracker.bag_visits, 4)
        await MovaLitterboxCoordinator._async_update_bag_visits(
            tracker, date(2026, 11, 6), {"toiletsCount": 6}
        )
        self.assertEqual(tracker.bag_visits, 4)
        self.assertEqual(tracker.saves, 1)

    async def test_recovers_final_day_and_missed_day(self):
        tracker = FakeTracker(date(2026, 11, 4), 4, 2,
                              {"2026/11/04": 7, "2026/11/05": 3})
        await MovaLitterboxCoordinator._async_update_bag_visits(
            tracker, date(2026, 11, 6), {"toiletsCount": 1}
        )
        self.assertEqual(tracker.bag_visits, 9)
        self.assertEqual(tracker.client.queried, ["2026/11/04", "2026/11/05"])
        self.assertEqual(tracker._bag_observed_date, date(2026, 11, 6))

    async def test_failed_history_does_not_partially_advance(self):
        tracker = FakeTracker(date(2026, 11, 4), 4, 2, {"2026/11/04": 7})
        with self.assertRaises(KeyError):
            await MovaLitterboxCoordinator._async_update_bag_visits(
                tracker, date(2026, 11, 6), {"toiletsCount": 1}
            )
        self.assertEqual(tracker.bag_visits, 2)
        self.assertEqual(tracker._bag_observed_date, date(2026, 11, 4))
        self.assertEqual(tracker.saves, 0)


if __name__ == "__main__":
    unittest.main()
