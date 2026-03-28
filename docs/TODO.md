# TODO & Milestones

Comprehensive task breakdown for repository improvements and production readiness.

## ✅ Recently Completed

- [x] **IMAP RFC 3501 flag syntax & aioimaplib UID SEARCH fix**: `_fetch_imap_emails`
  now uses a plain `SEARCH UNSEEN` + `FETCH (UID)` to resolve sequence numbers to
  stable UIDs (aioimaplib blocks `uid("search")`), and wraps all flag names in
  parentheses (`+FLAGS (\Seen)`, `+FLAGS (\Deleted)`) as required by RFC 3501 to
  prevent T-Online and other strict servers from dropping the connection with
  "Too many invalid IMAP commands".
- [x] **CI pipeline fixes**: Added `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` to `ci.yml` (Node.js 20 deprecation), fixed Codecov `file:` → `files:` invalid input, replaced `<img>` with `<Image />` from `next/image` in `ProviderWizard.tsx` (ESLint no-img-element).
- [x] **IMAP reliability: switched to UID-based commands** — `_fetch_imap_emails` now uses `UID SEARCH`, `UID FETCH`, and `UID STORE` throughout.  Sequence numbers are volatile (they shift on expunge), causing "Too many invalid IMAP commands" on strict servers (e.g. T-Online).  UIDs are stable.  The per-message `STORE +FLAGS \Seen` (redundant — RFC822 sets it implicitly) and per-message `STORE +FLAGS \Deleted` are replaced with single batch commands.  Stale already-seen UIDs are re-marked `\Seen` in one command.  Logout is now in a `finally` block so a mid-session `BYE` is handled gracefully.
- [x] Fixed timezone display bug in Mailbox Activity and Admin Logs pages: ISO timestamps without a `Z` suffix were parsed as local time by JavaScript, shifting "Xm ago" / "Xh ago" displays and absolute dates by the client's UTC offset.
- [x] Fixed worker `send_user_notification` using rolled-back DB session causing `greenlet_spawn has not been called` errors; status/`last_check_at` now always committed before sending notifications via a fresh session.
- [x] **Dashboard redesign**: Replaced noisy "Recent Processing Runs" table with a per-account "Mailbox Status" view showing last-check status (OK/Error/Pending), relative timestamp, error messages, and lifetime counters. Stats cards updated to show all-time processed count and accounts-with-errors count.
- [x] **Provider logos now saved on account creation**: `provider_name` field added to `MailAccountCreate` and `MailAccountUpdate` schemas (backend and frontend). `ProviderWizard` now passes `provider_name` in its `onSelect` callback; `AddMailAccountModal` stores it so logos are displayed correctly on the accounts page.
- [x] **Fetch button UX improvements**: The "fetch emails" button on the accounts page now shows a "Fetch" text label for clarity, a tooltip explaining its purpose, a spinning "Fetching…" state during the API call, and a brief green "Queued!" confirmation after success.

- [x] **Pull Now**: Added "Pull Now" button on Accounts page that immediately queues a `process_mail_account` Celery task via `POST /mail-accounts/{id}/pull-now`. Button shows spinner while in flight and is disabled for inactive accounts.
- [x] Fixed 21 mypy type errors: `Column[T]` vs native type mismatches in `notification_service.py`, `mail_processor.py`, `auth.py`, `tasks.py`, `providers.py`, `mail_accounts.py`, and `main.py` (`lifespan` parameter rename).
- [x] **Provider logos rework**: Logos now displayed as full-width banner strips at the top of each account card using `next/image fill + object-contain`. Handles all aspect ratios (1:1 square to 6:1 wordmark) without distortion. Proton Mail added.
- [x] **Proton Mail provider**: Added Proton Mail preset in backend and ProviderWizard frontend. Domains: proton.me, protonmail.com, protonmail.ch, pm.me. Auto-detect and IMAP/POP3 Bridge settings included.
- [x] Redesigned user-facing Logs page to mailbox-centric "Mailbox Activity" view: shows last check status per account + only successful pulls, suppressing noise from empty polling cycles.
- [x] Added `has_emails` filter to `GET /processing-runs` and `GET /mail-accounts/{id}/processing-runs` API endpoints.
- [x] Rename entire project to **InboxConverge**: all user-visible strings, Docker container/image names, DB defaults, monitoring, and docs updated.
- [x] Domain updated to `inboxconverge.com`; contact email defaults to `christian@inboxconverge.com`.
- [x] New configurable env vars: `CONTACT_EMAIL`, `APP_URL`, `NEXT_PUBLIC_APP_NAME`.
- [x] Fixed Black formatting failure in CI (`admin.py` reformatted).
- [x] Fixed `/processing-runs` endpoint 404s caused by duplicate path prefix in `logs.py`.
- [x] Added Semantic Release workflow (`release.yml`) for automatic versioning and GitHub Releases.
- [x] Added `pyproject.toml` with `[tool.semantic_release]` configuration.
- [x] Fixed GitOps `update-k8s-manifest` job: corrected image tag computation and `yq` patterns to use `registry.cklnet.com` (private registry) matching the actual k8s manifest image references, so SHA-pinned tags are properly applied on each deploy.
- [x] Added GitOps auto-deployment step in `ci.yml` to update preprod k8s manifest in `k8s-cluster-state` repo.
- [x] Fixed GitOps `update-k8s-manifest` job: added PAT availability check to skip gracefully when `GH_PAT` secret is not configured, fixing 403 "Write access to repository not granted" pipeline failure.
- [x] Fixed Celery `TypeError: can't subtract offset-naive and offset-aware datetimes` in `process_all_enabled_accounts` — all mail accounts were silently skipped on every scheduled run.
- [x] Fixed **Test Connection** always reporting success regardless of authentication outcome.
- [x] Added `POST /mail-accounts/{account_id}/test` endpoint to test existing accounts with stored credentials.

