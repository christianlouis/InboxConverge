"""Add sender_email column to user_smtp_configs

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-03

Adds a ``sender_email`` column to ``user_smtp_configs``.

SMTP providers such as Postmark use an API token (UUID) as the SMTP username
for authentication, but require a real email address as the ``From:`` header.
This column stores the address that should appear as the sender; when blank,
the existing ``username`` value is used as a fallback so existing rows remain
fully functional.

Using IF NOT EXISTS makes the migration idempotent against fresh installs
where create_all() already created the column.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE user_smtp_configs "
        "ADD COLUMN IF NOT EXISTS sender_email VARCHAR(255) NOT NULL DEFAULT ''"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE user_smtp_configs DROP COLUMN IF EXISTS sender_email")
