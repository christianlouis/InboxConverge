# POP3 to Gmail Forwarder

[![CI Tests](https://github.com/christianlouis/pop_puller_to_gmail/actions/workflows/test.yml/badge.svg)](https://github.com/christianlouis/pop_puller_to_gmail/actions/workflows/test.yml)
[![Lint](https://github.com/christianlouis/pop_puller_to_gmail/actions/workflows/lint.yml/badge.svg)](https://github.com/christianlouis/pop_puller_to_gmail/actions/workflows/lint.yml)
[![Security Scan](https://github.com/christianlouis/pop_puller_to_gmail/actions/workflows/security.yml/badge.svg)](https://github.com/christianlouis/pop_puller_to_gmail/actions/workflows/security.yml)
[![Docker Build](https://github.com/christianlouis/pop_puller_to_gmail/actions/workflows/docker-build.yml/badge.svg)](https://github.com/christianlouis/pop_puller_to_gmail/actions/workflows/docker-build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

A Docker-based solution that automatically fetches emails from POP3 mailboxes and forwards them to Gmail, replacing Google's discontinued POP3 import feature.

## Features

- **Multiple POP3 Accounts** — support for unlimited POP3 mailboxes
- **Dual Delivery** — inject emails via **Gmail API** (preferred) or forward via **SMTP**
- **Hybrid Configuration** — configure via environment variables, `.env` files, **or** the database
- **Smart Throttling** — configurable rate limiting to stay within Gmail quotas
- **Error Reporting** — multi-channel notifications (Apprise: email, Telegram, Slack, Discord, webhooks)
- **Scheduled Polling** — configurable check intervals (default: every 5 minutes)
- **Docker Ready** — fully containerized with Docker Compose support
- **Secure** — runs as non-root user, SSL/TLS connections, encrypted credential storage

### SaaS Platform (in development)

The repository also includes a multi-tenant SaaS backend built with FastAPI, PostgreSQL, Redis, and Celery. It adds multi-user support, OAuth2 authentication, POP3/IMAP protocol support, encrypted credential storage, and background job processing. See the [SaaS README](docs/README_SAAS.md) for details.

## Quick Start

### Using a Pre-built Docker Image (Recommended)

```bash
# Pull and configure
curl -O https://raw.githubusercontent.com/christianlouis/pop_puller_to_gmail/main/docker-compose.yml
curl -o .env https://raw.githubusercontent.com/christianlouis/pop_puller_to_gmail/main/.env.example

# Edit .env with your credentials
nano .env

# Start
docker-compose up -d
```

### Building from Source

```bash
git clone https://github.com/christianlouis/pop_puller_to_gmail.git
cd pop_puller_to_gmail
cp .env.example .env   # then edit .env
docker-compose up -d
```

See the [Quick Start Guide](docs/QUICKSTART.md) for detailed instructions.

## Configuration

### Hybrid Configuration (Environment + Database)

The application supports a **hybrid configuration model**:

| Source | Priority | Use For |
|--------|----------|---------|
| **Database** (`app_settings` table) | Highest | SMTP, processing, Gmail API, notifications |
| **Environment variables / `.env`** | Fallback | All settings; required for bootstrap settings |
| **Built-in defaults** | Lowest | Sensible defaults for all non-bootstrap settings |

**Bootstrap settings** (`DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`) always come from environment variables because the database connection depends on them.

All other settings (SMTP, processing intervals, Gmail API, etc.) can be managed via the admin API at `/api/v1/settings` and are stored in the PostgreSQL database. When a database setting exists, it takes priority over the corresponding environment variable.

### POP3 Accounts

Add multiple POP3 accounts by incrementing the account number in your `.env`:

```bash
POP3_ACCOUNT_1_HOST=pop.provider1.com
POP3_ACCOUNT_1_USER=user1@provider1.com
POP3_ACCOUNT_1_PASSWORD=password1

POP3_ACCOUNT_2_HOST=pop.provider2.com
POP3_ACCOUNT_2_USER=user2@provider2.com
POP3_ACCOUNT_2_PASSWORD=password2
```

### Email Delivery Methods

The forwarder supports two delivery methods for getting emails into Gmail:

#### Gmail API Injection (Preferred)

Emails are injected directly into your Gmail account using Google's `users.messages.insert()` API. This is the **recommended method** because it:

- Preserves original email headers and metadata exactly as-is
- Does not modify `From`, `Reply-To`, or `Message-ID` headers
- Applies Gmail labels (e.g., `INBOX`) on injection
- Does not count against Gmail's SMTP sending quotas
- Does not require an SMTP App Password

**Setup:**

1. Configure Google OAuth2 credentials (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`)
2. Authenticate via the SaaS web UI or API (`POST /api/v1/providers/gmail-credential`)
3. Set `delivery_method` to `gmail_api` when creating mail accounts

**Required OAuth2 Scopes:**
- `https://www.googleapis.com/auth/gmail.insert`
- `https://www.googleapis.com/auth/gmail.labels`

#### SMTP Forwarding (Fallback)

Emails are forwarded to Gmail via SMTP. This is the legacy method and is used as a fallback when Gmail API credentials are not available.

**Limitations vs Gmail API:**
- Modifies email headers (adds `Received`, may rewrite `From`)
- Counts against Gmail's SMTP sending quota (500/day for free accounts)
- Requires a Gmail App Password (see below)
- May trigger spam filters for forwarded mail

**Setup:**

1. Go to your [Google Account Security](https://myaccount.google.com/security)
2. Under "Signing in to Google," select **App Passwords**
3. Generate a new app password for "Mail"
4. Set `SMTP_PASSWORD` in your environment or database settings

### Environment Variables

> **Note:** All settings marked ★ can also be managed via the database
> through the admin API (`/api/v1/settings`). Database values take precedence.

#### Bootstrap Settings (env only)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `SECRET_KEY` | Yes | — | JWT signing key (min 32 chars) |
| `ENCRYPTION_KEY` | Yes | — | Credential encryption key (min 32 chars) |

#### POP3/IMAP Accounts (env only — or via API)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POP3_ACCOUNT_N_HOST` | Yes | — | POP3 server hostname |
| `POP3_ACCOUNT_N_PORT` | No | `995` | POP3 server port |
| `POP3_ACCOUNT_N_USER` | Yes | — | POP3 username |
| `POP3_ACCOUNT_N_PASSWORD` | Yes | — | POP3 password |
| `POP3_ACCOUNT_N_USE_SSL` | No | `true` | Use SSL/TLS |

#### SMTP Settings ★

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SMTP_HOST` | No | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USER` | For SMTP | — | SMTP username |
| `SMTP_PASSWORD` | For SMTP | — | SMTP password (App Password) |
| `SMTP_USE_TLS` | No | `true` | Use STARTTLS |

#### Gmail API Settings ★

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_CLIENT_ID` | For Gmail API | — | Google OAuth2 client ID |
| `GOOGLE_CLIENT_SECRET` | For Gmail API | — | Google OAuth2 client secret |
| `GMAIL_API_ENABLED` | No | `true` | Enable Gmail API delivery |

#### Processing Settings ★

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHECK_INTERVAL_MINUTES` | No | `5` | Polling interval |
| `MAX_EMAILS_PER_RUN` | No | `50` | Max emails per account per run |
| `THROTTLE_EMAILS_PER_MINUTE` | No | `10` | Rate limit |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## How It Works

```
┌─────────────────┐
│  POP3 Server 1  │
└────────┬────────┘
         │ (Fetch emails)
         ▼
┌─────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  POP3 Server 2  │─────▶│    Forwarder     │─────▶│  Gmail API       │
└─────────────────┘      │    Container     │      │  (Preferred)     │
         │               │                  │      └──────────────────┘
┌────────▼────────┐      │  Config from:    │      ┌──────────────────┐
│  POP3 Server N  │      │  • Database      │─────▶│  Gmail SMTP      │
└─────────────────┘      │  • Environment   │      │  (Fallback)      │
                         └──────┬───────────┘      └──────────────────┘
                                │ (Notifications)
                                ▼
                      ┌─────────────────┐
                      │  Apprise        │
                      │  (Email, Slack, │
                      │   Telegram ...) │
                      └─────────────────┘
```

1. **Polling** — checks POP3/IMAP mailboxes at the configured interval
2. **Fetching** — retrieves new emails from each account
3. **Delivery** — injects into Gmail via API (preferred) or forwards via SMTP (fallback)
4. **Cleanup** — deletes from source after successful delivery
5. **Throttling** — respects rate limits to avoid quota issues
6. **Notifications** — sends alerts via Apprise (email, Telegram, Slack, Discord, webhooks)

## Development

```bash
# Install dependencies
make install-dev

# Run linting & formatting
make lint
make format

# Run tests
make test

# Start backend in dev mode
make run-dev
```

See the [Testing Guide](docs/TESTING_GUIDE.md) for the full test workflow.

## Documentation

Detailed documentation lives in the [`docs/`](docs/) directory:

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design and component overview |
| [Quick Start](docs/QUICKSTART.md) | Step-by-step setup guide |
| [Migration Guide](docs/MIGRATION_GUIDE.md) | Upgrading from v1 to v2 |
| [Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md) | Production deployment guide |
| [Roadmap](docs/ROADMAP.md) | Planned features and milestones |
| [Testing Guide](docs/TESTING_GUIDE.md) | How to run and write tests |
| [Coding Patterns](docs/CODING_PATTERNS.md) | Code style and conventions |
| [SaaS README](docs/README_SAAS.md) | Multi-tenant SaaS platform details |

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Reporting bugs and suggesting features
- Development setup and code style
- Pull request process

## Security

To report a vulnerability, please see [SECURITY.md](SECURITY.md). **Do not open public issues for security concerns.**

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

## Support

- [Issue Tracker](https://github.com/christianlouis/pop_puller_to_gmail/issues)
- [Discussions](https://github.com/christianlouis/pop_puller_to_gmail/discussions)
