# ADR 010: Hybrid Configuration Model (Database + Environment Variables)

**Status:** Accepted  
**Date:** 2026-02-20  
**Deciders:** Development Team

## Context

The application requires configuration for many operational parameters:

1. **Bootstrap secrets** that must be available before the database is ready: `DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`
2. **SMTP relay settings** that operators want to change without redeployment: host, port, username, password
3. **Processing tuning parameters** that may need runtime adjustment: check interval, max emails per run, throttle rate
4. **Feature flags** for Gmail API, notifications, subscriptions
5. **Tier limits** (max accounts per subscription tier)

A pure environment-variable approach requires container redeployment for every config change. A pure database approach creates a chicken-and-egg problem for bootstrap settings.

## Decision

We will use a **hybrid configuration model** with the following priority chain:

```
1. Database (app_settings table)  ← highest priority
2. Environment variable / .env file
3. Built-in default               ← lowest priority
```

**Bootstrap settings** (`DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`) are **always** resolved from environment variables only, because the database connection depends on them.

**All other settings** are resolved by `ConfigService`, which checks the database first, then falls back to environment/defaults.

## Alternatives Considered

### 1. Environment Variables Only
- **Pros**: Simple, 12-factor compliant, works everywhere
- **Cons**: Config changes require redeployment, hard to manage across many instances, no UI for non-technical operators

### 2. Database-Only Configuration
- **Pros**: Runtime changes, admin UI possible, audit trail
- **Cons**: Chicken-and-egg for `DATABASE_URL` itself; database must exist before the app can read its own connection string

### 3. External Config Service (Consul, etcd)
- **Pros**: Distributed config, live reload, service discovery
- **Cons**: Additional infrastructure to deploy and operate, overkill for initial deployment

### 4. TOML / YAML Config Files
- **Pros**: Version-controlled, human-readable
- **Cons**: Requires file system mounts in Docker, config changes need file edits + possible restart

### 5. Pydantic Settings Only (env + .env files)
- **Pros**: Type-safe, validated at startup, no database dependency
- **Cons**: No runtime mutation, no admin UI, requires env changes for any tuning

## Rationale

The hybrid model was chosen because:

1. **Bootstrap Problem Solved**: Database connection string and secrets are always env-only — no circular dependency
2. **Runtime Mutability**: SMTP settings, tier limits, and feature flags can be changed via admin API without redeployment
3. **Operator Friendly**: Non-technical operators can use the admin UI or API to adjust settings
4. **Developer Friendly**: Developers can use `.env` files for local overrides without touching the database
5. **Gradual Migration**: Existing env-based deployments continue to work; database settings are additive

## Implementation

### Data Model

```python
# backend/app/models/database_models.py
class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

### ConfigService

```python
# backend/app/services/config_service.py
class ConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, key: str, default: str | None = None) -> str | None:
        """Resolve setting: DB → env → default."""
        # 1. Check database
        result = await self.db.get(AppSetting, key)
        if result is not None:
            return result.value
        # 2. Check environment
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value
        # 3. Return default
        return default

    async def set(self, key: str, value: str, description: str | None = None) -> None:
        """Persist setting to database (creates or updates)."""
        setting = AppSetting(key=key, value=value, description=description)
        await self.db.merge(setting)
        await self.db.commit()
```

### Default Seeding at Startup

On first boot, sensible defaults are written to the `app_settings` table if they don't already exist:

```python
# Called during lifespan startup
async def seed_default_settings(db: AsyncSession):
    defaults = {
        "CHECK_INTERVAL_MINUTES": ("5", "How often to check mail accounts"),
        "MAX_EMAILS_PER_RUN": ("50", "Maximum emails to process per run"),
        "SMTP_PORT": ("587", "SMTP relay port"),
        "TIER_FREE_MAX_ACCOUNTS": ("1", "Free tier account limit"),
        # ... etc.
    }
    for key, (value, description) in defaults.items():
        existing = await db.get(AppSetting, key)
        if existing is None:
            await db.add(AppSetting(key=key, value=value, description=description))
    await db.commit()
```

### Admin API Endpoints

```
GET    /api/v1/settings              # List all database settings (admin only)
PUT    /api/v1/settings/{key}        # Create or update a setting
DELETE /api/v1/settings/{key}        # Delete a setting (falls back to env/default)
POST   /api/v1/settings/seed-defaults # Re-seed all defaults
```

### Bootstrap Settings (Env-Only)

These are read via `pydantic-settings` (`BaseSettings`) and never looked up in the database:

| Setting | Required | Purpose |
|---------|----------|---------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | JWT signing key (≥32 chars) |
| `ENCRYPTION_KEY` | ✅ | Fernet master encryption key |
| `GOOGLE_CLIENT_ID` | Optional | Google OAuth2 |
| `GOOGLE_CLIENT_SECRET` | Optional | Google OAuth2 |

## Consequences

### Positive
- Bootstrap settings always resolved from env (no circular dependency)
- Runtime-mutable settings require no redeployment
- Default values seeded at startup so application works out-of-the-box
- Clear priority chain: database overrides env, env overrides code default
- Admin API provides complete CRUD on runtime settings

### Negative
- Two sources of truth for settings requires careful documentation
- Database settings take precedence over env — operators must know to check the database if env changes seem to have no effect
- `ConfigService` requires a database session (async), adding overhead for high-frequency config reads
- Settings cache is not implemented; every lookup hits the database (future improvement: TTL-based cache)

### Future Improvements

1. **In-Memory Cache**: Cache settings with a short TTL (e.g., 30 seconds) to reduce database load
2. **Change Notifications**: Pub/sub via Redis to notify workers of setting changes
3. **Typed Settings Schema**: JSON Schema validation for setting values
4. **Audit Trail**: Record who changed each setting and when

## Related Decisions

- See ADR-004 for PostgreSQL (stores `app_settings` table)
- See ADR-006 for key management (bootstrap secrets are env-only)
- See ADR-003 for FastAPI dependency injection of `ConfigService`

## References

- [12-Factor App: Config](https://12factor.net/config)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
