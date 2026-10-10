# Gmail failure alerts

Gmail authorization failures detected during delivery or scheduled token refresh
invalidate the saved credential before sending notifications. A failed message
and the unattempted remainder of its batch stay available for a later run.

User error channels and administrator error channels are notified independently.
Each audience is considered notified only after at least one of its enabled
channels accepts the alert. An exception, zero enabled channels, or a failed
delivery leaves that audience pending. The scheduled Gmail refresh task retries
pending alerts even when there are no new messages and no valid tokens to refresh.
The existing schedule runs at minute 0 and minute 45 of every hour; pending alerts
therefore have a retry interval of 15 or 45 minutes while Beat and workers run.

Successful alerts are suppressed until Gmail is reconnected. A row lock prevents
concurrent alert attempts for the same credential; the helper checks that the
credential is still invalid before sending. Delivery is at least once: a process
failure after a provider accepts a notification but before its database commit
can still cause a duplicate.

Quota limits, temporary Google errors, and retryable token refresh errors do not
invalidate credentials or ask users to reconnect. Ordinary delivery failures use
the existing account error notification route. Their suppression flag is only
saved after a successful notification and is cleared after a fully successful
processing run.

## Enable and verify delivery

1. Configure an enabled user error channel in notification settings and an
   enabled administrator error channel in the admin notification settings.
   Enable error notifications on both. Use an administrator destination that
   does not depend on the Gmail connection being monitored.
2. Use the existing channel test controls and confirm receipt at the destination.
   An application success response means the provider accepted the request;
   verify the actual notification as well.
3. In a test environment, use a dedicated test Google account to exercise revoked
   authorization. Confirm one user alert and one admin alert. Verify the credential
   is invalid and undelivered message UIDs have not been marked as forwarded.
4. Temporarily make one test notification channel fail. Confirm that route remains
   pending, restore it, then run `refresh_gmail_tokens` and verify that only the
   pending audience receives another alert. Reconnect the test Gmail account and
   confirm both notification flags reset.

Do not revoke production Gmail access just to test an alert. Do not paste Apprise
URLs, OAuth tokens, mailbox contents, or secret values into logs or bug reports.

## Rollout and monitoring

Apply Alembic migration `0005` before starting the updated backend, worker, and
Beat processes. It adds two non-null boolean flags with a false default and is
compatible with older application code. An application rollback can leave these
additive columns in place.

After rollout, verify worker and Beat activity, recent processing runs, Gmail
credential status, and enabled alert channel counts. A responding web page or
`/health` endpoint alone does not prove that mail processing or alert delivery
works.

These alerts depend on the database, Celery, and the notification provider. They
do not replace external monitoring for a stopped worker, stopped scheduler, or
database outage. The sample Prometheus configuration scrapes only the backend;
worker-process counters are not automatically shared with that process. Do not
treat backend Gmail counters as proof that worker failures are being monitored.

## Regression checks

With isolated test settings configured, run from `backend/`:

```sh
pytest tests/unit/test_tasks.py tests/unit/test_gmail_service.py \
  tests/unit/test_notification_service.py tests/unit/test_alembic_migrations.py
```
