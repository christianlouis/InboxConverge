# POP3/IMAP to Gmail Forwarder - Multi-Tenant SaaS 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

A production-ready multi-tenant SaaS application for forwarding emails from POP3/IMAP mailboxes to Gmail, replacing Google's discontinued POP3 import feature.

## 🎯 What's New in v2.0

This project has been **completely transformed** from a single-user Docker script into a full-featured multi-tenant SaaS platform:

### ✨ Key Features

- **🔐 Multi-User Support**: Each user has their own isolated accounts and settings
- **🌐 RESTful API**: Complete REST API with OpenAPI/Swagger documentation
- **🔑 Authentication**: Email/password + Google OAuth2 integration
- **💳 Subscription Tiers**: Free, Basic, Pro, and Enterprise plans
- **📧 Protocol Support**: POP3, POP3+SSL, IMAP, IMAP+SSL
- **🔍 Auto-Detection**: Automatic mail server configuration for 7+ providers
- **🔒 Encrypted Storage**: All credentials encrypted at rest
- **⚡ Background Processing**: Celery workers for async email processing
- **📊 Statistics & Monitoring**: Per-account tracking and error logging
- **🔔 Multi-Channel Notifications**: Apprise integration for 70+ services
- **🐳 Docker-Ready**: Complete multi-container orchestration

## 📚 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and technical details
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Setup and deployment guide
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Migrating from v1.0 to v2.0
- **[FEATURE_SUMMARY.md](FEATURE_SUMMARY.md)** - Complete feature list and roadmap
- **[ROADMAP.md](ROADMAP.md)** - Future development plans

## 🚀 Quick Start

### For New Users (v2.0 Multi-Tenant)

```bash
# Clone repository
git clone https://github.com/christianlouis/pop_puller_to_gmail.git
cd pop_puller_to_gmail

# Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your settings

# Start all services
docker-compose -f docker-compose.new.yml up -d

# Run database migrations
docker-compose -f docker-compose.new.yml exec backend alembic upgrade head

# Access API documentation
open http://localhost:8000/api/docs
```

### For Existing Users (Legacy v1.0)

If you're currently using the single-user version, see **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** for step-by-step migration instructions.

## 📖 User Guide

### 1. Register an Account

**Via API:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "secure-password",
    "full_name": "Your Name"
  }'
```

**Via Google OAuth:** (Recommended)
```bash
# Get authorization URL
curl "http://localhost:8000/api/v1/auth/google/authorize-url?redirect_uri=http://localhost:3000/callback"
# Follow the URL, authorize, then exchange code for tokens
```

### 2. Add Mail Accounts

```bash
# Login to get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=you@example.com&password=secure-password"

# Add a mail account
curl -X POST http://localhost:8000/api/v1/mail-accounts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Old Email",
    "email_address": "old@provider.com",
    "protocol": "pop3_ssl",
    "host": "pop.provider.com",
    "port": 995,
    "username": "old@provider.com",
    "password": "email-password",
    "forward_to": "you@gmail.com",
    "is_enabled": true
  }'
```

### 3. Auto-Detect Settings

```bash
# Get suggested settings for your email
curl -X POST http://localhost:8000/api/v1/mail-accounts/auto-detect \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email_address": "you@gmail.com"}'
```

### 4. Monitor Processing

```bash
# List your accounts
curl -X GET http://localhost:8000/api/v1/mail-accounts \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check logs
docker-compose -f docker-compose.new.yml logs -f celery-worker
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│            (React/Next.js - Planned)             │
└────────────────────┬────────────────────────────┘
                     │ HTTPS/REST API
                     ▼
┌─────────────────────────────────────────────────┐
│              FastAPI Backend (Port 8000)         │
│                                                  │
│  • Authentication (JWT + OAuth2)                 │
│  • User Management                               │
│  • Mail Account CRUD                            │
│  • Statistics & Monitoring                       │
└────────────────────┬────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │  Celery Workers │
│   (Database)    │    │  + Beat         │
│                 │    │                 │
│  • Users        │    │  • Fetch emails │
│  • Accounts     │    │  • Forward      │
│  • Logs         │    │  • Notify       │
└─────────────────┘    └────────┬────────┘
                               │
                               ▼
                      ┌─────────────────┐
                      │     Redis       │
                      │  (Queue/Cache)  │
                      └─────────────────┘
