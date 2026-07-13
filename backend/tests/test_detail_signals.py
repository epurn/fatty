"""Unit tests for the deterministic detail-signal parsers (FTY-167).

Pin the pure parsers that decide whether a casual-but-detailed log carries enough
structure — a count, a range, a distance, steps, or a game count — to be estimated
rather than clarified. No LLM, no database: exact assertions on pure functions.
"""

from __future__ import annotations

import pytest

from app.estimator.detail_signals import (
    distance_km,
    game_count,
    has_food_detail,
    parse_leading_count,
    parse_range_midpoint,
    step_count,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("i had 4", 4.0),  # stranded parenthetical-style count (FTY-362)
        ("(i had 4)", 4.0),
        ("4", 4.0),
        ("2 large", 2.0),  # count with a trailing size adjective
        ("4 toppables brand crackers", 4.0),  # count with stranded product tokens
    ],
)
def test_parse_leading_count_hits(text: str, expected: float) -> None:
    assert parse_leading_count(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "some crackers",  # no number
        "milk",
        "a slice",  # worded portion, not a bare count
        "100 grams",  # a measured mass is owned by the serving math, not a count
        "100g",
        "150 g",
        "1 tbsp",  # a measured household volume, not a count
        "about 1 tbsp",
        "1tbsp",
        "5-10",  # a range resolves through parse_range_midpoint, not here
        "1.5",  # a decimal is not a whole count
        "0",  # non-positive
        "60",  # beyond a casual count (MAX_BARE_COUNT)
    ],
)
def test_parse_leading_count_misses(text: str) -> None:
    assert parse_leading_count(text) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a handful (5-10) of onion rings", (5.0, 10.0, 7.5)),
        ("5 - 10", (5.0, 10.0, 7.5)),
        ("5 to 10", (5.0, 10.0, 7.5)),
        ("5–10", (5.0, 10.0, 7.5)),  # en dash
        ("10-5", (5.0, 10.0, 7.5)),  # reversed is normalised
        ("2.5-3.5", (2.5, 3.5, 3.0)),
    ],
)
def test_parse_range_midpoint_hits(text: str, expected: tuple[float, float, float]) -> None:
    assert parse_range_midpoint(text) == expected


@pytest.mark.parametrize("text", ["", "a handful", "150g", "three", "0-0"])
def test_parse_range_midpoint_misses(text: str) -> None:
    assert parse_range_midpoint(text) is None


@pytest.mark.parametrize(
    ("unit", "amount", "text", "expected"),
    [
        ("km", 5.0, "5 km", 5.0),
        ("mi", 1.0, "1 mi", 1.6093),  # rounded to 4 dp
        (None, None, "ran 5 km", 5.0),
        (None, None, "swam a mile", 1.6093),
        (None, None, "13.1 miles", pytest.approx(21.082, abs=0.01)),
        ("mile", None, "a mile", 1.6093),  # distance unit, no amount → one unit
        ("meters", 400.0, "400 meters", 0.4),
    ],
)
def test_distance_km_hits(
    unit: str | None, amount: float | None, text: str, expected: object
) -> None:
    assert distance_km(unit, amount, text) == expected


@pytest.mark.parametrize(
    ("unit", "amount", "text"),
    [
        (None, None, "30 min"),  # a time, not a distance
        ("min", 30.0, "30 min"),  # bare "m"-style time is not metres
        (None, None, "played 3 games"),
        (None, None, ""),
    ],
)
def test_distance_km_misses(unit: str | None, amount: float | None, text: str) -> None:
    assert distance_km(unit, amount, text) is None


@pytest.mark.parametrize(
    ("unit", "amount", "text", "expected"),
    [
        ("steps", 13000.0, "13000 steps", 13000.0),
        (None, None, "13000 steps", 13000.0),
        (None, None, "walked 13,000 steps", 13000.0),
        (None, None, "10000 step", 10000.0),
    ],
)
def test_step_count_hits(
    unit: str | None, amount: float | None, text: str, expected: float
) -> None:
    assert step_count(unit, amount, text) == expected


@pytest.mark.parametrize("text", ["", "5 km", "a walk"])
def test_step_count_misses(text: str) -> None:
    assert step_count(None, None, text) is None


@pytest.mark.parametrize(
    ("unit", "amount", "text", "expected"),
    [
        ("games", 3.0, "3 games", 3.0),
        (None, None, "played 3 games of badminton", 3.0),
        (None, None, "2 matches", 2.0),
        (None, None, "1 set", 1.0),
    ],
)
def test_game_count_hits(
    unit: str | None, amount: float | None, text: str, expected: float
) -> None:
    assert game_count(unit, amount, text) == expected


@pytest.mark.parametrize("text", ["", "played badminton", "5 km"])
def test_game_count_misses(text: str) -> None:
    assert game_count(None, None, text) is None


@pytest.mark.parametrize(
    ("amount", "text", "expected"),
    [
        (3.0, "3 sandwiches", True),  # explicit count
        (None, "a handful (5-10)", True),  # range
        (1.0, "a slice", True),
        # A bare count the model stranded in the phrase is detail (FTY-362), so a
        # counted item is not re-asked for an amount it already stated.
        (None, "i had 4", True),
        (None, "(i had 4)", True),
        (None, "2 large", True),
        (None, "some crackers", False),  # no amount signal
        (None, "", False),
        (0.0, "", False),  # non-positive amount is not detail
        # Stated worded/household/indefinite portions count as detail (FTY-275),
        # even when the structured amount is empty.
        (None, "1/3 cup", True),  # household measure
        (None, "a tsp of maple syrup", True),  # household + indefinite article
        (None, "2 tbsp", True),
        (None, "1 fl oz", True),  # "fl oz" tokenises to "fl"/"oz"; "fl" flags it
        (None, "a splash of milk", True),  # colloquial measure
        (None, "a drizzle of oil", True),
        (None, "a handful of nuts", True),
        (None, "an apple", True),  # indefinite article standing for one
        # Boundary preserved: a genuinely amountless component still clarifies.
        (None, "some milk", False),
        (None, "milk", False),
        (None, "a", False),  # bare article with no following portion word
    ],
)
def test_has_food_detail(amount: float | None, text: str, expected: bool) -> None:
    assert has_food_detail(amount, text) is expected
