# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Prometheus metrics** (`/metrics` endpoint on the FastAPI backend, scraped every 15 s):
  - **HTTP layer** — `http_requests_total` (counter, labelled `method`/`endpoint`/`status_code`) and `http_request_duration_seconds` (histogram). Path segments that are numeric IDs are normalised to `{id}` to avoid label-set explosion.
  - **Mail processing** — `mail_processing_runs_total` (counter, by `status`: `completed` / `partial_failure` / `failed`), `mail_processing_emails_total` (counter, by `operation`: `fetched` / `forwarded` / `failed`), `mail_processing_duration_seconds` (histogram), `active_mail_accounts_total` (gauge — set each scheduler cycle).
  - **Gmail API** — `gmail_api_requests_total` (counter, by `operation` and `status`), `gmail_api_duration_seconds` (histogram, by `operation`), `gmail_token_refreshes_total` (counter), `gmail_credentials_invalidated_total` (counter).
  - **Authentication / OAuth** — `auth_logins_total` (counter, `method` × `status`), `auth_registrations_total` (counter, `method` × `status`), `oauth_callbacks_total` (counter, `provider` × `status`).
  - **Celery tasks** — `celery_tasks_total` (counter, `task_name` × `status`) and `celery_task_duration_seconds` (histogram, by `task_name`).
- **All metrics** defined as module-level singletons in `backend/app/core/metrics.py` (imported by HTTP middleware, task workers, GmailService, and auth endpoints).
- **Prometheus service** added to `docker-compose.new.yml` (port 9090, 30-day retention, config from `monitoring/prometheus.yml`).
- **Grafana service** added to `docker-compose.new.yml` (port 3001, auto-provisioned datasource + pre-built dashboard). Default credentials: `admin` / `admin`.
- **Pre-built Grafana dashboard** (`monitoring/grafana/dashboards/inboxrescue.json`) with five sections: Mail Processing, Gmail API, Authentication & OAuth, HTTP API, and Celery Workers. Dashboard auto-refreshes every 30 s.


- **Admin interface**: Superusers now have access to a dedicated Admin section in the sidebar with three pages:
  - **Admin Overview** (`/admin`): System-wide stats (total users, mail accounts, processing runs).
  - **Manage Users** (`/admin/users`): Table of all registered users with their subscription tier, status, mail account count, and last login. Admins can edit any user's name, email, plan, active status, and promote/demote admin (superuser) privileges. Users can be deleted (with confirmation).
  - **Manage Plans** (`/admin/plans`): Full CRUD for subscription plans—create, edit, and delete plans with fields for tier, name, pricing, max mailboxes, max emails/day, check interval, and support level.
- **Auto-promotion of admin email**: When the user whose email matches the `ADMIN_EMAIL` environment variable logs in or registers (via email/password or Google OAuth), they are automatically promoted to superuser. Default value is `christianlouis@gmail.com` (configurable via the `ADMIN_EMAIL` env var).
- **`is_superuser` field in API responses**: `GET /users/me` and all admin user endpoints now include `is_superuser` so the frontend can conditionally show admin UI.
- **New admin API endpoints** (all require superuser role):
  - `GET /admin/users` – List all users with mail account counts.
  - `GET /admin/users/{id}` – Get a single user's details.
  - `PUT /admin/users/{id}` – Update user details, plan, active status, and superuser flag.
  - `DELETE /admin/users/{id}` – Delete a user.
  - `GET /admin/plans` – List all subscription plans (including zero-price / inactive).
  - `POST /admin/plans` – Create a new subscription plan.
  - `PUT /admin/plans/{id}` – Update a subscription plan.
  - `DELETE /admin/plans/{id}` – Delete a subscription plan.
- **Admin badge in top bar**: Admin users see a purple shield icon and an "Admin" badge next to their email in the top navigation bar.
- **`DEFAULT_USER_TIER` env var**: Controls the subscription tier assigned to every new user on registration. Defaults to `free`. Set to `enterprise` (or any other tier) for B2B / Google Workspace installations where all employees should start on a zero-rate plan.
- **`ALLOWED_DOMAINS` env var**: Comma-separated list of permitted email domains (e.g. `company.com,subsidiary.com`). When set, only addresses from those domains may register or log in. Superusers always bypass this check. Empty (default) = no restriction (normal B2C mode).
- **Dynamic pricing section on landing page**: The home page now fetches `GET /subscriptions/plans` and renders a pricing section only when paid plans exist. In enterprise / all-zero-rate deployments the pricing section is silently hidden — the page just shows features and a "Get started free" CTA.
- **B2C copy and branding**: App renamed to **InboxRescue** throughout (was "POP3 Forwarder SaaS"). Landing page hero, feature cards, how-it-works, and footer rewritten in a personal, consumer-friendly tone. Pricing updated to €0.99 / €1.99 / €2.99 per month for Good / Better / Best plans.

