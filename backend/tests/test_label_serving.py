"""Deterministic nutrition-label serving math (FTY-061).

The label step turns schema-validated per-serving panel facts into canonical
calories/macros with the *same* serving math as FTY-044, extended with two pure
helpers:

- :func:`serving_size_grams` — the label's printed serving size → grams (mass /
  volume only; a count serving size fails closed);
- :func:`per_serving_to_per_100g` — printed per-serving facts → canonical per-100g.

These tests pin the arithmetic so a regression in the deterministic calculators is
caught without any provider or database.
"""

from __future__ import annotations

import pytest

from app.estimator.food_serving import (
    NutritionFacts,
    per_serving_to_per_100g,
    resolve_grams,
    scale_facts,
    serving_size_grams,
)


def test_serving_size_grams_mass_and_volume() -> None:
    assert serving_size_grams(30.0, "g") == 30.0
    assert serving_size_grams(2.0, "oz") == pytest.approx(56.699, abs=1e-3)
    # 1 ml ≈ 1 g (documented v1 density assumption, shared with FTY-044).
    assert serving_size_grams(240.0, "ml") == 240.0


def test_serving_size_grams_rejects_count_and_nonpositive() -> None:
    # A count-only serving size ("1 bar") has no mass/volume, so it cannot be
    # canonicalised to per-100g: fail closed (caller asks rather than guesses).
    assert serving_size_grams(1.0, "bar") is None
    assert serving_size_grams(0.0, "g") is None
    assert serving_size_grams(-5.0, "g") is None


def test_per_serving_to_per_100g_scales_by_serving_size() -> None:
    # 200 kcal / 10 P / 20 C / 8 F per 40 g serving → ×(100/40)=×2.5 per 100 g.
    per_serving = NutritionFacts(calories=200.0, protein_g=10.0, carbs_g=20.0, fat_g=8.0)
    per_100g = per_serving_to_per_100g(per_serving, 40.0)
    assert per_100g.calories == pytest.approx(500.0)
    assert per_100g.protein_g == pytest.approx(25.0)
    assert per_100g.carbs_g == pytest.approx(50.0)
    assert per_100g.fat_g == pytest.approx(20.0)


def test_one_serving_round_trips_to_per_serving_values() -> None:
    # Consuming exactly one serving must reproduce the printed per-serving numbers.
    per_serving = NutritionFacts(calories=150.0, protein_g=5.0, carbs_g=27.0, fat_g=3.0)
    serving_g = serving_size_grams(45.0, "g")
    assert serving_g == 45.0
    per_100g = per_serving_to_per_100g(per_serving, serving_g)
    grams = resolve_grams(unit=None, amount=1.0, quantity_text="", default_serving_g=serving_g)
    assert grams == 45.0
    scaled = scale_facts(per_100g, grams)
    assert scaled.calories == 150.0
    assert scaled.protein_g == 5.0
    assert scaled.carbs_g == 27.0
    assert scaled.fat_g == 3.0


def test_two_servings_doubles_the_panel() -> None:
    per_serving = NutritionFacts(calories=120.0, protein_g=2.0, carbs_g=24.0, fat_g=1.5)
    serving_g = serving_size_grams(30.0, "g")
    assert serving_g is not None
    per_100g = per_serving_to_per_100g(per_serving, serving_g)
    grams = resolve_grams(unit=None, amount=2.0, quantity_text="", default_serving_g=serving_g)
    assert grams == 60.0
    scaled = scale_facts(per_100g, grams)
    assert scaled.calories == 240.0
    assert scaled.carbs_g == 48.0


def test_explicit_mass_quantity_overrides_serving_count() -> None:
    # The user can log a measured mass instead of a serving count; the per-100g
    # facts scale to that mass directly.
    per_serving = NutritionFacts(calories=250.0, protein_g=10.0, carbs_g=30.0, fat_g=9.0)
    serving_g = serving_size_grams(50.0, "g")
    assert serving_g is not None
    per_100g = per_serving_to_per_100g(per_serving, serving_g)  # 500 kcal / 100 g
    grams = resolve_grams(unit="g", amount=25.0, quantity_text="25g", default_serving_g=serving_g)
    assert grams == 25.0
    scaled = scale_facts(per_100g, grams)
    assert scaled.calories == 125.0
