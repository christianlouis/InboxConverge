# ADR 004: Use PostgreSQL as Primary Database

**Status:** Accepted  
**Date:** 2026-01-28  
**Deciders:** Development Team

## Context

The application requires a relational database to store:

1. User accounts and subscription data
2. Mail account configurations (servers, protocols, check intervals)
3. Processing run history and per-email logs
4. Notification configurations
5. Subscription plans and audit logs
6. Database-backed application settings (`app_settings` key-value store)

Requirements:
- ACID transactions for financial/subscription data
- Foreign key constraints for referential integrity
- JSON support for flexible metadata storage
- Async driver support for FastAPI integration
- Horizontal read-scaling capability

## Decision

We will use **PostgreSQL 15+** as the primary relational database, accessed via **SQLAlchemy 2.x** with the **asyncpg** driver.

## Alternatives Considered

### 1. MySQL / MariaDB
- **Pros**: Wide adoption, good tooling, familiar to many developers
- **Cons**: Historically weaker JSON support, slightly different SQL dialect, asyncio driver (aiomysql) less mature than asyncpg

### 2. SQLite
- **Pros**: Zero infrastructure, simple setup, file-based
- **Cons**: No concurrent writes, no horizontal scaling, not suitable for multi-user production SaaS

### 3. MongoDB
- **Pros**: Flexible schema, easy horizontal sharding, native JSON
- **Cons**: No ACID transactions across collections (before 4.0), weaker relational integrity, harder to query with joins, async support less mature

### 4. CockroachDB
- **Pros**: Distributed SQL, auto-sharding, highly available
- **Cons**: More complex deployment, higher cost, unnecessary for initial scale

## Rationale

PostgreSQL was chosen because:

1. **ACID Compliance**: Full transaction support critical for subscription billing and user data integrity
2. **JSON/JSONB Support**: Native JSON columns allow flexible metadata without schema migrations
3. **asyncpg Driver**: The fastest PostgreSQL async driver for Python, purpose-built for asyncio
4. **SQLAlchemy 2.x Async**: Mature async ORM integration via `create_async_engine` and `AsyncSession`
5. **Extension Ecosystem**: uuid-ossp, pgcrypto, and other extensions available if needed
6. **Alembic Migrations**: SQLAlchemy's Alembic integrates seamlessly for schema version control
7. **Row-Level Security**: Available for multi-tenant data isolation if required in future
8. **Industry Standard**: Well-understood operational characteristics, strong community, excellent documentation

## Implementation Details

### Async Engine Configuration
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"prepared_statement_cache_size": 0},  # Avoids plan invalidation when create_all() runs CREATE TYPE DDL at startup
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
```

### Session Dependency
```python
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

### Schema Management
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "add gmail_credentials table"

# Apply all pending migrations
alembic upgrade head
```

## Consequences

### Positive
- Full relational integrity with foreign keys and constraints
- Async I/O with asyncpg eliminates blocking database calls
- Alembic provides version-controlled, reviewable schema changes
- Familiar SQL tooling (pgAdmin, psql, etc.) for debugging
- Supports connection pooling (PgBouncer) for high-concurrency deployments

### Negative
- Additional infrastructure to deploy and operate (unlike SQLite)
- asyncpg prepared statement cache must be disabled when `create_all()` runs `CREATE TYPE … AS ENUM` DDL at startup — this DDL invalidates cached plans on the same connection, causing the next enum-type existence check to fail with `ProgrammingError: cached statement plan is invalid` (fix: `prepared_statement_cache_size=0`)
- Async SQLAlchemy patterns are more complex than synchronous ORM patterns

### Neutral
- Redis is still required as a separate service (for Celery broker/result backend)
- Database backups must be configured separately (pg_dump or WAL archiving)

## Migration Strategy

All schema changes are managed via Alembic:
- Development: auto-generate from SQLAlchemy model changes
- Production: migrations run explicitly via `alembic upgrade head`
- Rollback: `alembic downgrade -1` for single-step rollback

## Related Decisions

- See ADR-001 for Celery (uses Redis, separate from PostgreSQL)
- See ADR-010 for hybrid configuration model (uses `app_settings` table in PostgreSQL)

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
