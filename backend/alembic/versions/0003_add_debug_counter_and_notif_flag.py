"""Add debug_logging_run_count and error_notification_sent columns

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-03

Changes:
- debug_logging_run_count (INTEGER, default 0): counts completed/partial_failure
  runs since debug_logging was last enabled.  Auto-disables debug_logging once
  this counter reaches 5.  The counter is reset to 0 whenever debug_logging is
  toggled back on via the API.

- error_notification_sent (BOOLEAN, default FALSE): tracks whether a failure
  notification has already been dispatched for the current consecutive error
  streak.  Prevents notification spam: only the first failure in a streak fires
  a notification.  Cleared (and a recovery notice sent) when a run succeeds.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE mail_accounts "
        "ADD COLUMN IF NOT EXISTS debug_logging_run_count INTEGER NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE mail_accounts "
        "ADD COLUMN IF NOT EXISTS error_notification_sent BOOLEAN NOT NULL DEFAULT FALSE"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE mail_accounts DROP COLUMN IF EXISTS debug_logging_run_count"
    )
    op.execute(
        "ALTER TABLE mail_accounts DROP COLUMN IF EXISTS error_notification_sent"
    )