### Fixed
- Test email sender name corrected from "Christian Loris" to "Christian Krakau-Louis".
- **Mailbox limit always hit at 1**: The `subscription_plans` table was never seeded, so the limit check fell back to the env-var default of `TIER_FREE_MAX_ACCOUNTS=1` for every user regardless of their tier. Fixed by:
  1. Seeding four default `SubscriptionPlan` rows at startup — **Free**, **Good** (€0.99), **Better** (€1.99), **Best** (€2.99).
  2. Rewriting the limit check to look up the user's active plan from the DB first, falling back to env-var config only when no plan row exists.
  3. Bypassing the limit entirely for superusers (admins can always add mailboxes).
  4. Adding plan limit fields (`max_mail_accounts`, `max_emails_per_day`, `check_interval_minutes`) to `GET /subscriptions/current`.
- **Zero-price plans hidden from public marketing**: `GET /subscriptions/plans` now only returns plans with `price_monthly > 0`. Zero-rate plans (Free tier, custom enterprise plans) are still managed by admins but never shown in the public pricing UI.

### Fixed
- Fixed `TypeError: can't subtract offset-naive and offset-aware datetimes` in `process_mail_account` task when computing `duration_seconds`. After a database refresh, `started_at` may be returned as a naive datetime; it is now normalized to UTC before subtraction.
- **Admin user not seeing admin dashboard**: Added startup auto-promotion in `main.py` lifespan handler — on every application start, if the user matching `ADMIN_EMAIL` exists in the database but does not yet have `is_superuser=True`, they are promoted immediately. This fixes accounts created before the auto-promotion-on-login code was deployed (e.g. `christianlouis@gmail.com` was logged in but saw no admin section).
- **Blank page on direct navigation to `/admin`, `/admin/users`, `/admin/plans`**: All three admin pages had `if (!user?.is_superuser) return null` before the `<AuthGuard>` was ever rendered. On a direct page load or refresh the Zustand store initialises with `user = null`, so the guard fired immediately and returned an empty render — `AuthGuard` was never mounted, its `checkAuth` effect never ran, and the user data was never fetched. Fixed by removing the early return and moving the superuser guard inside the `<AuthGuard>/<DashboardLayout>` tree, so authentication always runs first.

### Security
- Upgraded `python-jose` from 3.3.0 to 3.5.0 to fix CVE: algorithm confusion vulnerability with OpenSSH ECDSA keys (affected versions < 3.4.0).
- Upgraded `python-jose[cryptography]` from `3.3.0` to `3.4.0` to fix an algorithm-confusion vulnerability with OpenSSH ECDSA keys (CVE affects all versions < 3.4.0).

### Added
- **Impressum & Datenschutz pages**: Added `/impressum` (legal notice per § 5 TMG) and `/datenschutz` (comprehensive privacy policy covering GDPR/DSGVO, CCPA, LGPD, and other international regulations) as public pages. Footer links to both pages were added to the dashboard layout and the login page.
- **Gmail Debug Email**: New "Send Debug Email" button in the Gmail API settings section. When clicked, it injects a test email into the user's Gmail inbox via the Gmail API. The message appears to be from `christian@docuelevate.org`, includes the current date in the subject line, and is automatically labelled with `test` and `imported` (labels are created on first use) and placed in the inbox. Useful for verifying end-to-end Gmail API delivery without requiring a full mail-account polling cycle.
- `GmailService.get_or_create_label()` async method: lists the user's Gmail labels and returns the matching label ID, creating the label if it does not yet exist.
- `GmailService.inject_debug_email()` async method: builds a properly formatted RFC 2822 test message and calls `inject_email()` with the INBOX, `test`, and `imported` label IDs.
- `POST /providers/gmail/debug-email` backend endpoint: requires a valid Gmail credential, injects the debug email, and persists any auto-refreshed access token.
- `gmailApi.sendDebugEmail()` frontend API helper and `GmailDebugEmailResponse` TypeScript interface.
- **Unified Google OAuth flow**: Google Sign-In now requests all Gmail API scopes (`gmail.insert`, `gmail.labels`, `gmail.readonly`) in the same consent screen, so users no longer need a separate "Connect Gmail" step after signing in with Google. Gmail credentials are stored automatically on successful sign-in.
- `include_granted_scopes=true` added to both the login and Gmail authorize URLs so scope additions take effect for users who previously connected.

