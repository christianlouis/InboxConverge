"""Add debug_logging column to mail_accounts

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-03

Adds a boolean ``debug_logging`` column to ``mail_accounts``.

When True, the next processing run will record a detailed connection trace
(timings, phase-by-phase events, message UIDs/sizes) and persist it as a
``ProcessingLog`` row with ``level='DEBUG'``.  The column auto-resets to
False after 5 completed runs in a 24-hour window to prevent it being left
on indefinitely.

The column defaults to False so all existing rows are unaffected.
Using IF NOT EXISTS makes the migration idempotent against fresh installs
where create_all() already created the column.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE mail_accounts "
        "ADD COLUMN IF NOT EXISTS debug_logging BOOLEAN NOT NULL DEFAULT FALSE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE mail_accounts DROP COLUMN IF EXISTS debug_logging")
