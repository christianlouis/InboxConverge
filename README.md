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

- **Multiple POP3 Accounts** — support for unlimited POP3 mailboxes via environment variables
- **Automatic Forwarding** — sends emails to your Gmail account via SMTP
- **Smart Throttling** — configurable rate limiting to stay within Gmail quotas
- **Error Reporting** — notifications via Postmarkapp when issues occur
- **Scheduled Polling** — configurable check intervals (default: every 5 minutes)
- **Docker Ready** — fully containerized with Docker Compose support
- **Secure** — runs as non-root user, SSL/TLS connections

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

### Gmail App Password

1. Go to your [Google Account Security](https://myaccount.google.com/security)
2. Under "Signing in to Google," select **App Passwords**
3. Generate a new app password for "Mail"
4. Use this password as `SMTP_PASSWORD`

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POP3_ACCOUNT_N_HOST` | Yes | — | POP3 server hostname |
| `POP3_ACCOUNT_N_PORT` | No | `995` | POP3 server port |
| `POP3_ACCOUNT_N_USER` | Yes | — | POP3 username |
| `POP3_ACCOUNT_N_PASSWORD` | Yes | — | POP3 password |
| `POP3_ACCOUNT_N_USE_SSL` | No | `true` | Use SSL/TLS |
| `SMTP_HOST` | No | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USER` | Yes | — | SMTP username |
| `SMTP_PASSWORD` | Yes | — | SMTP password (App Password) |
| `SMTP_USE_TLS` | No | `true` | Use STARTTLS |
| `GMAIL_DESTINATION` | Yes | — | Destination Gmail address |
| `CHECK_INTERVAL_MINUTES` | No | `5` | Polling interval |
| `MAX_EMAILS_PER_RUN` | No | `50` | Max emails per account per run |
| `THROTTLE_EMAILS_PER_MINUTE` | No | `10` | Rate limit |
| `POSTMARK_API_TOKEN` | No | — | Postmarkapp API token |
| `POSTMARK_FROM_EMAIL` | No | — | Error notification sender |
| `POSTMARK_TO_EMAIL` | No | — | Error notification recipient |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## How It Works

```
┌─────────────────┐
│  POP3 Server 1  │
└────────┬────────┘
         │ (Fetch emails)
         ▼
┌─────────────────┐      ┌──────────────┐      ┌─────────────┐
│  POP3 Server 2  │─────▶│  Forwarder   │─────▶│    Gmail    │
└─────────────────┘      │  Container   │      │   (SMTP)    │
         │               └──────┬───────┘      └─────────────┘
┌────────▼────────┐             │ (Error notifications)
│  POP3 Server N  │             ▼
└─────────────────┘   ┌─────────────────┐
                      │   Postmarkapp   │
                      └─────────────────┘
```

1. **Polling** — checks POP3 mailboxes at the configured interval
2. **Fetching** — retrieves new emails from each account
3. **Forwarding** — delivers to Gmail with original metadata preserved
4. **Cleanup** — deletes from POP3 after successful forwarding
5. **Throttling** — respects rate limits to avoid quota issues
6. **Error Handling** — sends notifications if something goes wrong

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