### Changed
- `providers.py` now imports both `encrypt_credential` and `decrypt_credential` from `app.core.security`.
- `gmail_service.py` now imports `textwrap`, `MIMEText`, `format_datetime`, and `datetime`/`timezone` for the debug email builder.
- `GMAIL_API_SCOPES` (providers endpoint) and `GMAIL_SCOPES` (GmailService) now include `gmail.readonly`, required for `users().getProfile()` access verification (fixes 403 insufficientPermissions errors).
- Google Sign-In authorize URL (`GET /auth/google/authorize-url`) now requests all six scopes with `access_type=offline`, `prompt=consent`, and `include_granted_scopes=true` so a refresh token is always issued.
- Gmail "Connect Gmail" button in Settings now redirects to `/auth/callback?state=gmail_connect` instead of the dedicated `/auth/gmail-callback` page, reducing the number of redirect URIs that must be registered in Google Cloud Console to one (`{origin}/auth/callback`).
- `auth_service.py` `get_google_user_info` now returns `access_token`, `refresh_token`, `expires_in`, and `scope` alongside user info so the login endpoint can persist Gmail credentials in the same request.

### Fixed
- Fixed mailbox edit form: username field was marked `required` but was never pre-populated (the backend intentionally excludes credentials from responses), making it impossible to save edits without re-entering the username. The backend now returns `username` in `MailAccountResponse` so the edit form can pre-populate it. All connection fields (protocol, host, port, use\_ssl, username) are now fully editable in edit mode. The Auto-Detect button is also shown in edit mode to re-detect server settings after a protocol change.
- Fixed mailbox edit form silently overwriting stored credentials with an empty string: when the password field was left blank during an edit the frontend sent `password: ""`, which the backend encrypted and stored, locking the user out. The frontend now only includes `password` in the update payload when it is non-empty, and the backend additionally guards against empty-string passwords.
- Fixed mailbox edit form sending all `MailAccountCreate` fields (including immutable ones like `username`, `host`, `port`) on update requests. The submit handler now builds a `MailAccountUpdate` payload containing all editable fields; `MailAccountUpdate` now covers every field in `MailAccountBase` (protocol, host, port, use\_ssl, use\_tls, username, email\_address, and the previously supported subset).
- Fixed `Exception terminating connection` error logged by Celery workers after every task run. The error was caused by `asyncio.run()` closing the event loop while the asyncpg connection pool still held open idle connections. The fix calls `await engine.dispose()` inside the task's `_run()` coroutine (within the same event loop) so all pooled connections are closed cleanly before the loop is torn down.
- Gmail API `verify_access()` returning 403 for tokens that lacked a read-capable scope: added `gmail.readonly` to all scope lists.

