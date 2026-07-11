"""Exact-evidence proposal read projection (FTY-307).

The read-model half of the ``Make it exact`` foundation: :func:`serialize_proposal`
turns a server-held :class:`~app.estimator.exact_evidence.ExactEvidenceProposal` plus
its opaque reference into the :class:`~app.schemas.exact_evidence.ExactEvidenceProposalDTO`
a propose route (barcode FTY-308, label FTY-309) returns. It costs the preview at the
item's **current amount** using the same serving math apply uses
(:func:`~app.estimator.exact_evidence.cost_grams`), so the preview's
``can_cost_current_amount`` flag and apply's costability decision are one code path
and cannot disagree; when the current amount cannot be costed the preview carries the
proposal's source facts on its own basis instead of invented totals.

The preview's ``source`` descriptor is derived through the shared
:func:`~app.services.item_read_model.source_descriptor`, so a fallback proposal
previews its honest low-trust source label — never an exact one — matching what the
applied item will read.
"""

from __future__ import annotations

from app.estimator.exact_evidence import ExactEvidenceProposal, cost_grams
from app.estimator.food_serving import scale_facts
from app.models.derived import DerivedFoodItem
from app.schemas.exact_evidence import (
    ExactEvidenceProposalDTO,
    ExactEvidenceProposalPreviewDTO,
)
from app.services.item_read_model import source_descriptor


def serialize_proposal(
    item: DerivedFoodItem,
    proposal: ExactEvidenceProposal,
    proposal_ref: str,
    *,
    failure_reason: str | None = None,
) -> ExactEvidenceProposalDTO:
    """Project a server-held proposal + its reference into the read DTO.

    Costs the preview at ``item``'s current amount: when costable, the nutrition
    fields are the item's would-be totals; otherwise they are the proposal's per-100g
    source facts (``can_cost_current_amount = False``), so the client asks for an
    amount rather than being shown an invented portion. ``failure_reason`` is the
    closed, content-free label a ``fallback`` proposal carries (``None`` for
    ``exact``).
    """

    facts = proposal.facts
    grams = cost_grams(item, proposal, item.amount)
    can_cost = grams is not None

    descriptor = source_descriptor(proposal.source_type, proposal.source_ref, proposal.assumptions)
    # A propose route only builds a proposal for an in-hierarchy source, so the
    # descriptor is always present; guard defensively rather than raise on a read.
    if descriptor is None:
        preview = None
    elif grams is not None:
        scaled = scale_facts(facts.as_nutrition_facts(), grams)
        preview = ExactEvidenceProposalPreviewDTO(
            source=descriptor,
            basis=facts.basis,
            calories=scaled.calories,
            protein_g=scaled.protein_g,
            carbs_g=scaled.carbs_g,
            fat_g=scaled.fat_g,
            amount=item.amount,
            serving_label=facts.serving_label,
        )
    else:
        preview = ExactEvidenceProposalPreviewDTO(
            source=descriptor,
            basis=facts.basis,
            calories=facts.calories,
            protein_g=facts.protein_g,
            carbs_g=facts.carbs_g,
            fat_g=facts.fat_g,
            amount=item.amount,
            serving_label=facts.serving_label,
        )

    return ExactEvidenceProposalDTO(
        proposal_ref=proposal_ref,
        kind=proposal.kind,
        quality=proposal.quality,
        failure_reason=failure_reason,
        preview=preview,
        can_cost_current_amount=can_cost,
    )
