import pytest

from app.scoring import (
    CHOICE_POINTS,
    MAX_SCORE,
    Level,
    Result,
    evaluate,
    is_valid_choice,
    k6_score,
    risk_level,
)


def choices_for_score(score: int) -> list[int]:
    """Build 6 valid choices whose K6 score equals `score`."""
    points = []
    remaining = score
    for _ in range(6):
        p = min(4, remaining)
        points.append(p)
        remaining -= p
    assert remaining == 0
    return [p + 1 for p in points]


def test_choice_mapping_matches_spec():
    assert CHOICE_POINTS == {1: 0, 2: 1, 3: 2, 4: 3, 5: 4}
    assert MAX_SCORE == 24


@pytest.mark.parametrize("score", range(0, 25))
def test_k6_score_round_trip(score):
    assert k6_score(choices_for_score(score)) == score


def test_k6_score_bounds():
    assert k6_score([1] * 6) == 0
    assert k6_score([5] * 6) == 24
    assert k6_score([1, 2, 3, 4, 5, 1]) == 10


def test_k6_score_accepts_tuple():
    assert k6_score((3,) * 6) == 12


@pytest.mark.parametrize("choices", [[], [1] * 5, [1] * 7])
def test_k6_score_rejects_wrong_length(choices):
    with pytest.raises(ValueError):
        k6_score(choices)


@pytest.mark.parametrize("bad", [0, 6, -1, "3", 3.0, None, True])
def test_k6_score_rejects_invalid_values(bad):
    with pytest.raises(ValueError):
        k6_score([1, 1, 1, 1, 1, bad])


@pytest.mark.parametrize(
    "score, expected",
    [
        (0, Level.GREEN),
        (7, Level.GREEN),
        (8, Level.ORANGE),
        (12, Level.ORANGE),
        (13, Level.RED),
        (24, Level.RED),
    ],
)
def test_risk_level_thresholds(score, expected):
    assert risk_level(score, safety_positive=False) is expected


@pytest.mark.parametrize("score", range(0, 25))
def test_positive_safety_is_always_red(score):
    assert risk_level(score, safety_positive=True) is Level.RED


@pytest.mark.parametrize("bad_score", [-1, 25, 7.5, "7", None])
def test_risk_level_rejects_invalid_score(bad_score):
    with pytest.raises(ValueError):
        risk_level(bad_score, safety_positive=False)


@pytest.mark.parametrize("bad_safety", [None, 0, 1, "no"])
def test_risk_level_rejects_non_bool_safety(bad_safety):
    with pytest.raises(ValueError):
        risk_level(0, safety_positive=bad_safety)


def test_evaluate_green():
    assert evaluate([1] * 6, safety_positive=False) == Result(0, Level.GREEN, False)


def test_evaluate_orange():
    assert evaluate(choices_for_score(10), safety_positive=False) == Result(10, Level.ORANGE, False)


def test_evaluate_red_by_score():
    assert evaluate([5] * 6, safety_positive=False) == Result(24, Level.RED, False)


def test_evaluate_red_by_safety_with_zero_score():
    assert evaluate([1] * 6, safety_positive=True) == Result(0, Level.RED, True)


def test_is_valid_choice():
    assert all(is_valid_choice(c) for c in range(1, 6))
    assert not any(is_valid_choice(c) for c in (0, 6, "1", True, 1.0, None))
