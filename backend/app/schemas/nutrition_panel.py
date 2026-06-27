"""LLM structured-output schema for nutrition-label extraction (FTY-061).

This is the *untrusted-analyst* contract for reading a user-provided nutrition
**label image**: the strict schema the label-resolution step asks the v2 vision
provider (FTY-076) to enforce, and the validator every model reply must pass
before any of it is trusted. The model is told to transcribe the printed
nutrition panel into structured per-serving facts; its reply is trusted only
insofar as it validates against these models, and the backend — never the model —
turns those facts into stored calories/macros (see
:mod:`app.estimator.food_serving`).

Defence in depth against prompt injection embedded in the label image lives in
the schema shape itself, mirroring :mod:`app.schemas.parse`:

- ``extra="forbid"`` on every model rejects smuggled keys, so a reply cannot
  carry fields the step never asked for.
- Every numeric field is bounded (``ge`` / ``le`` / ``gt``), so an adversarial
  reply cannot persist absurd or unbounded values, and string fields are
  length-bounded.
- The disposition vocabulary is closed (:class:`PanelDisposition`), so how the
  label was read is a value the step routes on, never a free-form instruction.

Text printed on the label (including any "ignore your instructions …" injection)
is **data to transcribe**, never instructions: the step never executes it, the
schema bounds it, and the deterministic calculators — not the model — produce the
stored numbers.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

#: Schema version recorded on the estimation run for reproducibility. Bump when
#: the panel shape changes so old runs remain interpretable.
NUTRITION_PANEL_SCHEMA_VERSION = "nutrition_panel/v1"

#: Upper bounds that cap an adversarial or runaway model reply. Generous enough
#: for any real packaged-food label yet small enough that a malicious reply
#: cannot persist nonsense values.
MAX_PRODUCT_NAME_LEN = 200
MAX_UNIT_LEN = 32
MAX_REASON_LEN = 120
#: A single serving never realistically exceeds these; they are a fail-closed
#: ceiling on the transcribed numbers, not a nutrition judgement.
MAX_ENERGY_KCAL = 10_000.0
MAX_MACRO_G = 1_000.0
MAX_SERVING_AMOUNT = 100_000.0
MAX_SERVINGS_PER_CONTAINER = 10_000.0


class PanelDisposition(StrEnum):
    """How the model read the supplied image as a whole.

    - :attr:`EXTRACTED` — a nutrition panel was read legibly; ``facts`` is present.
    - :attr:`UNREADABLE` — the image is recognisably a nutrition label but its
      numbers cannot be transcribed confidently (blur, glare, crop); the step
      routes to ``needs_clarification`` rather than guess.
    - :attr:`NOT_A_LABEL` — the image is not a nutrition label at all (or is
      unusable input); the step fails closed, never inventing an estimate.
    """

    EXTRACTED = "extracted"
    UNREADABLE = "unreadable"
    NOT_A_LABEL = "not_a_label"


class PanelFacts(BaseModel):
    """The transcribed **per-serving** facts from one nutrition panel.

    All energy/macro values are **per single serving** as printed on the label —
    the backend converts them to canonical per-100g facts and scales them to the
    consumed quantity deterministically (:mod:`app.estimator.food_serving`); the
    model never supplies the final calories/macros. ``serving_size_amount`` /
    ``serving_size_unit`` are the printed serving size (e.g. ``30`` / ``g``);
    a confident resolution requires a serving size that resolves to grams.
    """

    model_config = ConfigDict(extra="forbid")

    #: Optional product name printed near the panel; used only as the derived
    #: item's display name, stored as data, never interpreted.
    product_name: str | None = Field(default=None, max_length=MAX_PRODUCT_NAME_LEN)
    serving_size_amount: float = Field(gt=0.0, le=MAX_SERVING_AMOUNT)
    serving_size_unit: str = Field(min_length=1, max_length=MAX_UNIT_LEN)
    servings_per_container: float | None = Field(
        default=None, gt=0.0, le=MAX_SERVINGS_PER_CONTAINER
    )
    energy_kcal_per_serving: float = Field(ge=0.0, le=MAX_ENERGY_KCAL)
    protein_g_per_serving: float = Field(ge=0.0, le=MAX_MACRO_G)
    carbs_g_per_serving: float = Field(ge=0.0, le=MAX_MACRO_G)
    fat_g_per_serving: float = Field(ge=0.0, le=MAX_MACRO_G)


class NutritionPanel(BaseModel):
    """The strict structured reply the label step validates before trusting it.

    Treated as untrusted until it validates: a schema-invalid reply is rejected
    and never persisted (fail closed). ``facts`` is required when ``disposition``
    is ``extracted`` and ignored otherwise — the step enforces that pairing when
    it routes.
    """

    model_config = ConfigDict(extra="forbid")

    disposition: PanelDisposition
    confidence: float = Field(ge=0.0, le=1.0)
    facts: PanelFacts | None = None
    #: Short, sanitized label set when ``disposition`` is ``not_a_label`` — never
    #: echoed raw image text; used only for the run's failure reason.
    reason: str | None = Field(default=None, max_length=MAX_REASON_LEN)
