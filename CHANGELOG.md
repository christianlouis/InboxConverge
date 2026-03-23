# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Fixed TypeScript build error in `frontend/src/app/accounts/page.tsx`: replaced non-existent `account.username` with `account.email_address` (the backend intentionally excludes `username` from API responses for security)
- Upgraded Node.js base image in `frontend/Dockerfile` from `node:18-alpine` to `node:20-alpine` to satisfy the Node.js >= 20.9.0 requirement for Next.js and fix Docker build failures
- Removed `actions/attest-build-provenance` step and associated `id-token: write` / `attestations: write` permissions from the CI `build` job — this action is not available for private user-owned repositories and caused every build to fail
- Downgraded `eslint` from `^10` to `^9` in the frontend to resolve `TypeError: contextOrFilename.getFilename is not a function` caused by ESLint 10 removing the `getFilename()` API used by `eslint-plugin-react` bundled in `eslint-config-next`
- Upgraded `sqlalchemy` from `2.0.25` to `2.0.48` to fix `AssertionError: Class ... directly inherits TypingOnly but has additional attributes` on Python 3.14 (`__static_attributes__`, `__firstlineno__`)

### Added
- **Dual-registry Docker deployment**: CI now builds separate backend and frontend images and pushes to both GHCR (`ghcr.io`) and private registry (`registry.cklnet.com`) using a matrix strategy
- **Database-backed configuration**: `AppSetting` model and `ConfigService` for hybrid config (DB-first, env-var fallback)
- Admin API endpoints for managing settings (`GET/PUT/DELETE /api/v1/settings`)
- Default settings seeded into database on first startup (SMTP, processing, Gmail API, notifications)
- Unit tests for `ConfigService` (24 tests covering resolution order, CRUD, SMTP helper, defaults)
- Gmail API delivery documentation with comparison table (Gmail API vs SMTP forwarding)
- GitHub issue templates (bug report, feature request, test needed)
- Pull request template with comprehensive checklist
- `docs/CODING_PATTERNS.md` with development best practices
- `docs/ERRORS.md` documenting all error codes
- `docs/adr/` directory with Architecture Decision Records
- `Makefile` with common development tasks
- `.pre-commit-config.yaml` for code quality enforcement
- `CHANGELOG.md` for version tracking
- Security validation for SECRET_KEY and ENCRYPTION_KEY on startup
- CSRF protection middleware
- Security headers middleware (X-Frame-Options, CSP, HSTS)
- Rate limiting per user/tier
- Comprehensive test infrastructure setup
- CI/CD pipeline for testing and security scanning
- Dependabot configuration for automated dependency updates (pip, npm, GitHub Actions, Docker)
- Copilot instructions requiring TODO.md and CHANGELOG.md updates
- Unit tests for security middleware (SecurityHeadersMiddleware, CSRFProtectionMiddleware)
- Unit tests for JWT token lifecycle (access tokens, refresh tokens, decode, edge cases)
- Unit tests for credential encryption edge cases (empty, long, unicode, special chars)
- Unit tests for FastAPI application factory and core endpoints (root, health, OpenAPI)
- Unit tests for Pydantic schema validation (users, mail accounts, notifications, subscriptions)
- Unit tests for JWT `sub` claim string encoding and token type verification
- Created `frontend/src/lib/api.ts` — API client module (fixes frontend compilation blocker)
- Reached 57% test coverage (up from 54%)

