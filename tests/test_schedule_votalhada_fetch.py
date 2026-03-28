from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from schedule_votalhada_fetch import (
    SAO_PAULO_TZ,
    VOTALHADA_HOURS_FIRST_DAY,
    VOTALHADA_HOURS_OTHER_DAYS,
    _build_dynamic_schedule,
    next_capture_hourly_in_brt,
    next_capture_in_brt,
    upcoming_slots,
)


# --- Dynamic schedule builder ---

def test_build_dynamic_schedule_standard_cycle():
    """Standard Mon–Tue cycle: formation Sunday, elimination Tuesday."""
    paredao = {
        "data_formacao": "2026-03-22",
        "data": "2026-03-24",
        "status": "em_andamento",
    }
    sched = _build_dynamic_schedule(paredao)
    assert "2026-03-22" in sched  # Sun (formation day)
    assert "2026-03-23" in sched  # Mon
    assert "2026-03-24" in sched  # Tue (elimination day)
    # First day has 00:00 slot
    assert (0, 0) in sched["2026-03-22"]
    # Subsequent days start at 08:00
    assert (0, 0) not in sched["2026-03-23"]
    assert (8, 0) in sched["2026-03-23"]


def test_build_dynamic_schedule_turbo_clips_elimination_day():
    """Turbo P11: elimination at 14:55 — last day clipped."""
    paredao = {
        "data_formacao": "2026-03-27",
        "data": "2026-03-29",
        "hora_eliminacao": "14:55",
    }
    sched = _build_dynamic_schedule(paredao)
    assert len(sched) == 3  # Fri, Sat, Sun
    # Sunday: only hours before 14:55
    sun = sched["2026-03-29"]
    assert (8, 0) in sun
    assert (12, 0) in sun
    assert (15, 0) not in sun  # 15:00 >= 14:55
    assert (18, 0) not in sun
    assert (21, 0) not in sun


def test_build_dynamic_schedule_default_hora():
    """Without hora_eliminacao, defaults to 23:00 — all hours included."""
    paredao = {
        "data_formacao": "2026-03-22",
        "data": "2026-03-24",
    }
    sched = _build_dynamic_schedule(paredao)
    # Tue: all standard hours fit before 23:00
    assert (21, 0) in sched["2026-03-24"]


# --- next_capture_in_brt with dynamic schedule ---

def test_next_capture_with_schedule_first_slot():
    schedule = {
        "2026-03-27": [(0, 0), (8, 0), (12, 0)],
        "2026-03-28": [(8, 0), (12, 0)],
    }
    now = datetime(2026, 3, 27, 0, 30, tzinfo=SAO_PAULO_TZ)
    nxt = next_capture_in_brt(now, schedule)
    assert nxt == datetime(2026, 3, 27, 8, 0, tzinfo=SAO_PAULO_TZ)


def test_next_capture_rolls_to_next_day():
    schedule = {
        "2026-03-27": [(8, 0), (12, 0)],
        "2026-03-28": [(8, 0), (12, 0)],
    }
    now = datetime(2026, 3, 27, 12, 5, tzinfo=SAO_PAULO_TZ)
    nxt = next_capture_in_brt(now, schedule)
    assert nxt == datetime(2026, 3, 28, 8, 0, tzinfo=SAO_PAULO_TZ)


def test_next_capture_returns_none_after_last_slot():
    schedule = {
        "2026-03-29": [(8, 0), (12, 0)],
    }
    now = datetime(2026, 3, 29, 12, 5, tzinfo=SAO_PAULO_TZ)
    nxt = next_capture_in_brt(now, schedule)
    assert nxt is None


# --- upcoming_slots ---

def test_upcoming_slots_windows_mode():
    local_tz = ZoneInfo("America/New_York")
    schedule = {
        "2026-03-28": [(8, 0), (12, 0), (15, 0)],
        "2026-03-29": [(8, 0), (12, 0)],
    }
    # 2026-03-28 13:00 UTC → 10:00 BRT
    now_utc = datetime(2026, 3, 28, 13, 0, tzinfo=timezone.utc)
    slots = upcoming_slots(now_utc, local_tz, count=3, mode="windows", schedule=schedule)

    assert len(slots) == 3
    assert slots[0][0] == datetime(2026, 3, 28, 12, 0, tzinfo=SAO_PAULO_TZ)
    assert slots[1][0] == datetime(2026, 3, 28, 15, 0, tzinfo=SAO_PAULO_TZ)
    assert slots[2][0] == datetime(2026, 3, 29, 8, 0, tzinfo=SAO_PAULO_TZ)


def test_upcoming_slots_stops_when_no_more():
    local_tz = ZoneInfo("America/New_York")
    schedule = {
        "2026-03-29": [(8, 0)],
    }
    now_utc = datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)  # 09:00 BRT
    slots = upcoming_slots(now_utc, local_tz, count=5, mode="windows", schedule=schedule)
    # Only one slot left, should return just that
    # 09:00 BRT → next is... wait, 8:00 is before 09:00 so no slots
    assert len(slots) == 0


# --- Hourly mode (unchanged) ---

def test_next_capture_hourly_in_brt():
    now = datetime(2026, 3, 9, 10, 39, 12, tzinfo=SAO_PAULO_TZ)
    nxt = next_capture_hourly_in_brt(now)
    assert nxt == datetime(2026, 3, 9, 11, 0, tzinfo=SAO_PAULO_TZ)


def test_upcoming_slots_hourly_mode():
    local_tz = ZoneInfo("America/New_York")
    now_utc = datetime(2026, 3, 9, 13, 39, tzinfo=timezone.utc)  # 10:39 BRT
    slots = upcoming_slots(now_utc, local_tz, count=3, mode="hourly")
    assert [s[0].hour for s in slots] == [11, 12, 13]
