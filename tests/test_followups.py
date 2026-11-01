from datetime import date

from app.followups import format_followups

TODAY = date(2026, 11, 19)


def test_no_followup_due():
    assert format_followups([], TODAY) == "No follow-up due on 2026-11-19."


def test_lists_due_followups_by_code_only():
    rows = [
        {"woman_code": "F-0007", "followup_due": "2026-11-19", "chw_phone": "+22670000000",
         "completed_at": "2026-11-05T10:00:00+00:00"},
    ]  # fmt: skip
    text = format_followups(rows, TODAY)
    assert text.splitlines()[0] == "1 follow-up(s) due on 2026-11-19:"
    assert "F-0007" in text and "+22670000000" in text
