"""0009 — convert root_cause_analyses.human_verified to BOOLEAN

Schema drift missed by the 0008 audit: the model annotates
``human_verified: Mapped[bool]`` but its column type was ``String(10)``,
so the table was created as ``VARCHAR(10) NOT NULL`` without a server
default. The RCA write path passes a Python bool, which asyncpg refuses
to encode as VARCHAR — the LLM analysis succeeds (53s of provider time)
and the INSERT then fails with DataError, surfacing to users as a
misleading "AI service unavailable" message.

Table is empty-or-string-only at this point ('true'/'false' never
written in practice — the column was unwritable), so the cast is safe.

Revision ID: 0009_rca_human_verified_bool
Revises: 0008_widen_business_impact
"""

from alembic import op

# revision identifiers
revision = "0009_rca_human_verified_bool"
down_revision = "0008_widen_business_impact"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE root_cause_analyses "
        "ALTER COLUMN human_verified DROP DEFAULT, "
        "ALTER COLUMN human_verified TYPE BOOLEAN "
        "USING LOWER(human_verified)::boolean, "
        "ALTER COLUMN human_verified SET DEFAULT false"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE root_cause_analyses "
        "ALTER COLUMN human_verified DROP DEFAULT, "
        "ALTER COLUMN human_verified TYPE VARCHAR(10) "
        "USING CASE WHEN human_verified THEN 'true' ELSE 'false' END, "
        "ALTER COLUMN human_verified SET DEFAULT 'false'"
    )
