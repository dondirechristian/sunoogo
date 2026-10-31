from datetime import date

import pytest

from app.flow import (
    MESSAGE_KEYS,
    Effect,
    Session,
    State,
    Transition,
    followup_due_date,
    handle_message,
)
from app.scoring import Level


def run(messages: list[str], session: Session | None = None) -> list[Transition]:
    """Feed messages one by one and return every transition."""
    transitions = []
    for text in messages:
        t = handle_message(session, text)
        transitions.append(t)
        session = t.session
    return transitions


def session_at(messages: list[str]) -> Session:
    return run(messages)[-1].session


def all_effects(transitions: list[Transition]) -> list[Effect]:
    return [e for t in transitions for e in t.effects]


START = ["START F-0042"]
CONSENTED = START + ["1"]


# --- Starting a session -------------------------------------------------------------------


def test_start_sends_intro_and_consent_without_saving():
    t = handle_message(None, "START F-0042")
    assert t.replies == ("intro", "consent")
    assert t.effects == ()
    assert t.session == Session(woman_code="F-0042", state=State.AWAITING_CONSENT)


def test_start_is_case_and_whitespace_insensitive():
    t = handle_message(None, "  start   f-0042 \n")
    assert t.session.woman_code == "F-0042"


@pytest.mark.parametrize(
    "text",
    [
        "START",
        "START Awa",
        "START F-42",
        "START F-00421",
        "START 0042",
        "START F0042",
        "START F-0042 Awa",
        "START Awa F-0042",
        "START F-٠٠٤٢",  # non-ASCII digits
    ],
)
def test_start_rejects_invalid_codes(text):
    t = handle_message(None, text)
    assert t.replies == ("invalid_code",)
    assert t.session is None
    assert t.effects == ()


@pytest.mark.parametrize("text", ["", "   ", "bonjour", "1", "STOP", "F-0042"])
def test_idle_messages_get_help(text):
    t = handle_message(None, text)
    assert t.replies == ("help",)
    assert t.session is None
    assert t.effects == ()


def test_start_during_active_session_is_rejected():
    session = session_at(CONSENTED + ["3"])
    t = handle_message(session, "START F-0001")
    assert t.replies == ("session_in_progress",)
    assert t.session == session
    assert t.effects == ()


@pytest.mark.parametrize("state", [State.COMPLETED, State.REFUSED, State.STOPPED])
def test_terminal_session_is_treated_as_idle(state):
    old = Session(woman_code="F-0042", state=state)
    assert handle_message(old, "1").replies == ("help",)
    t = handle_message(old, "START F-0043")
    assert t.session == Session(woman_code="F-0043")


# --- Consent ------------------------------------------------------------------------------


def test_consent_accept_saves_and_asks_first_question():
    t = run(CONSENTED)[-1]
    assert t.replies == ("choices", "q1")
    assert t.effects == (Effect.SAVE_SESSION,)
    assert t.session.consent is True
    assert t.session.state is State.QUESTIONS


def test_consent_refused_ends_politely_and_stores_nothing():
    transitions = run(START + ["2"])
    assert transitions[-1].replies == ("consent_refused",)
    assert transitions[-1].session.state is State.REFUSED
    assert all_effects(transitions) == []


@pytest.mark.parametrize("text", ["0", "3", "oui", "1 2", "", "11"])
def test_invalid_consent_reply_repeats_consent(text):
    session = session_at(START)
    t = handle_message(session, text)
    assert t.replies == ("consent",)
    assert t.session == session
    assert t.effects == ()


# --- K6 questions -------------------------------------------------------------------------


def test_each_answer_asks_the_next_question_and_saves():
    transitions = run(CONSENTED + ["1", "2", "3", "4", "5", "1"])[2:]
    assert [t.replies for t in transitions] == [
        ("q2",),
        ("q3",),
        ("q4",),
        ("q5",),
        ("q6",),
        ("safety",),
    ]
    assert all(t.effects == (Effect.SAVE_SESSION,) for t in transitions)
    assert transitions[-1].session.answers == (1, 2, 3, 4, 5, 1)
    assert transitions[-1].session.state is State.SAFETY


@pytest.mark.parametrize("answered", range(0, 6))
@pytest.mark.parametrize("text", ["0", "6", "9", "12", "abc", "1 2", "", "-1"])
def test_invalid_answer_replays_choices_without_advancing(answered, text):
    session = session_at(CONSENTED + ["3"] * answered)
    t = handle_message(session, text)
    assert t.replies == ("choices", f"q{answered + 1}")
    assert t.session == session
    assert t.effects == ()