## 🔴 Critical - Security (In Progress)

### Completed ✅
- [x] Add SECRET_KEY validation on startup
- [x] Add ENCRYPTION_KEY validation on startup
- [x] Implement security headers middleware (X-Frame-Options, CSP, HSTS, etc.)
- [x] Implement CSRF protection middleware
- [x] Document all error codes in docs/ERRORS.md
- [x] Create security ADR (Architecture Decision Records)
- [x] Upgrade `python-jose` 3.3.0 → 3.5.0 (algorithm confusion with OpenSSH ECDSA keys, CVE, affected < 3.4.0)

### In Progress 🔨
- [ ] Enable rate limiting per user/tier
- [x] Fix bare exception handlers throughout codebase
- [x] Update datetime usage to timezone-aware (`DateTime(timezone=True)` columns and `lambda: datetime.now(timezone.utc)` defaults; fixes `DBAPIError` from asyncpg on timezone-naive columns)
- [x] Fix `Exception terminating connection` in Celery workers: call `await engine.dispose()` inside task coroutine so pooled asyncpg connections are closed before the event loop is torn down
- [ ] Validate redirect_uri to prevent open redirect vulnerabilities
- [ ] Add per-user random salt for encryption (currently deterministic)

### Not Started 📋
- [ ] Implement audit logging middleware
- [ ] Add 2FA support
- [ ] Implement API key authentication
- [ ] Set up secrets management (HashiCorp Vault or AWS Secrets Manager)
- [ ] Professional security audit/penetration testing

---

## 🤖 High Priority - Agentic Coding Infrastructure

### Completed ✅
- [x] Create `.github/ISSUE_TEMPLATE/` (bug_report.md, feature_request.md, test_needed.md)
- [x] Create `.github/PULL_REQUEST_TEMPLATE.md`
- [x] Create `docs/CODING_PATTERNS.md` with best practices
- [x] Create `docs/ERRORS.md` documenting error codes
- [x] Create `docs/adr/` for Architecture Decision Records
- [x] Add `Makefile` with common development tasks
- [x] Add `.pre-commit-config.yaml` with black, ruff, mypy
- [x] Create `CHANGELOG.md` with version history
- [x] Add `.yamllint.yml` configuration
- [x] Add `.secrets.baseline` for detect-secrets

### In Progress 🔨
- [x] Reorganize documentation into `docs/` directory
- [x] Complete ADR documentation (add ADR-003 through ADR-010)
- [ ] Create GitHub Projects board for task management

### Not Started 📋
- [ ] Add `commitlint.config.js` for conventional commits
- [ ] Create video tutorials for setup
- [ ] Add interactive setup wizard
- [ ] Document migration path from legacy script
- [ ] Create performance benchmarks baseline
- [ ] Set up Discord/Slack community

---

## 🧪 High Priority - Testing Infrastructure

### Completed ✅
- [x] Create `backend/tests/` directory structure (unit, integration, e2e)
- [x] Add `backend/tests/conftest.py` with fixtures
- [x] Add `backend/pytest.ini` configuration
- [x] Create sample unit tests (test_security.py, test_config.py)
- [x] Add user and mail account factory fixtures
- [x] Write unit tests for security module (100% coverage)
- [x] Write unit tests for middleware (98% coverage)
- [x] Write unit tests for schemas and validation
- [x] Write unit tests for application factory and core endpoints
- [x] Reach 50%+ test coverage (currently 59%)

