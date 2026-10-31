"""K6 scoring and risk level.

This is a fixed, deterministic rule. It must never be delegated to an LLM.
Pure module: no I/O, no network.
"""

from dataclasses import dataclass
from enum import Enum

NUM_QUESTIONS = 6

# CHW reply digit -> K6 points.
# 1 = never, 2 = rarely, 3 = sometimes, 4 = most of the time, 5 = all of the time.
CHOICE_POINTS = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4}

MAX_SCORE = NUM_QUESTIONS * max(CHOICE_POINTS.values())

# PROVISIONAL thresholds, to be validated by the referral nurse.
GREEN_MAX = 7  # score <= 7 -> green (if safety question is negative)
ORANGE_MAX = 12  # 8..12 -> orange; >= 13 -> red


class Level(str, Enum):
    GREEN = "green"
    ORANGE = "orange"
    RED = "red"


@dataclass(frozen=True)
class Result:
    score: int
    level: Level
    safety_flag: bool


def is_valid_choice(choice: object) -> bool:
    """True if `choice` is an accepted reply digit (int 1..5, not a bool)."""
    return type(choice) is int and choice in CHOICE_POINTS


def k6_score(choices: list[int] | tuple[int, ...]) -> int:
    """Sum the K6 points for the 6 raw choices (each 1..5). Returns 0..24."""
    if len(choices) != NUM_QUESTIONS:
        raise ValueError(f"expected {NUM_QUESTIONS} answers, got {len(choices)}")
    for choice in choices:
        if not is_valid_choice(choice):
            raise ValueError(f"invalid answer {choice!r}, expected an int from 1 to 5")
    return sum(CHOICE_POINTS[choice] for choice in choices)


def risk_level(score: int, safety_positive: bool) -> Level:
    """Map a K6 score and the safety answer to a level. A positive safety answer is always red."""
    if type(score) is not int or not 0 <= score <= MAX_SCORE:
        raise ValueError(f"invalid score {score!r}, expected an int from 0 to {MAX_SCORE}")
    if type(safety_positive) is not bool:
        raise ValueError(f"invalid safety answer {safety_positive!r}, expected a bool")
    if safety_positive:
        return Level.RED
    if score <= GREEN_MAX:
        return Level.GREEN
    if score <= ORANGE_MAX:
        return Level.ORANGE
    return Level.RED


def evaluate(choices: list[int] | tuple[int, ...], safety_positive: bool) -> Result:
    score = k6_score(choices)
    return Result(score=score, level=risk_level(score, safety_positive), safety_flag=safety_positive)
