from datetime import date

import pytest

from app.dhis2 import (
    DATA_ELEMENTS,
    DATA_SET_ID,
    current_week,
    data_value_set,
    metadata_payload,
    parse_week,
    week_values,
)

ROWS = [
    {"iso_week": "2026-W44", "sessions_completed": 2, "level_green": 1, "level_orange": 0,
     "level_red": 1, "sessions_started": 3, "alerts_sent": 1},
    {"iso_week": "2026-W45", "sessions_completed": 5, "level_green": 3, "level_orange": 1,
     "level_red": 1, "sessions_started": 6, "alerts_sent": 1},
]  # fmt: skip


@pytest.mark.parametrize(
    "week, period", [("2026-W45", "2026W45"), ("2026-W01", "2026W1"), ("2026-W53", "2026W53")]
)
def test_parse_week(week, period):
    assert parse_week(week) == period


@pytest.mark.parametrize("bad", ["2026W45", "2026-W00", "2026-W54", "2026-45", "W45", ""])
def test_parse_week_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        parse_week(bad)


def test_current_week_uses_iso_calendar():
    assert current_week(date(2026, 11, 1)) == "2026-W44"  # Sunday
    assert current_week(date(2026, 11, 2)) == "2026-W45"  # Monday
    assert current_week(date(2027, 1, 1)) == "2026-W53"


def test_week_values_picks_the_week_and_only_the_four_indicators():
    assert week_values(ROWS, "2026-W45") == {
        "sessions_completed": 5, "level_green": 3, "level_orange": 1, "level_red": 1,
    }  # fmt: skip


def test_week_without_sessions_sends_zeros():
    assert set(week_values(ROWS, "2026-W40").values()) == {0}


def test_data_value_set():
    payload = data_value_set("2026-W45", week_values(ROWS, "2026-W45"), "OU123456789")
    assert payload["dataSet"] == DATA_SET_ID
    assert payload["period"] == "2026W45"
    assert payload["orgUnit"] == "OU123456789"
    assert {"dataElement": "SuNoDEcmp01", "value": "5"} in payload["dataValues"]
    assert len(payload["dataValues"]) == 4


def test_metadata_payload_has_four_weekly_aggregate_elements():
    meta = metadata_payload("OU123456789")
    assert len(meta["dataElements"]) == 4
    assert all(de["domainType"] == "AGGREGATE" for de in meta["dataElements"])
    data_set = meta["dataSets"][0]
    assert data_set["name"] == "SuNoogo perinatal screening"
    assert data_set["periodType"] == "Weekly"
    assert data_set["organisationUnits"] == [{"id": "OU123456789"}]
    assert len(data_set["dataSetElements"]) == 4


def test_uids_are_valid_dhis2_identifiers():
    uids = [DATA_SET_ID] + [uid for uid, _ in DATA_ELEMENTS.values()]
    assert all(len(u) == 11 and u[0].isalpha() and u.isalnum() for u in uids)
    assert len(set(uids)) == len(uids)
