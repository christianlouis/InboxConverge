# ADR 005: Celery Task Retry Strategy

**Status:** Accepted  
**Date:** 2026-02-01  
**Deciders:** Development Team

## Context

Email processing tasks can fail for many transient reasons:

1. Mail server temporarily unavailable or overloaded
2. Network timeouts during POP3/IMAP connections
3. SMTP delivery failures (temporary, e.g. greylisting)
4. Gmail API rate limits or transient 5xx errors
5. Database connection errors

Without a retry strategy, transient failures result in permanently missed emails. However, aggressive retries can overload external services or cause duplicate deliveries.

## Decision

We will use **Celery's built-in autoretry mechanism** with **exponential backoff**, capped at **3 retries** per task invocation. Failed tasks after exhausting retries are recorded in the processing log and flagged on the mail account for user visibility.

## Alternatives Considered

### 1. No Retries (fail-fast)
- **Pros**: Simple, predictable
- **Cons**: Transient failures cause permanent data loss, poor user experience

### 2. Infinite Retries
- **Pros**: Guarantees eventual processing
- **Cons**: Fills task queue, may mask persistent failures, delays detection of real errors

### 3. Fixed-Interval Retries
- **Pros**: Simple to reason about
- **Cons**: Hammers failing services, does not give them time to recover

### 4. External Retry Orchestrator (e.g., Temporal, AWS Step Functions)
- **Pros**: Advanced workflow management, visual debugging
- **Cons**: Significant infrastructure overhead, unnecessary complexity at current scale

### 5. Manual Retry Queue
- **Pros**: Full control
- **Cons**: Re-implements what Celery already provides

## Rationale

Celery's `autoretry_for` with `retry_backoff=True` was chosen because:

1. **Native Integration**: No additional libraries required, built into Celery
2. **Exponential Backoff**: Gives external services time to recover between retries
3. **Jitter**: Prevents thundering herd when many accounts fail simultaneously
4. **Bounded Retries**: `max_retries=3` ensures tasks eventually fail rather than running forever
5. **Configurable**: Per-task retry configuration allows tuning per failure type
6. **Visibility**: Failed tasks appear in Flower dashboard and processing logs

## Implementation

```python
from celery import Task
from app.core.celery_app import celery_app

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,          # Exponential: 60s, 120s, 240s
    retry_backoff_max=600,       # Cap at 10 minutes
    retry_jitter=True,           # Add randomness to spread load
)
def process_mail_account(self: Task, account_id: int) -> dict:
    """Fetch and forward emails for a single mail account."""
    try:
        # ... email processing logic ...
        pass
    except Exception as exc:
        # Log failure to processing_logs table before re-raising
        _record_failure(account_id, str(exc))
        raise
```

### Retry Schedule (default config)

| Attempt | Delay (approx.) | Total elapsed |
|---------|-----------------|---------------|
| 1st     | immediate       | 0s            |
| 2nd     | ~60s            | 60s           |
| 3rd     | ~120s           | 3m            |
| 4th     | ~240s           | 7m            |
| Final failure | — recorded to DB | ~7m     |

### Failure Handling After All Retries

When all retries are exhausted, the task:
1. Marks the `ProcessingRun` as `failed` in the database
2. Increments the `consecutive_failures` counter on the `MailAccount`
3. If `consecutive_failures` exceeds threshold: marks account as `error` state
4. Triggers a user notification via Apprise (if configured)

## Consequences

### Positive
- Transient failures (network blips, greylisting) recover automatically
- Exponential backoff respects external service rate limits
- Bounded retry count prevents runaway task accumulation
- Failure visibility in Flower and processing logs

### Negative
- Up to ~7 minutes of additional delay for permanently failing accounts
- Retry state stored in Redis; Redis failure loses retry context
- Duplicate delivery possible if task succeeds after partial completion (must ensure idempotency)

### Idempotency Requirement

Tasks **must be idempotent**: re-running a task for the same mail account must not deliver duplicate emails. Implementations must:
- Track message UIDs already processed in `processing_logs`
- Use POP3 `UIDL` or IMAP `UID` to identify messages
- Check for existing `ProcessingLog` entries before delivery

## Related Decisions

- See ADR-001 for Celery architecture overview
- See ADR-009 for Gmail API delivery (idempotency considerations)

## References

- [Celery Retrying Tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying)
- [Celery autoretry_for](https://docs.celeryq.dev/en/stable/userguide/tasks.html#automatic-retry-for-known-exceptions)
- [Exponential Backoff and Jitter (AWS blog)](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
