"""evidence_sources user-text basis + field provenance (FTY-280)

Makes ``evidence_sources`` able to record a **user-stated** nutrition fact honestly
(FTY-279 contract; FTY-280 implementation), without a per-100g lie:

- adds ``basis`` (``per_100g`` default) — what the immutable fact snapshot is
  expressed against, so an ``as_logged`` user-stated total is never silently
  reinterpreted as a per-100g density (``docs/contracts/evidence-retrieval.md``);
- adds ``field_provenance`` (nullable JSON) — the per-field origin map
  (``user_stated`` / ``estimated`` / ``unknown``) when a record's fields have mixed
  origins (user-stated calories + estimated/unknown macros);
- makes the four ``*_per_100g`` fact-snapshot columns **nullable**, so an *unknown*
  macro (FTY-279) is stored ``NULL`` and stays distinct from a real ``0 g`` — never a
  silent zero. ``calories`` is still required for a usable match, but nullability is
  relaxed uniformly so a user-stated calorie-only item can leave its macros unknown.

Additive and backward-compatible: existing USDA/OFF/label/official/reference rows
keep their per-100g snapshot values, get ``basis = 'per_100g'`` via the server
default, and ``field_provenance = NULL``; no backfill is needed and no row is
rewritten in meaning. Never stores raw user text or page content.

Rollback: ``alembic downgrade 0017`` (or ``-1``) drops the two new columns and
restores the snapshot columns to ``NOT NULL``, fully reversing this migration —
verified by an apply/rollback test against a throwaway database (a fresh rollback
has no user-text rows, so re-tightening the snapshot columns is safe).

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SNAPSHOT_COLUMNS = (
    "calories_per_100g",
    "protein_per_100g",
    "carbs_per_100g",
    "fat_per_100g",
)


def upgrade() -> None:
    with op.batch_alter_table("evidence_sources") as batch_op:
        batch_op.add_column(
            sa.Column(
                "basis",
                sa.String(length=16),
                nullable=False,
                server_default="per_100g",
            )
        )
        batch_op.add_column(sa.Column("field_provenance", sa.JSON(), nullable=True))
        for column in _SNAPSHOT_COLUMNS:
            batch_op.alter_column(
                column,
                existing_type=sa.Float(),
                nullable=True,
                existing_nullable=False,
            )


def downgrade() -> None:
    with op.batch_alter_table("evidence_sources") as batch_op:
        for column in _SNAPSHOT_COLUMNS:
            batch_op.alter_column(
                column,
                existing_type=sa.Float(),
                nullable=False,
                existing_nullable=True,
            )
        batch_op.drop_column("field_provenance")
        batch_op.drop_column("basis")
