"""0008 — widen correlated_events.business_impact to TEXT

Schema drift fix: the model declares ``business_impact`` as ``Text`` (long
free-form impact descriptions, e.g. the demo seed's Chinese incident
summaries), but the 0001 baseline created it as ``VARCHAR(20)``. Databases
built through Alembic (CI/E2E/production) therefore raise
StringDataRightTruncationError whenever the correlation engine or seed
writes a real impact description, while create_all-built databases
(dev/tests) silently allow it — which is why this only surfaced in CI.

A full model↔schema audit found this to be the only drift.

Revision ID: 0008_widen_business_impact
Revises: 0007_drop_dead_tables
"""

from alembic import op

# revision identifiers
revision = "0008_widen_business_impact"
down_revision = "0007_drop_dead_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # varchar -> text keeps existing data; no table rewrite needed in PG
    op.execute(
        "ALTER TABLE correlated_events "
        "ALTER COLUMN business_impact TYPE TEXT"
    )


def downgrade() -> None:
    # Narrowing back would fail when rows exceed 20 chars; truncate
    # explicitly so the downgrade remains traversable.
    op.execute(
        "ALTER TABLE correlated_events "
        "ALTER COLUMN business_impact TYPE VARCHAR(20) "
        "USING LEFT(business_impact, 20)"
    )