### In Progress 🔨
- [ ] Write unit tests for authentication (target 80%+ coverage)
- [ ] Write unit tests for mail processing
- [ ] Write integration tests for API endpoints
- [ ] Write tests for Celery tasks

### Not Started 📋
- [ ] Add end-to-end tests
- [ ] Add performance/load tests
- [ ] Create mock POP3/IMAP server for testing
- [ ] Add test data seeding scripts
- [ ] Reach 80%+ code coverage

---

## 🔄 High Priority - CI/CD Pipeline

### Completed ✅
- [x] Create `.github/workflows/test.yml` for automated testing
- [x] Create `.github/workflows/lint.yml` for code quality checks
- [x] Create `.github/workflows/security.yml` for security scanning
- [x] Existing `.github/workflows/docker-build.yml` for Docker images
- [x] Set up automatic dependency updates (Dependabot)
- [x] Merge Dependabot dependency updates (PRs #26–#49)
- [x] Remove CodeQL checks from CI (was blocking builds)
- [x] Upgrade SQLAlchemy to 2.0.48 to fix Python 3.14 test failures
- [x] Fix Docker build failure: wrap `useSearchParams()` in Suspense boundary in `/auth/callback` page
- [x] Fix frontend API URL hardcoded to `localhost:8000` in production: replaced build-time `NEXT_PUBLIC_API_URL` with a runtime Next.js Route Handler proxy (`/api/v1/[...path]`) reading `BACKEND_URL` at server startup
- [x] Log `BACKEND_URL` at frontend server startup and include target URL in per-request proxy error messages
- [x] Fix `UndefinedTableError` on first boot: lifespan event now runs `Base.metadata.create_all()` so tables are created automatically when no migrations have been applied
- [x] Fix `ProgrammingError` (cached statement plan is invalid) during startup: set `prepared_statement_cache_size=0` on the asyncpg engine to prevent plan invalidation when `CREATE TYPE` DDL runs at startup

### In Progress 🔨
- [ ] Configure branch protection rules
- [ ] Set up Codecov integration

### Not Started 📋
- [x] Add deployment workflow (dual-registry: GHCR + private registry)
- [ ] Add release workflow with automated changelog
- [ ] Configure status checks for PRs
- [ ] Add performance regression detection

---

## 🟡 Medium Priority - Code Quality

### Completed ✅
- [x] Create coding patterns documentation
- [x] Define error code structure

### In Progress 🔨
- [ ] Add comprehensive type hints to all functions
- [ ] Add docstrings to all public methods
- [ ] Move magic numbers to constants
- [ ] Improve error messages with context

### Not Started 📋
- [ ] Add database indexes for performance
- [ ] Complete database migration scripts
- [ ] Implement retry logic for Celery tasks
- [ ] Add structured JSON logging
- [ ] Refactor mixed async/blocking code in mail processor
- [ ] Complete API documentation with examples

---

## 📦 Medium Priority - Production Readiness

### Completed ✅
- [x] Basic health check endpoint exists
- [x] Database-backed configuration (`AppSetting` model + `ConfigService`)
- [x] Admin API for managing settings (`/api/v1/settings`)
- [x] Default settings seeded on first startup

### In Progress 🔨
- [ ] Improve health checks (DB/Redis connectivity)

### Not Started 📋
- [ ] Create production docker-compose.yml
- [ ] Add Kubernetes manifests (deployment, service, ingress)
- [ ] Create Helm chart for easy deployment
- [ ] Add nginx reverse proxy configuration
- [ ] Document backup strategy
- [ ] Create comprehensive deployment guide
- [ ] Set up log aggregation (ELK/Loki)
- [ ] Configure alerting system

---

## 📊 Medium Priority - Observability

### Completed ✅
- [x] Add Prometheus metrics endpoint (`/metrics`) to FastAPI backend
- [x] Instrument HTTP layer (request count + latency histograms per method/endpoint/status)
- [x] Instrument mail-processing tasks (runs, emails fetched/forwarded/failed, duration)
- [x] Instrument Gmail API operations (inject, verify, get_profile, get_label — count + latency)
- [x] Track OAuth token refreshes and credential invalidation events
- [x] Instrument auth endpoints (logins, registrations, OAuth callbacks — by method/status)
- [x] Instrument Celery tasks (count + duration per task name)
- [x] Add Prometheus scrape config (`monitoring/prometheus.yml`)
- [x] Add Grafana auto-provisioned datasource and pre-built dashboard (`monitoring/grafana/`)
- [x] Add Prometheus + Grafana services to `docker-compose.new.yml` (Grafana on port 3001)

### Not Started 📋
- [ ] Integrate Sentry for error tracking
- [x] Add structured logging with correlation IDs (per-email ProcessingLog entries now captured in DB)
- [ ] Add APM (Application Performance Monitoring)
- [ ] Set up uptime monitoring
- [ ] Create runbook for common issues

---

## ✨ Low Priority - Feature Completion

### Not Started 📋
- [ ] Implement Stripe webhook handling
- [ ] Add scheduled Celery tasks for email processing
- [x] Account enable/disable toggle (UX + backend)
- [x] Per-user SMTP configuration (UX + backend)
- [x] Gmail API one-click OAuth grant flow with token refresh and revocation handling
- [x] Configurable Gmail import labels (default `{{source_email}}` + `imported`, editable in Settings with reset-to-default action)
- [x] Decoupled Google Sign-In from Gmail API permissions: login now requests only basic profile scopes; Gmail access is granted separately via Settings
- [x] Message deduplication (POP3 UIDL + IMAP \Seen flag + DB tracking)
- [x] **Debug email**: "Send Debug Email" button in Settings injects a test message (from christian@docuelevate.org, dated today, labelled `test` + `imported`, placed in inbox) to verify end-to-end Gmail API delivery
- [x] **Logging & reporting**: per-email ProcessingLog capture in worker; user `/logs` page; admin `/admin/logs` page; GDPR masking utilities (`gdpr.py`)
- [ ] Implement GDPR data export endpoint
- [x] Complete notification service integration (Apprise)
- [ ] Add advanced email filtering
- [ ] Implement OAuth2 for Gmail (instead of App Passwords)
- [ ] Add attachment handling improvements
- [ ] Add email archiving feature
- [ ] Implement webhook support for external integrations

---

## 🖥️ High Priority - Frontend Completion

The Next.js frontend has pages and components implemented but is **not functional**
because the API client layer is missing.

### Critical Blockers 🔴
- [x] Create `frontend/src/lib/api.ts` — API client using axios
  - Exports: `authApi`, `mailAccountsApi`, `processingRunsApi`, `userApi`
  - Exports types: `User`, `MailAccount`, `MailAccountCreate`, `ProcessingRun`
  - 8 files import from `@/lib/api` — all compilation errors resolved
- [x] Fix infinite spinner on home page: `isLoading` now initialises based on token presence; home page performs auth check when token exists

### Existing Pages (UI done, need API wiring) 🔨
- [x] Landing page (`app/page.tsx`)
- [x] Login page with email/password + Google OAuth
- [x] Registration page
- [x] OAuth callback handler
- [x] Dashboard with stats cards and processing runs table
- [x] Mail accounts list with CRUD operations + enable/disable toggle
- [x] Settings page — Profile, Gmail API connection, SMTP relay, Account info, Security
- [x] `AddMailAccountModal` component (auto-detect, test connection, all required fields, is_enabled checkbox)
- [x] Fix `AddMailAccountModal` edit mode: backend now returns `username` in `MailAccountResponse`; all fields (including protocol, host, port, use\_ssl, username) are editable in edit mode and pre-populated from the stored account; Auto-Detect is shown in edit mode too; only password is omitted from the update payload when left blank
- [x] `DashboardLayout` with responsive sidebar
- [x] `AuthGuard` for protected routes
- [x] Fix wizard grey screen (Tailwind v4 `bg-opacity` → `/75` syntax, modal restructure)
- [x] `/auth/gmail-callback` page for Gmail OAuth one-click flow
- [x] **`/logs` page** — user processing history: paginated runs table with expandable per-email log panel (subject, sender, size, status)
- [x] **Dashboard** — "Recent Processing Runs" now wired to real `/processing-runs` endpoint; shows account name and links to `/logs`

### Not Started 📋
- [ ] End-to-end testing of frontend against backend API
- [ ] Error boundary components
- [ ] Loading skeletons / proper loading states
- [ ] Notification preferences UI
- [x] Notification channels page (`/notifications`) with full CRUD, wizard, and test button
- [x] Apprise-powered notification wizard for Telegram, Discord, Slack, Email, Webhook, and custom URLs
- [x] Admin system alert channels section (`/admin` page) with full CRUD and test
- [ ] Subscription management / billing UI

### Admin Interface ✅
- [x] Admin section in sidebar (visible to superusers only)
- [x] Admin overview page (`/admin`) with system-wide stats
- [x] User management page (`/admin/users`) — list, edit, delete users; assign plans; promote/demote admin
- [x] Plan management page (`/admin/plans`) — full CRUD for subscription plans (mailboxes, emails/day, interval, pricing)
- [x] `ADMIN_EMAIL` env var with default `christian@inboxconverge.com`; admin auto-promoted on login and on every application startup (fixes pre-existing accounts)
- [x] `is_superuser` exposed in `/users/me` response
- [x] Admin badge (purple shield) shown in top bar for superusers
- [x] Fix blank page on direct navigation to `/admin*`: moved superuser guard inside `<AuthGuard>` so auth check always runs on fresh load
- [x] **`/admin/logs` page** — system-wide processing activity: expandable run table + flat per-email log table with GDPR-masked sender addresses; filterable by user ID, status, log level

---

## 📅 Milestone Timeline

### Milestone 1: Security & Infrastructure (Week 1-2) 🔴
**Goal**: Make repository secure and AI-agent friendly

**Tasks**:
- Complete all security hardening
- Finish agentic coding infrastructure
- Set up CI/CD pipeline
- Reach 50% test coverage

**Success Criteria**:
- All security validators passing
- CI/CD running on all PRs
- Issue/PR templates in use
- Pre-commit hooks working

---

### Milestone 2: Testing & Quality (Week 3-4) 🧪
**Goal**: Establish quality baseline

**Tasks**:
- Write comprehensive test suite
- Reach 80% code coverage
- Fix all linting issues
- Complete API documentation

**Success Criteria**:
- 80%+ test coverage
- All tests passing
- Zero critical security issues
- API docs complete

---

### Milestone 3: Production Readiness (Week 5-6) 📦
**Goal**: Ready for production deployment

**Tasks**:
- Complete observability setup
- Add Kubernetes manifests
- Implement rate limiting
- Add audit logging
- Complete deployment documentation

**Success Criteria**:
- Can deploy to Kubernetes
- Monitoring and alerting active
- Health checks comprehensive
- Deployment documented

---

### Milestone 4: Feature Completion (Week 7-8) ✨
**Goal**: Complete remaining features

**Tasks**:
- Implement Stripe webhooks
- Add Celery scheduled tasks
- Complete notification integration
- Build basic frontend

**Success Criteria**:
- Stripe integration working
- Scheduled tasks running
- Notifications functional
- Basic UI available

---

## 📊 Progress Tracking

### Overall Progress by Category

| Category | Progress | Status |
|----------|----------|--------|
| Security | 60% | 🟡 In Progress |
| Agentic Infrastructure | 98% | 🟢 Near Complete |
| Testing | 59% | 🟡 In Progress |
| CI/CD | 80% | 🟢 Near Complete |
| Code Quality | 40% | 🔴 Needs Work |
| Production Ready | 30% | 🔴 Needs Work |
| Observability | 10% | 🔴 Needs Work |
| Backend Features | 85% | 🟢 Near Complete |
| Frontend | 65% | 🟢 Near Complete |

**Overall Repository Readiness**: 55% ⚠️

---

## 🎯 Next Actions (Priority Order)

1. **Immediate** (Today):
   - [x] Create `frontend/src/lib/api.ts` (frontend is broken without it)
   - [x] Fix remaining security issues (bare excepts, datetime, redirect_uri)
   - [x] Add backend endpoint for processing runs (needed by dashboard)
   - [x] Build logging & reporting: per-email ProcessingLog capture, user `/logs` page, admin `/admin/logs` page, GDPR masking

2. **This Week**:
   - [ ] Enable rate limiting
   - [ ] Add audit logging
   - [ ] Write more unit tests (target 70% coverage)
   - [x] Complete ADR documentation
   - [ ] End-to-end test frontend against backend

3. **Next Week**:
   - [ ] Kubernetes manifests
   - [ ] Prometheus metrics
   - [ ] Sentry integration
   - [ ] Production docker-compose

4. **This Month**:
   - [ ] 80% test coverage
   - [ ] Complete all documentation
   - [ ] Professional security audit
   - [ ] First production deployment

---

## 📝 Notes

### Dependencies Between Tasks
- Security hardening must complete before production deployment
- Test infrastructure needed before reaching coverage goals
- CI/CD needed before enforcing quality standards
- Observability needed before production monitoring

### AI Agent Readiness
After Milestone 1 completes, AI agents will have:
- Clear issue templates to report bugs
- Coding patterns to follow
- Test fixtures to write tests
- CI/CD to validate changes
- Pre-commit hooks to enforce quality

### Production Blockers
Must complete before production:
1. All critical security issues
2. Basic monitoring/alerting
3. Backup strategy
4. Incident response plan
5. 50%+ test coverage

---

**Last Updated**: 2026-03-25
**Maintained By**: Development Team
**Review Frequency**: Weekly
