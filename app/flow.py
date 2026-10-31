"""Session state machine for one K6 screening conversation.

Pure module: given the current session and the incoming WhatsApp text, it returns the next
session, the message keys to send back and the side effects the caller (app/main.py) must
perform. No I/O, no network, no clock.

Privacy: nothing is persisted before consent. SAVE_SESSION is only emitted once the CHW has
answered 1 (accept) to the consent question.
"""

import re
from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import Enum

from app.scoring import NUM_QUESTIONS, Level, Result, evaluate, is_valid_choice

FOLLOWUP_DAYS = 14

# Strict format so that a CHW cannot type a woman's name in place of the code.
WOMAN_CODE_RE = re.compile(r"F-[0-9]{4}")
DIGIT_RE = re.compile(r"[0-9]")

CONSENT_ACCEPT, CONSENT_REFUSE = 1, 2
SAFETY_NO, SAFETY_YES = 1, 2

QUESTION_KEYS = tuple(f"q{n}" for n in range(1, NUM_QUESTIONS + 1))

# Every message key flow.py can emit. app/messages.py must provide a text for each of them.
MESSAGE_KEYS = (
    "help",
    "invalid_code",
    "session_in_progress",
    "intro",
    "consent",
    "consent_refused",
    "choices",
    *QUESTION_KEYS,
    "safety",
    "result_green",
    "result_orange",
    "result_red",
    "thanks",
    "stop",
)


class State(str, Enum):
    AWAITING_CONSENT = "awaiting_consent"
    QUESTIONS = "questions"
    SAFETY = "safety"
    COMPLETED = "completed"
    REFUSED = "refused"
    STOPPED = "stopped"


ACTIVE_STATES = frozenset({State.AWAITING_CONSENT, State.QUESTIONS, State.SAFETY})


class Effect(str, Enum):
    # Effects are listed in the order they must be performed.
    SAVE_SESSION = "save_session"  # upsert the session row
    SEND_ALERT = "send_alert"  # immediate WhatsApp alert to the referral nurse
    SCHEDULE_FOLLOWUP = "schedule_followup"  # set followup_due = followup_due_date(today)


@dataclass(frozen=True)
class Session:
    woman_code: str
    state: State = State.AWAITING_CONSENT
    consent: bool = False
    answers: tuple[int, ...] = ()  # raw choices 1..5, in question order
    safety_flag: bool | None = None
    result: Result | None = None

    @property
    def is_active(self) -> bool:
        return self.state in ACTIVE_STATES

    @property
    def current_question_key(self) -> str:
        return QUESTION_KEYS[len(self.answers)]


@dataclass(frozen=True)
class Transition:
    session: Session | None  # None or a terminal session means no conversation is open
    replies: tuple[str, ...]
    effects: tuple[Effect, ...] = ()


def handle_message(session: Session | None, text: str) -> Transition:
    tokens = (text or "").split()
    command = tokens[0].upper() if tokens else ""

    if session is None or not session.is_active:
        return _handle_idle(tokens, command)
    if command == "STOP" and len(tokens) == 1:
        return _stop(session)
    if command == "START":
        return Transition(session, ("session_in_progress",))

    digit = _parse_digit(tokens)
    if session.state is State.AWAITING_CONSENT:
        return _handle_consent(session, digit)
    if session.state is State.QUESTIONS:
        return _handle_question(session, digit)
    return _handle_safety(session, digit)


def followup_due_date(completed_on: date) -> date:
    return completed_on + timedelta(days=FOLLOWUP_DAYS)


def parse_woman_code(raw: str) -> str | None:
    code = raw.upper()
    return code if WOMAN_CODE_RE.fullmatch(code) else None


def _parse_digit(tokens: list[str]) -> int | None:
    if len(tokens) == 1 and DIGIT_RE.fullmatch(tokens[0]):
        return int(tokens[0])
    return None


def _handle_idle(tokens: list[str], command: str) -> Transition:
    if command != "START":
        return Transition(None, ("help",))
    code = parse_woman_code(tokens[1]) if len(tokens) == 2 else None
    if code is None:
        return Transition(None, ("invalid_code",))
    return Transition(Session(woman_code=code), ("intro", "consent"))


def _handle_consent(session: Session, digit: int | None) -> Transition:
    if digit == CONSENT_ACCEPT:
        accepted = replace(session, state=State.QUESTIONS, consent=True)
        return Transition(accepted, ("choices", QUESTION_KEYS[0]), (Effect.SAVE_SESSION,))
    if digit == CONSENT_REFUSE:
        return Transition(replace(session, state=State.REFUSED), ("consent_refused",))
    return Transition(session, ("consent",))


def _handle_question(session: Session, digit: int | None) -> Transition:
    if not is_valid_choice(digit):
        return Transition(session, ("choices", session.current_question_key))
    answers = session.answers + (digit,)
    if len(answers) == NUM_QUESTIONS:
        updated = replace(session, state=State.SAFETY, answers=answers)
        return Transition(updated, ("safety",), (Effect.SAVE_SESSION,))
    updated = replace(session, answers=answers)
    return Transition(updated, (updated.current_question_key,), (Effect.SAVE_SESSION,))


def _handle_safety(session: Session, digit: int | None) -> Transition:
    if digit == SAFETY_NO:
        return _complete(session, safety_positive=False)
    if digit == SAFETY_YES:
        return _complete(session, safety_positive=True)
    return Transition(session, ("safety",))


def _complete(session: Session, safety_positive: bool) -> Transition:
    result = evaluate(session.answers, safety_positive)
    completed = replace(
        session, state=State.COMPLETED, safety_flag=safety_positive, result=result
    )
    effects = [Effect.SAVE_SESSION]
    if result.level is Level.RED:
        effects.append(Effect.SEND_ALERT)
    elif result.level is Level.ORANGE:
        effects.append(Effect.SCHEDULE_FOLLOWUP)
    return Transition(completed, (f"result_{result.level.value}", "thanks"), tuple(effects))


def _stop(session: Session) -> Transition:
    # Before consent nothing was stored, so nothing is saved now either.
    effects = (Effect.SAVE_SESSION,) if session.consent else ()
    return Transition(replace(session, state=State.STOPPED), ("stop",), effects)
