# ADR 003: Use FastAPI as Web Framework

**Status:** Accepted  
**Date:** 2026-01-25  
**Deciders:** Development Team

## Context

The multi-tenant SaaS backend requires a Python web framework that can handle:

1. High-concurrency API requests (multiple users, simultaneous email polls)
2. Asynchronous database and network I/O without blocking
3. Automatic input validation and serialization
4. Built-in interactive API documentation
5. Easy integration with the async ecosystem (asyncpg, aiosmtplib, aioimaplib)

## Decision

We will use **FastAPI** as the primary web framework for the backend API.

## Alternatives Considered

### 1. Django REST Framework (DRF)
- **Pros**: Mature ecosystem, batteries-included ORM, admin panel, well-known
- **Cons**: Synchronous-first, heavier footprint, complex async support, more boilerplate

### 2. Flask
- **Pros**: Lightweight, flexible, large community
- **Cons**: No native async support, requires extensions for validation, no auto-docs, more manual wiring

### 3. Starlette (bare)
- **Pros**: Minimal, pure async, very fast
- **Cons**: No built-in validation, no auto-documentation, requires writing more boilerplate

### 4. Tornado
- **Pros**: Battle-tested async framework, good WebSocket support
- **Cons**: Older API design, less active development, no modern type annotation support

## Rationale

FastAPI was chosen because:

1. **Native Async Support**: First-class `async`/`await` support matches our async database (asyncpg) and mail protocol (aiosmtplib, aioimaplib) libraries
2. **Automatic Validation**: Pydantic models provide request/response validation with no extra code
3. **Auto-generated Docs**: OpenAPI spec and Swagger UI at `/api/docs` out of the box
4. **Type Safety**: Python type annotations drive both validation and editor tooling
5. **Performance**: Comparable to Node.js and Go for async I/O workloads (Starlette/uvicorn underneath)
6. **Dependency Injection**: Built-in `Depends()` system for auth, database sessions, and config
7. **Modern Python**: Designed for Python 3.8+ with full typing support

## Implementation Notes

```python
# Application factory pattern with lifespan context manager
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables, seed defaults
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: cleanup

app = FastAPI(
    title="POP3 Forwarder API",
    lifespan=lifespan,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
)
```

```python
# Versioned API routing
from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(mail_accounts.router, prefix="/mail-accounts", tags=["mail-accounts"])
```

## Consequences

### Positive
- Clean, self-documenting API with zero extra work
- Async I/O throughout eliminates thread-pool bottlenecks
- Pydantic validation catches bad input before it reaches business logic
- Dependency injection decouples auth, DB, and config from route handlers
- Fast iteration: type errors and validation errors caught at startup

### Negative
- Smaller ecosystem than Django (fewer ready-made plugins)
- Pydantic v2 migration required breaking changes from v1
- Lifespan/startup patterns require careful structuring to avoid import cycles

### Neutral
- Uvicorn required as ASGI server for production
- Gunicorn can be used to manage multiple uvicorn workers

## Related Decisions

- See ADR-004 for database choice (asyncpg/SQLAlchemy async)
- See ADR-007 for JWT authentication via `Depends()`

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Starlette Documentation](https://www.starlette.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [TechEmpower Framework Benchmarks](https://www.techempower.com/benchmarks/)