```

## 💰 Subscription Tiers

| Feature | Free | Basic | Pro | Enterprise |
|---------|------|-------|-----|------------|
| **Price** | $0/mo | $9/mo | $29/mo | $99/mo |
| **Mail Accounts** | 1 | 5 | 20 | 100 |
| **Check Interval** | 5 min | 5 min | 1 min | Custom |
| **Support** | Community | Email | Priority | Dedicated |
| **API Access** | ✅ | ✅ | ✅ | ✅ |
| **Auto-Detection** | ✅ | ✅ | ✅ | ✅ |
| **Notifications** | ❌ | ✅ | ✅ | ✅ |
| **Custom Rules** | ❌ | ❌ | ✅ | ✅ |
| **White-Label** | ❌ | ❌ | ❌ | ✅ |

## 🔒 Security Features

- **Encrypted Credentials**: Fernet encryption for all POP3/IMAP passwords
- **JWT Authentication**: Secure API access with refresh tokens
- **OAuth2**: Google Sign-In integration
- **Password Hashing**: Bcrypt for user passwords
- **Audit Logging**: Complete security audit trail
- **CORS Protection**: Configurable allowed origins
- **SQL Injection Protection**: SQLAlchemy ORM
- **Rate Limiting**: Per-user and per-tier limits (planned)

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 15 + SQLAlchemy 2.0
- **Task Queue**: Celery + Redis
- **Authentication**: JWT + OAuth2
- **Containerization**: Docker + Docker Compose
- **Frontend**: React/Next.js (planned)
- **Monitoring**: Prometheus + Grafana (planned)

## 📊 Supported Email Providers

### Pre-configured Auto-Detection

- ✅ Gmail (pop.gmail.com / imap.gmail.com)
- ✅ Outlook/Hotmail (outlook.office365.com)
- ✅ GMX (pop.gmx.com / imap.gmx.com)
- ✅ WEB.de (pop3.web.de / imap.web.de)
- ✅ T-Online (pop.t-online.de / imap.t-online.de)
- ✅ Yahoo (pop.mail.yahoo.com / imap.mail.yahoo.com)
- ✅ Generic patterns for unknown providers

### Adding Custom Providers

You can manually configure any POP3 or IMAP server by specifying host, port, and protocol.

## 🔧 Configuration

### Environment Variables

Key settings in `backend/.env`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# Security (Generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-minimum-32-characters
ENCRYPTION_KEY=your-encryption-key-for-credentials

# OAuth (Get from Google Cloud Console)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Stripe (Optional for monetization)
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Application
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
DEBUG=false
LOG_LEVEL=INFO
```

See `backend/.env.example` for all options.

## 🧪 Development

### Local Development Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start database & Redis
docker-compose -f docker-compose.new.yml up -d postgres redis

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000
```

### Running Tests

```bash
# Unit tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Integration tests
pytest tests/integration/
```

### Creating Database Migrations

```bash
# Auto-generate migration
alembic revision --autogenerate -m "Add new field"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## 📦 Deployment

### Docker Compose (Recommended)

```bash
# Production deployment
docker-compose -f docker-compose.new.yml up -d

# View logs
docker-compose -f docker-compose.new.yml logs -f

# Scale workers
docker-compose -f docker-compose.new.yml up -d --scale celery-worker=3
```

### Kubernetes (Coming Soon)

Helm charts and Kubernetes manifests will be provided for production deployment.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

### Areas for Contribution

1. **Frontend Development**: React/Next.js dashboard
2. **Stripe Integration**: Payment processing implementation
3. **Notification System**: Apprise integration
4. **Email Improvements**: DMARC/SPF handling, HTML emails
5. **Testing**: Unit and integration tests
6. **Documentation**: Tutorials, examples, translations

## 📜 License

MIT License - See [LICENSE](../LICENSE) file for details.

## 🆘 Support

- **Documentation**: See docs in repository
- **Issues**: https://github.com/christianlouis/pop_puller_to_gmail/issues
- **Discussions**: https://github.com/christianlouis/pop_puller_to_gmail/discussions
- **Email**: support@example.com (for Enterprise customers)

## 🎉 Acknowledgments

Built with these amazing open-source projects:

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [Celery](https://docs.celeryq.dev/) - Distributed task queue
- [PostgreSQL](https://www.postgresql.org/) - Relational database
- [Redis](https://redis.io/) - In-memory data store
- [Stripe](https://stripe.com/) - Payment processing
- [Apprise](https://github.com/caronc/apprise) - Notification library

## 📈 Project Status

| Phase | Status | Progress |
|-------|--------|----------|
| Backend API | ✅ Complete | 100% |
| Database Models | ✅ Complete | 100% |
| Authentication | ✅ Complete | 100% |
| Email Processing | ✅ Complete | 100% |
| Background Jobs | ✅ Complete | 100% |
| Documentation | ✅ Complete | 100% |
| Stripe Integration | 🚧 In Progress | 60% |
| Frontend Dashboard | 🚧 In Progress | 70% |
| Notification System | 🚧 In Progress | 40% |
| Testing Suite | 🚧 In Progress | 30% |

> **Note:** The frontend pages and components are implemented but the API client
> layer (`lib/api.ts`) is not yet wired up, so the dashboard does not function
> end-to-end yet.

## 🔮 Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed future plans, including:

- Complete web dashboard
- Advanced email filtering
- Email archiving
- Multi-destination forwarding
- White-label support
- Kubernetes deployment
- High availability setup

---

**Status**: In Development | **Backend**: Production-ready | **Frontend**: In Progress