- Fixed three ESLint errors that caused CI to fail: removed unused `_setUser` store binding and unused `useAuthStore` import from `login/page.tsx`; replaced unused `_err` catch binding with a bare `catch {}` in `login/page.tsx`; removed a `useEffect` in `settings/page.tsx` that called `setProfileForm` synchronously (flagged by `react-hooks/set-state-in-effect`) — the effect was redundant because `useState` already initialises the form from the auth store's `user` object, which is the same value passed as `initialData` to `useQuery`.
- Fixed wizard to create new mail accounts showing a big grey screen: `bg-opacity-75` was removed in Tailwind CSS v4; replaced with the `/75` opacity modifier syntax (`bg-gray-500/75`) in `AddMailAccountModal` and `DashboardLayout` mobile overlay. Restructured the modal from the deprecated `inline-block align-bottom` centering trick to a proper flexbox layout with `relative z-10` on the modal content.
- Fixed mail account creation always failing with a backend validation error: `email_address` and `forward_to` are required fields in the backend schema but were missing from the `AddMailAccountModal` form. Added both fields to the form — `email_address` is auto-synced from the username input, and `forward_to` (destination Gmail address) is a new explicit field pre-populated from the logged-in user's email. Also added `delivery_method` selector and `delete_after_forward` checkbox.
- Implemented the Settings page (was a placeholder showing "coming soon"): now includes a Profile section to update name and email via `PUT /users/me`, an Account Information section showing subscription tier/status and member-since date, and a Security section.
- Fixed `sqlalchemy.exc.DBAPIError` raised by asyncpg when inserting timezone-aware `datetime.now(timezone.utc)` values into timezone-naive `DateTime` (TIMESTAMP WITHOUT TIME ZONE) columns: changed all `DateTime` column definitions in `database_models.py` to `DateTime(timezone=True)` (TIMESTAMP WITH TIME ZONE) and replaced all `default=datetime.utcnow` callable references with `default=lambda: datetime.now(timezone.utc)` for consistent, timezone-aware timestamps throughout the ORM.
- Fixed `ProgrammingError` (`cached statement plan is invalid`) raised by the asyncpg dialect during startup: SQLAlchemy's asyncpg wrapper maintains an LRU prepared-statement cache per connection (default size 100). When `Base.metadata.create_all()` executes `CREATE TYPE … AS ENUM` DDL inside a transaction, PostgreSQL invalidates the cached plans for that connection. The next enum-type existence check then fails because the dialect tries to reuse the now-stale prepared statement. Fix: set `prepared_statement_cache_size=0` in `connect_args` on `create_async_engine` to disable the cache entirely, which is the documented SQLAlchemy recommendation for DDL-at-startup scenarios.
- Fixed `UndefinedTableError` on first boot: the lifespan startup event now calls `Base.metadata.create_all()` via the async engine before attempting to seed default settings, so all tables are created automatically when the database is empty (e.g., fresh PostgreSQL container with no Alembic migrations run yet).
- Fixed frontend API calls being hardcoded to `http://localhost:8000` in production: `NEXT_PUBLIC_API_URL` is baked into the JavaScript bundle at Next.js build time, so it can never be overridden at container runtime. Replaced the `NEXT_PUBLIC_API_URL` mechanism with a Next.js Route Handler proxy at `/api/v1/[...path]` that reads `process.env.BACKEND_URL` at server startup and proxies all `/api/v1/*` requests to the real backend. The frontend Axios client now uses a relative base URL (`/api/v1`), which also eliminates the CORS issue since the browser only ever talks to the same-origin Next.js server. Update `BACKEND_URL=http://backend:8000` in `docker-compose.new.yml` (or your deployment env) to point the proxy at your backend.
- Fixed infinite spinning wheel on the home page: `authStore` no longer initialises `isLoading` as `true` unconditionally — it is now `false` when no access token exists in `localStorage`, so unauthenticated users see the landing page immediately instead of an endless spinner
- Home page now performs an auth check when a token is present in `localStorage`, redirecting authenticated users to the dashboard and clearing stale tokens on failure
- Wrapped `useSearchParams()` in a `Suspense` boundary in `frontend/src/app/auth/callback/page.tsx` to fix the Next.js build error: "useSearchParams() should be wrapped in a suspense boundary at page /auth/callback"
- Fixed TypeScript build error in `frontend/src/app/accounts/page.tsx`: replaced non-existent `account.username` with `account.email_address`, `account.last_checked_at` with `account.last_check_at`, and `account.last_error` with `account.last_error_message` (the backend intentionally excludes `username` from API responses for security)
- Fixed TypeScript error in `frontend/src/app/auth/callback/page.tsx`: `TokenResponse` doesn't include `user`; now fetches user via `userApi.getCurrentUser()` after OAuth token exchange
- Fixed TypeScript errors in `frontend/src/app/dashboard/page.tsx`: replaced non-existent `errors_count` with `emails_failed` on `ProcessingRun`
- Fixed TypeScript errors in `frontend/src/components/AddMailAccountModal.tsx`: removed invalid `account.username` access, added missing required fields to initial form state, and fixed autoDetect suggestions access
- Made `email_address`, `use_tls`, `forward_to` optional in the `MailAccountCreate` TypeScript interface to align with form usage
- Added typed suggestion fields to `autoDetect` return type in `api.ts`
- Excluded test files (`*.test.ts`, `*.spec.ts`) from TypeScript compilation in `tsconfig.json`
- Upgraded Node.js base image in `frontend/Dockerfile` from `node:18-alpine` to `node:20-alpine` to satisfy the Node.js >= 20.9.0 requirement for Next.js and fix Docker build failures
- Removed `actions/attest-build-provenance` step and associated `id-token: write` / `attestations: write` permissions from the CI `build` job — this action is not available for private user-owned repositories and caused every build to fail
- Downgraded `eslint` from `^10` to `^9` in the frontend to resolve `TypeError: contextOrFilename.getFilename is not a function` caused by ESLint 10 removing the `getFilename()` API used by `eslint-plugin-react` bundled in `eslint-config-next`
- Upgraded `sqlalchemy` from `2.0.25` to `2.0.48` to fix `AssertionError: Class ... directly inherits TypingOnly but has additional attributes` on Python 3.14 (`__static_attributes__`, `__firstlineno__`)

