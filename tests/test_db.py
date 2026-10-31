from datetime import date, datetime, timezone

from app.db import session_row
from app.flow import Session, State
from app.scoring import evaluate

SID = "6f1d2c1e-0000-4000-8000-000000000000"


def test_row_for_session_in_progress():
    session = Session(woman_code="F-0042", state=State.QUESTIONS, consent=True, answers=(2, 3))
    assert session_row(SID, "+22670000000", session) == {
        "id": SID,
        "chw_phone": "+22670000000",
        "woman_code": "F-0042",
        "consent": True,
        "answers": [2, 3],
        "safety_flag": None,
    }


def test_row_for_completed_orange_session():
    answers = (3, 3, 3, 3, 3, 1)
    session = Session(
        woman_code="F-0042",
        state=State.COMPLETED,
        consent=True,
        answers=answers,
        safety_flag=False,
        result=evaluate(answers, False),
    )
    completed_at = datetime(2026, 11, 5, 18, 30, tzinfo=timezone.utc)
    row = session_row(SID, "+22670000000", session, completed_at, date(2026, 11, 19))
    assert row["score"] == 10
    assert row["level"] == "orange"
    assert row["safety_flag"] is False
    assert row["completed_at"] == "2026-11-05T18:30:00+00:00"
    assert row["followup_due"] == "2026-11-19"


def test_row_never_contains_free_text_fields():
    session = Session(woman_code="F-0042", consent=True)
    assert set(session_row(SID, "+22670000000", session)) <= {
        "id", "chw_phone", "woman_code", "consent", "answers", "score", "level",
        "safety_flag", "completed_at", "followup_due",
    }  # fmt: skip