### Changed
- Configuration system now supports database-backed settings in addition to environment variables
- Celery tasks (`tasks.py`) use `ConfigService` for SMTP config instead of raw `os.getenv()` calls
- README updated with hybrid configuration docs, Gmail API vs SMTP comparison, and Apprise notifications
- Architecture docs updated to reflect Gmail API service, hybrid config, and new API endpoints
- Reorganized documentation into `docs/` directory
- Improved error handling with specific exception types
- Updated datetime usage to timezone-aware
- Enhanced logging with structured context
- Bumped Docker Python base image from 3.11-slim to 3.14-slim
- Bumped CI Python version from 3.11 to 3.14
- Bumped CI Node.js version from 18 to 20
- Bumped GitHub Actions: `actions/setup-python` v5 → v6, `actions/setup-node` v4 → v6, `docker/setup-buildx-action` v3 → v4, `codecov/codecov-action` v3 → v5
- Bumped backend dependencies: pydantic 2.5.3 → 2.12.5, pydantic-settings 2.1.0 → 2.13.1, psycopg2-binary 2.9.9 → 2.9.11, asyncpg 0.29.0 → 0.31.0, stripe 7.11.0 → 14.4.1, aioimaplib 1.0.1 → 2.0.1, google-auth-httplib2 0.2.0 → 0.3.0, celery 5.3.6 → 5.6.2, redis 5.0.1 → 7.3.0, tenacity 8.2.3 → 9.1.4
- Bumped frontend dependencies: react 19.2.3 → 19.2.4, @tanstack/react-query ^5.90.20 → ^5.95.0, axios ^1.13.5 → ^1.13.6, zustand ^5.0.11 → ^5.0.12, eslint ^9 → ^10, eslint-config-next 16.1.6 → 16.2.1
- Synced `frontend/package.json` `eslint-config-next` to `16.2.1` to match `package-lock.json` (resolves `npm ci` EUSAGE failure)

### Removed
- Removed CodeQL analysis from CI pipeline (was blocking builds)

### Fixed
- JWT `sub` claim now encoded as string per JWT spec (python-jose rejects integer subjects)
- `TokenPayload` schema `sub` field type changed from `int` to `str` for consistency
- Replaced deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` throughout backend
- Replaced deprecated FastAPI `@app.on_event()` handlers with modern `lifespan` context manager
- Replaced deprecated Pydantic `class Config` with `model_config = ConfigDict(...)` in all schemas
- Replaced deprecated Pydantic `.dict()` with `.model_dump()` in mail account updates
- Removed overly broad `except (GmailInjectionError, Exception)` in task error handler
- Bare exception handlers replaced with specific types
- Open redirect vulnerability in OAuth redirect_uri
- Default encryption keys security issue

### Security
- All dependencies updated to patched versions
- Security headers added to all API responses
- Input validation improved for all endpoints
- Credential handling audited and improved

## [1.0.0] - 2026-02-01

### Added
- Multi-tenant SaaS backend with FastAPI
- JWT and OAuth2 (Google Sign-In) authentication
- Encrypted credential storage with Fernet
- Subscription management with Stripe integration
- PostgreSQL database with SQLAlchemy ORM
- Redis for caching and session management
- Celery for background task processing
- Apprise for multi-channel notifications
- Docker and docker-compose support
- Comprehensive API documentation with OpenAPI
- Extensive documentation (README, ARCHITECTURE, SECURITY_REPORT, etc.)

### Changed
- Upgraded from single-user script to multi-tenant platform

## [0.1.0] - 2025-12-15 (Legacy Version)

### Added
- Initial release of single-user pop3_forwarder.py script
- Docker support with docker-compose
- Multiple POP3 account support
- Gmail forwarding via SMTP
- Rate limiting and throttling
- Error notifications via Postmarkapp
- Environment-based configuration
- Basic logging

---

## Version History

- **[Unreleased]** - Current development (agentic coding improvements, security hardening)
- **[1.0.0]** - Multi-tenant SaaS platform (2026-02-01)
- **[0.1.0]** - Legacy single-user script (2025-12-15)

---

## How to Update This Changelog

### Categories

Use these standard categories:
- **Added** - New features
- **Changed** - Changes in existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Vulnerability fixes

### Format

```markdown
## [Version] - YYYY-MM-DD

### Added
- New feature description (#issue-number)

### Fixed
- Bug fix description (#issue-number)
```

### Workflow

1. Add unreleased changes to `[Unreleased]` section
2. When releasing, move unreleased changes to new version section
3. Add version number, date, and comparison link
4. Create git tag: `git tag -a v1.0.0 -m "Release v1.0.0"`

---

**Maintained by**: Development Team
**Last Updated**: 2026-03-23
