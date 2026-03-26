"""Add name and apprise_url columns to notification_configs

Revision ID: 0001
Revises:
Create Date: 2026-03-26

These two columns were added to the NotificationConfig ORM model in the
Apprise alerting feature PR.  SQLAlchemy's create_all() does not ALTER
existing tables, so deployments that had notification_configs created before
this change are missing the columns and raise a ProgrammingError at runtime.

Using ADD COLUMN IF NOT EXISTS makes this migration idempotent – it is safe
to run against both fresh installs (where create_all already created the
columns) and existing deployments (where the columns are absent).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE notification_configs "
        "ADD COLUMN IF NOT EXISTS name VARCHAR(255) NOT NULL DEFAULT 'My Notification'"
    )
    op.execute(
        "ALTER TABLE notification_configs " "ADD COLUMN IF NOT EXISTS apprise_url TEXT"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE notification_configs DROP COLUMN IF EXISTS apprise_url")
    op.execute("ALTER TABLE notification_configs DROP COLUMN IF EXISTS name")
