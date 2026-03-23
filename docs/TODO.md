# TODO & Milestones

Comprehensive task breakdown for repository improvements and production readiness.

## 🔴 Critical - Security (In Progress)

### Completed ✅
- [x] Add SECRET_KEY validation on startup
- [x] Add ENCRYPTION_KEY validation on startup
- [x] Implement security headers middleware (X-Frame-Options, CSP, HSTS, etc.)
- [x] Implement CSRF protection middleware
- [x] Document all error codes in docs/ERRORS.md
- [x] Create security ADR (Architecture Decision Records)

### In Progress 🔨
- [ ] Enable rate limiting per user/tier
- [ ] Fix bare exception handlers throughout codebase
- [ ] Update datetime usage to timezone-aware (datetime.now(timezone.utc))
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
- [ ] Complete ADR documentation (add ADR-003 through ADR-010)
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
- [x] Reach 50%+ test coverage (currently 57%)

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

### In Progress 🔨
- [ ] Configure branch protection rules
- [ ] Set up Codecov integration

### Not Started 📋
- [ ] Add deployment workflow (staging/production)
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

### In Progress 🔨
- [ ] Improve health checks (DB/Redis connectivity)
- [ ] Add environment variable validation

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

### Not Started 📋
- [ ] Add Prometheus metrics endpoints
- [ ] Integrate Sentry for error tracking
- [ ] Add structured logging with correlation IDs
- [ ] Create Grafana dashboard templates
- [ ] Document monitoring setup
- [ ] Add APM (Application Performance Monitoring)
- [ ] Set up uptime monitoring
- [ ] Create runbook for common issues

---

## ✨ Low Priority - Feature Completion

### Not Started 📋
- [ ] Implement Stripe webhook handling
- [ ] Add scheduled Celery tasks for email processing
- [ ] Implement GDPR data export endpoint
- [ ] Complete notification service integration (Apprise)
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
- [ ] Create `frontend/src/lib/api.ts` — API client using axios
  - Must export: `authApi`, `mailAccountsApi`, `processingRunsApi`, `userApi`
  - Must export types: `User`, `MailAccount`, `MailAccountCreate`
  - 8 files import from `@/lib/api` and will fail to compile without it:
    `AuthGuard.tsx`, `AddMailAccountModal.tsx`, `authStore.ts`,
    `login/page.tsx`, `register/page.tsx`, `auth/callback/page.tsx`,
    `dashboard/page.tsx`, `accounts/page.tsx`

### Existing Pages (UI done, need API wiring) 🔨
- [x] Landing page (`app/page.tsx`)
- [x] Login page with email/password + Google OAuth
- [x] Registration page
- [x] OAuth callback handler
- [x] Dashboard with stats cards and processing runs table
- [x] Mail accounts list with CRUD operations
- [x] Settings page
- [x] `AddMailAccountModal` component (auto-detect, test connection)
- [x] `DashboardLayout` with responsive sidebar
- [x] `AuthGuard` for protected routes

### Not Started 📋
- [ ] End-to-end testing of frontend against backend API
- [ ] Error boundary components
- [ ] Loading skeletons / proper loading states
- [ ] Notification preferences UI
- [ ] Subscription management / billing UI

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
| Agentic Infrastructure | 95% | 🟢 Near Complete |
| Testing | 57% | 🟡 In Progress |
| CI/CD | 80% | 🟢 Near Complete |
| Code Quality | 40% | 🔴 Needs Work |
| Production Ready | 20% | 🔴 Needs Work |
| Observability | 10% | 🔴 Needs Work |
| Backend Features | 80% | 🟢 Near Complete |
| Frontend | 30% | 🔴 Blocked (missing lib/api.ts) |

**Overall Repository Readiness**: 52% ⚠️

---

## 🎯 Next Actions (Priority Order)

1. **Immediate** (Today):
   - [ ] Create `frontend/src/lib/api.ts` (frontend is broken without it)
   - [ ] Fix remaining security issues (bare excepts, datetime, redirect_uri)

2. **This Week**:
   - [ ] Enable rate limiting
   - [ ] Add audit logging
   - [ ] Write more unit tests (target 70% coverage)
   - [ ] Complete ADR documentation
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

**Last Updated**: 2026-03-23
**Maintained By**: Development Team
**Review Frequency**: Weekly