def test_answer_with_surrounding_whitespace_is_accepted():
    session = session_at(CONSENTED)
    t = handle_message(session, " 4\n")
    assert t.session.answers == (4,)


# --- Safety question and result -----------------------------------------------------------


@pytest.mark.parametrize("text", ["0", "3", "oui", ""])
def test_invalid_safety_reply_repeats_safety(text):
    session = session_at(CONSENTED + ["1"] * 6)
    t = handle_message(session, text)
    assert t.replies == ("safety",)
    assert t.session == session
    assert t.effects == ()


def test_full_session_green():
    t = run(CONSENTED + ["1"] * 6 + ["1"])[-1]
    assert t.replies == ("result_green", "thanks")
    assert t.effects == (Effect.SAVE_SESSION,)
    assert t.session.state is State.COMPLETED
    assert t.session.result.score == 0
    assert t.session.result.level is Level.GREEN
    assert t.session.safety_flag is False


def test_full_session_orange_schedules_followup():
    t = run(CONSENTED + ["3", "3", "3", "3", "3", "1"] + ["1"])[-1]
    assert t.session.result.score == 10
    assert t.replies == ("result_orange", "thanks")
    assert t.effects == (Effect.SAVE_SESSION, Effect.SCHEDULE_FOLLOWUP)


def test_full_session_red_by_score_sends_alert():
    t = run(CONSENTED + ["5"] * 6 + ["1"])[-1]
    assert t.session.result.score == 24
    assert t.replies == ("result_red", "thanks")
    assert t.effects == (Effect.SAVE_SESSION, Effect.SEND_ALERT)


def test_positive_safety_with_zero_score_is_red_and_alerts():
    t = run(CONSENTED + ["1"] * 6 + ["2"])[-1]
    assert t.session.result.score == 0
    assert t.session.result.level is Level.RED
    assert t.session.safety_flag is True
    assert t.replies == ("result_red", "thanks")
    assert t.effects == (Effect.SAVE_SESSION, Effect.SEND_ALERT)


@pytest.mark.parametrize(
    "answers, expected",
    [
        (["2", "2", "2", "2", "2", "3"], Level.GREEN),  # 7
        (["2", "2", "2", "2", "3", "3"], Level.ORANGE),  # 8
        (["3", "3", "3", "3", "3", "3"], Level.ORANGE),  # 12
        (["3", "3", "3", "3", "3", "4"], Level.RED),  # 13
    ],
)
def test_thresholds_through_the_flow(answers, expected):
    t = run(CONSENTED + answers + ["1"])[-1]
    assert t.session.result.level is expected


# --- STOP ---------------------------------------------------------------------------------


def test_stop_before_consent_stores_nothing():
    transitions = run(START + ["STOP"])
    assert transitions[-1].replies == ("stop",)
    assert transitions[-1].session.state is State.STOPPED
    assert all_effects(transitions) == []


@pytest.mark.parametrize("answered", [0, 3, 6])
def test_stop_after_consent_saves_incomplete_session(answered):
    session = session_at(CONSENTED + ["2"] * answered)
    t = handle_message(session, " stop ")
    assert t.replies == ("stop",)
    assert t.effects == (Effect.SAVE_SESSION,)
    assert t.session.state is State.STOPPED
    assert t.session.result is None
    assert len(t.session.answers) == answered


def test_stop_followed_by_text_is_not_a_command():
    session = session_at(CONSENTED)
    assert handle_message(session, "STOP please").replies == ("choices", "q1")


# --- Misc ---------------------------------------------------------------------------------


def test_every_emitted_reply_is_a_known_message_key():
    transcripts = [
        ["hello", "START x", "START F-0001", "START F-0002", "9", "1", "x"] + ["4"] * 6 + ["9", "2"],
        START + ["2"],
        CONSENTED + ["STOP"],
        CONSENTED + ["3", "3", "3", "3", "3", "1", "1"],
        CONSENTED + ["1"] * 6 + ["1"],
    ]
    emitted = {key for msgs in transcripts for t in run(msgs) for key in t.replies}
    assert emitted <= set(MESSAGE_KEYS)
    assert emitted == set(MESSAGE_KEYS)


def test_followup_due_date_is_14_days_later():
    assert followup_due_date(date(2026, 11, 5)) == date(2026, 11, 19)
    assert followup_due_date(date(2026, 12, 25)) == date(2027, 1, 8)
