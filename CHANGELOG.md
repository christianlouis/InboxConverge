# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
- Reached 57% test coverage (up from 54%)

### Changed
- Reorganized documentation into `docs/` directory
- Improved error handling with specific exception types
- Updated datetime usage to timezone-aware
- Enhanced logging with structured context

### Fixed
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
