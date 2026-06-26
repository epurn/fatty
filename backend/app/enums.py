"""Shared domain enums for the identity/profile contract.

These string enums are the canonical vocabulary for the profile contract and are
reused by both the ORM models (column validation) and the Pydantic boundary DTOs
so the persisted values and the API surface cannot drift apart.
"""

from __future__ import annotations

from enum import StrEnum


class MetabolicFormula(StrEnum):
    """Resting-metabolic-rate formula preference (FTY-022).

    Mifflin-St Jeor is the v1 RMR equation (see the system overview). The
    equation differs only by a sex-dependent additive constant (``+5`` vs
    ``-161`` kcal/day), so the product models that choice here as a *metabolic
    formula preference* rather than storing biological sex as a separate field —
    the profile keeps the minimum body data the math needs and nothing more.

    The two members are the only valid inputs to the target calculator; each maps
    to one Mifflin-St Jeor constant (see :mod:`app.estimator.calculator`). FTY-021
    profile capture must offer exactly these values.
    """

    MIFFLIN_ST_JEOR_MALE = "mifflin_st_jeor_male"
    MIFFLIN_ST_JEOR_FEMALE = "mifflin_st_jeor_female"


class GoalDirection(StrEnum):
    """Direction of a weight goal, derived from start vs. target weight (FTY-022)."""

    LOSS = "loss"
    GAIN = "gain"
    MAINTAIN = "maintain"


class UnitsPreference(StrEnum):
    """Display-unit preference. Storage is always canonical (kg, m)."""

    METRIC = "metric"
    IMPERIAL = "imperial"


#: Authentication provider for an :class:`~app.models.identity.AuthIdentity`.
#: Only the local email+password path exists in v1; hosted providers (e.g. Sign
#: in with Apple) are deferred to a later story but modelled as separate
#: identities against the same user.
class AuthProvider(StrEnum):
    """Authentication provider backing an auth identity."""

    LOCAL = "local"
