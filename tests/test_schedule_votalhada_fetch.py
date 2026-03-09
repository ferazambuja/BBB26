from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from schedule_votalhada_fetch import (
    SAO_PAULO_TZ,
    next_capture_hourly_in_brt,
    next_capture_in_brt,
    upcoming_slots,
)


def test_next_capture_monday_before_first_slot():
    now = datetime(2026, 3, 9, 0, 30, tzinfo=SAO_PAULO_TZ)  # Monday
    nxt = next_capture_in_brt(now)
    assert nxt == datetime(2026, 3, 9, 1, 0, tzinfo=SAO_PAULO_TZ)


def test_next_capture_monday_after_last_slot_rolls_to_tuesday():
    now = datetime(2026, 3, 9, 21, 5, tzinfo=SAO_PAULO_TZ)  # Monday
    nxt = next_capture_in_brt(now)
    assert nxt == datetime(2026, 3, 10, 8, 0, tzinfo=SAO_PAULO_TZ)


def test_next_capture_tuesday_after_last_slot_rolls_to_next_monday():
    now = datetime(2026, 3, 10, 21, 5, tzinfo=SAO_PAULO_TZ)  # Tuesday
    nxt = next_capture_in_brt(now)
    assert nxt == datetime(2026, 3, 16, 1, 0, tzinfo=SAO_PAULO_TZ)


def test_upcoming_slots_convert_to_new_york_timezone():
    local_tz = ZoneInfo("America/New_York")
    # 2026-03-09 13:00 UTC -> 10:00 in Sao Paulo on Monday.
    now_utc = datetime(2026, 3, 9, 13, 0, tzinfo=timezone.utc)
    slots = upcoming_slots(now_utc, local_tz, count=2, mode="windows")

    first_brt, first_local = slots[0]
    second_brt, second_local = slots[1]

    assert first_brt == datetime(2026, 3, 9, 12, 0, tzinfo=SAO_PAULO_TZ)
    assert first_local.hour == 11

    assert second_brt == datetime(2026, 3, 9, 15, 0, tzinfo=SAO_PAULO_TZ)
    assert second_local.hour == 14


def test_next_capture_hourly_in_brt():
    now = datetime(2026, 3, 9, 10, 39, 12, tzinfo=SAO_PAULO_TZ)
    nxt = next_capture_hourly_in_brt(now)
    assert nxt == datetime(2026, 3, 9, 11, 0, tzinfo=SAO_PAULO_TZ)


def test_upcoming_slots_hourly_mode():
    local_tz = ZoneInfo("America/New_York")
    now_utc = datetime(2026, 3, 9, 13, 39, tzinfo=timezone.utc)  # 10:39 BRT
    slots = upcoming_slots(now_utc, local_tz, count=3, mode="hourly")
    assert [s[0].hour for s in slots] == [11, 12, 13]
