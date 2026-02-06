# ADR 001: Use Celery for Background Task Processing

**Status:** Accepted  
**Date:** 2026-01-15  
**Deciders:** Development Team

## Context

The multi-tenant SaaS version of the POP3 forwarder needs to process emails for multiple users on different schedules. We need a reliable way to:

1. Schedule periodic email checks per mail account
2. Process emails asynchronously without blocking API requests
3. Handle failures and retries gracefully
4. Scale horizontally as user base grows

## Decision

We will use **Celery** with **Redis** as the message broker for background task processing.

## Alternatives Considered

### 1. APScheduler
- **Pros**: Simpler, lightweight, no separate broker needed
- **Cons**: Doesn't scale horizontally, limited monitoring, no distributed task queue

### 2. RQ (Redis Queue)
- **Pros**: Simple Redis-based queue, Pythonic API
- **Cons**: Less mature than Celery, fewer features (no complex routing, less monitoring)

### 3. AWS SQS + Lambda
- **Pros**: Fully managed, auto-scaling
- **Cons**: Cloud vendor lock-in, more expensive, requires AWS infrastructure

### 4. Custom Threading
- **Pros**: No external dependencies
- **Cons**: Complex to implement correctly, hard to scale, no retry logic

## Rationale

Celery was chosen because:

1. **Proven at Scale**: Used by companies like Instagram, Reddit, well-tested
2. **Rich Feature Set**: Built-in retries, rate limiting, task routing, monitoring
3. **Horizontal Scaling**: Add more workers to handle more load
4. **Monitoring**: Flower provides real-time monitoring dashboard
5. **Community**: Large community, extensive documentation
6. **Redis Integration**: Redis already used for caching, can serve dual purpose

## Consequences

### Positive
- Background tasks can scale independently from API
- Automatic retry with exponential backoff
- Task prioritization and routing possible
- Flower provides monitoring and management UI
- Can easily add more task types in future

### Negative
- Additional infrastructure component (Celery workers)
- More complex deployment (workers, beat scheduler)
- Redis becomes critical dependency
- Learning curve for team unfamiliar with Celery

### Neutral
- Need to monitor Redis memory usage
- Task serialization must be considered (use JSON, not pickle)
- Task idempotency should be ensured

## Implementation Notes

```python
# Task definition pattern
@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True
)
def process_mail_account(self: Task, account_id: int) -> dict:
    # Implementation
    pass
```

## Monitoring

- Use Flower for web-based monitoring: `celery -A app.core.celery_app flower`
- Track metrics: task success/failure rate, execution time, queue length
- Set up alerts for: worker unavailability, high failure rate, queue backlog

## Related Decisions

- See ADR-002 for Redis choice
- See ADR-005 for task retry strategy

## References

- [Celery Documentation](https://docs.celeryq.dev/)
- [Flower Monitoring](https://flower.readthedocs.io/)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html#best-practices)