### Added
- **Architecture Decision Records ADR-003 through ADR-010**: Added eight new ADRs covering FastAPI web framework (ADR-003), PostgreSQL database (ADR-004), Celery task retry strategy (ADR-005), key management in production (ADR-006), JWT authentication (ADR-007), Next.js frontend (ADR-008), Gmail API email delivery (ADR-009), and hybrid configuration model (ADR-010)
- `userApi.updateProfile()` method in `frontend/src/lib/api.ts` for updating user profile via `PUT /users/me`
- **Account enable/disable toggle**: `PATCH /mail-accounts/{id}/toggle` backend endpoint and a Power-icon toggle button on each account card in the UI. Disabled accounts are visually dimmed. Re-enabling an account that was in ERROR state resets its status to ACTIVE so the scheduler picks it up again.
- **`is_enabled` checkbox in edit modal**: The Add/Edit mail account form now includes an "Enabled" checkbox so the flag can be set when creating or editing an account.
- **Message deduplication tracking** (`DownloadedMessageId` table): Both POP3 and IMAP fetch paths now track downloaded message UIDs so the same message is never delivered twice, even when `delete_after_forward=False`.
  - IMAP: messages are marked `\Seen` after fetching so they don't appear in future `UNSEEN` searches. DB UIDs provide a secondary guard.
  - POP3: UIDL-based deduplication; messages are skipped if their UID is already in the DB.
  - Old UID records are pruned by `cleanup_old_logs` after `days_to_keep` days.
- **Gmail API "one-click" OAuth grant flow**: New `GET /providers/gmail/authorize-url` and `POST /providers/gmail/callback` endpoints. The flow requests `gmail.insert + gmail.labels` scopes with `access_type=offline` so a long-lived refresh token is issued. A new `/auth/gmail-callback` frontend page handles the redirect from Google, exchanges the code, and redirects the user back to Settings.
- **Gmail token auto-refresh and persistence**: `GmailService` now records whether the `google-auth` library refreshed the access token during a Celery run. If it did, the Celery task writes the new access token and expiry back to `GmailCredential`, eliminating an unnecessary extra refresh call on the next run. A `401/403` or `invalid_grant` error during delivery marks `GmailCredential.is_valid = False` so the user is prompted to re-authorise.
- **Per-user SMTP relay configuration** (`UserSmtpConfig` table): New `GET/PUT/DELETE /users/smtp-config` endpoints let each user store their own SMTP relay (host, port, username, password, TLS flag). The Celery task checks for per-user SMTP first; falls back to the global `AppSetting` SMTP config if none is set.
- **Settings page – Gmail & SMTP sections**: The Settings page now shows a "Gmail API Delivery" card with connection status, "Connect Gmail" / "Re-authorise" / "Disconnect" buttons, and a token-lifetime explanation. An "SMTP Fallback" card lets users save their own SMTP relay credentials.
- **Celery scheduling fix**: `process_all_enabled_accounts` previously only polled accounts with `status IN [ACTIVE, TESTING]`, causing ERROR-status accounts to be silently skipped forever. It now polls all `is_enabled = True` accounts regardless of status, so transient errors are retried automatically.
- **Backend URL logged at startup**: The Next.js server now logs the resolved `BACKEND_URL` (e.g. `[proxy] BACKEND_URL = http://backend:8000`) via `src/instrumentation.ts` when the server starts, making it easy to diagnose `ECONNREFUSED` proxy errors. The per-request error log now also includes the full target URL.
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
