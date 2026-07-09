"""Typed parse-policy settings consumed by the estimator (FTY-300).

The application-level :mod:`app.settings` module owns environment loading and
validation. The parse step receives this small immutable value object so estimator
modules route on typed policy settings rather than reading raw environment
variables.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.estimator.clarify_policy import NL_PARSE_CLARIFY_POLICY
from app.settings import (
    DEFAULT_ESTIMATOR_MAX_PARSE_REPAIR_ATTEMPTS,
    EstimatorClarifyMode,
    Settings,
)


@dataclass(frozen=True)
class ParsePolicySettings:
    """Operator-selected parse clarification posture and bounded recovery caps."""

    mode: EstimatorClarifyMode = "estimate_first"
    clarify_threshold: float = NL_PARSE_CLARIFY_POLICY.threshold
    max_repair_attempts: int = DEFAULT_ESTIMATOR_MAX_PARSE_REPAIR_ATTEMPTS

    @classmethod
    def from_app_settings(cls, settings: Settings) -> ParsePolicySettings:
        """Build parse-policy settings from validated application settings."""

        return cls(
            mode=settings.estimator_clarify_mode,
            clarify_threshold=(
                settings.estimator_parse_clarify_threshold
                if settings.estimator_parse_clarify_threshold is not None
                else NL_PARSE_CLARIFY_POLICY.threshold
            ),
            max_repair_attempts=settings.estimator_max_parse_repair_attempts,
        )

    def should_clarify(self, score: float) -> bool:
        """Whether ``score`` falls below the active mode's parse threshold."""

        return score < self.clarify_threshold
