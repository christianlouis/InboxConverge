"""
Prometheus metrics definitions for InboxRescue.

All application metrics are defined here as module-level singletons so that
every subsystem (HTTP layer, Celery workers, Gmail service, auth) imports
the same registry objects.
"""

from prometheus_client import Counter, Histogram, Gauge

# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ---------------------------------------------------------------------------
# Mail processing
# ---------------------------------------------------------------------------

MAIL_PROCESSING_RUNS_TOTAL = Counter(
    "mail_processing_runs_total",
    "Total mail-account processing runs by final status",
    ["status"],  # completed | partial_failure | failed
)

MAIL_PROCESSING_EMAILS_TOTAL = Counter(
    "mail_processing_emails_total",
    "Total emails encountered during processing runs",
    ["operation"],  # fetched | forwarded | failed
)

MAIL_PROCESSING_DURATION_SECONDS = Histogram(
    "mail_processing_duration_seconds",
    "Duration of a single mail-account processing run in seconds",
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)

ACTIVE_MAIL_ACCOUNTS = Gauge(
    "active_mail_accounts_total",
    "Number of enabled mail accounts queued for this scheduler cycle",
)

# ---------------------------------------------------------------------------
# Gmail API
# ---------------------------------------------------------------------------

GMAIL_API_REQUESTS_TOTAL = Counter(
    "gmail_api_requests_total",
    "Total Gmail API requests by operation and outcome",
    [
        "operation",
        "status",
    ],  # operation: inject|verify|get_label|get_profile  status: success|error
)

GMAIL_API_DURATION_SECONDS = Histogram(
    "gmail_api_duration_seconds",
    "Gmail API call duration in seconds",
    ["operation"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

GMAIL_TOKEN_REFRESHES_TOTAL = Counter(
    "gmail_token_refreshes_total",
    "Total number of OAuth access-token refreshes performed by GmailService",
)

GMAIL_CREDENTIALS_INVALIDATED_TOTAL = Counter(
    "gmail_credentials_invalidated_total",
    "Total times a user's Gmail credentials were marked invalid (revoked token)",
)

# ---------------------------------------------------------------------------
# Authentication / OAuth
# ---------------------------------------------------------------------------

AUTH_LOGINS_TOTAL = Counter(
    "auth_logins_total",
    "Total login attempts by method and outcome",
    ["method", "status"],  # method: password|google  status: success|failure
)

AUTH_REGISTRATIONS_TOTAL = Counter(
    "auth_registrations_total",
    "Total registration attempts by method and outcome",
    ["method", "status"],  # method: password|google  status: success|failure
)

OAUTH_CALLBACKS_TOTAL = Counter(
    "oauth_callbacks_total",
    "Total OAuth2 callback events by provider and outcome",
    ["provider", "status"],  # provider: google  status: success|error
)

# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------

CELERY_TASKS_TOTAL = Counter(
    "celery_tasks_total",
    "Total Celery task executions by task name and status",
    ["task_name", "status"],  # status: success|failure
)

CELERY_TASK_DURATION_SECONDS = Histogram(
    "celery_task_duration_seconds",
    "Celery task execution duration in seconds",
    ["task_name"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800),
)
