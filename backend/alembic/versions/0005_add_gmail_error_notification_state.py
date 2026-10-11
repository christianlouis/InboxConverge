"""Track delivery of Gmail invalid-credential alerts."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE gmail_credentials "
        "ADD COLUMN IF NOT EXISTS gmail_user_error_notification_sent "
        "BOOLEAN NOT NULL DEFAULT FALSE"
    )
    op.execute(
        "ALTER TABLE gmail_credentials "
        "ADD COLUMN IF NOT EXISTS gmail_admin_error_notification_sent "
        "BOOLEAN NOT NULL DEFAULT FALSE"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE gmail_credentials "
        "DROP COLUMN IF EXISTS gmail_user_error_notification_sent"
    )
    op.execute(
        "ALTER TABLE gmail_credentials DROP COLUMN IF EXISTS gmail_admin_error_notification_sent"
    )
