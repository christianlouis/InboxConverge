# InboxConverge

[![CI](https://github.com/christianlouis/InboxConverge/actions/workflows/ci.yml/badge.svg)](https://github.com/christianlouis/InboxConverge/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/christianlouis/InboxConverge?sort=semver&label=release)](https://github.com/christianlouis/InboxConverge/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**Google is removing "Check mail from other accounts" (POP) and Gmailify in 2026. InboxConverge is the self-hosted replacement.**

Gmail's built-in POP fetcher and Gmailify are being shut down imminently. Google's suggested alternatives — asking your old provider to configure outbound forwarding, or reading mail in the Gmail mobile app over IMAP — don't replicate the seamless, automatic consolidation you had. InboxConverge does: it polls your POP3/IMAP mailboxes on a schedule and injects new messages directly into your Gmail inbox, exactly like the old feature, running on your own infrastructure.

> **Google's own announcement:** *"Gmail no longer supports fetching email from third-party accounts via POP. The 'Check mail from other accounts' option is no longer available in Gmail."*
>
> InboxConverge puts that option back — permanently, on your own terms.

## Who this is for

- You used Gmail's "Check mail from other accounts" and it's going away
- You have one or more external mailboxes (work, old ISP, custom domain) that you want consolidated into Gmail automatically
- You don't want to rely on your old provider supporting outbound forwarding
- You want email delivered cleanly into Gmail without headers being mangled or spam filters misfiring

## What you get

| | Google POP Import (shutting down 2026) | InboxConverge |
|---|---|---|
| Still works? | ❌ Shutting down 2026 | ✅ |
| Multiple source accounts | Limited | ✅ Unlimited |
| Automatic, scheduled polling | ✅ | ✅ Every 5 min (configurable) |
| Original headers preserved | ❌ | ✅ Via Gmail API injection |
| Counts against sending quota | ❌ N/A | ✅ No (Gmail API) / ⚠️ Yes (SMTP) |
| Alerts when something breaks | ❌ | ✅ Email, Slack, Telegram, Discord… |
| Self-hosted, no third-party dependency | ❌ | ✅ Docker, runs anywhere |
| Open source | ❌ | ✅ MIT |

## Get started in 5 minutes

```bash
# 1. Grab the config files
curl -O https://raw.githubusercontent.com/christianlouis/InboxConverge/main/docker-compose.yml
curl -o .env https://raw.githubusercontent.com/christianlouis/InboxConverge/main/.env.example

# 2. Fill in your credentials
nano .env

# 3. Launch
docker-compose up -d
```

Minimum `.env` to get going:

```dotenv
# Source mailbox — add _2_, _3_, … for additional accounts
POP3_ACCOUNT_1_HOST=pop.yourprovider.com
POP3_ACCOUNT_1_USER=you@yourprovider.com
POP3_ACCOUNT_1_PASSWORD=your-pop3-password

# Destination — Gmail App Password (quickest way to start)
SMTP_USER=you@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# Required internal secrets (generate once, keep private)
SECRET_KEY=<python -c 'import secrets; print(secrets.token_urlsafe(32))'>
ENCRYPTION_KEY=<python -c 'import secrets; print(secrets.token_urlsafe(32))'>
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/inboxconverge
```

See the [Quick Start Guide](docs/QUICKSTART.md) for a full walkthrough, including the recommended Gmail API setup which preserves headers and avoids sending-quota limits.

## Two ways to deliver mail into Gmail

**Gmail API injection (recommended)** — messages land in your inbox with original `From`, `Reply-To`, and `Message-ID` intact, don't count against your sending quota, and bypass the spam-filter penalties that forwarded mail often triggers. Requires a one-time Google OAuth2 authorisation.

**SMTP with App Password (zero-setup fallback)** — works immediately with a [Gmail App Password](https://myaccount.google.com/apppasswords). Forwarded messages may be re-wrapped and count toward your 500-message/day free-tier limit. Good for getting started quickly; upgrade to the API later.

## Key settings

| Variable | Default | What it does |
|---|---|---|
| `CHECK_INTERVAL_MINUTES` | `5` | How often mailboxes are polled |
| `MAX_EMAILS_PER_RUN` | `50` | Maximum messages fetched per account per run |
| `THROTTLE_EMAILS_PER_MINUTE` | `10` | Rate cap toward Gmail |

All settings except the three bootstrap secrets can be changed at runtime in the admin web UI — no restart needed.

## Documentation

| | |
|---|---|
| [Quick Start](docs/QUICKSTART.md) | Step-by-step setup, Gmail API & SMTP |
| [Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md) | Production hardening guide |
| [Architecture](docs/ARCHITECTURE.md) | How the pieces fit together |
| [Migration Guide](docs/MIGRATION_GUIDE.md) | Upgrading from an older version |
| [Roadmap](docs/ROADMAP.md) | What's coming next |

## Contributing

Bug reports, feature requests, and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

Please report vulnerabilities privately via [SECURITY.md](SECURITY.md) rather than opening a public issue.

## License

MIT — see [LICENSE](LICENSE).
