# POP3 Forwarder SaaS - Multi-Tenant Architecture

This document describes the new multi-tenant SaaS architecture for the POP3/IMAP email forwarder.

## 🎯 Project Overview

The project has been transformed from a single-user Docker application into a full-featured multi-tenant SaaS platform with:

- **Multi-user support** with subscription tiers
- **Google OAuth2 authentication**
- **RESTful API** for all operations
- **Web dashboard** (frontend to be implemented)
- **Subscription management** with Stripe integration
- **POP3 and IMAP protocol support**
- **Auto-detection** of mail server settings
- **Encrypted credential storage**
- **Background job processing** with Celery
- **Multi-channel notifications** with Apprise

## 📁 Project Structure

```
pop_puller_to_gmail/
├── backend/                    # FastAPI backend application
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   │   └── v1/
│   │   │       ├── endpoints/ # Individual route modules
│   │   │       └── api.py     # Router aggregation
│   │   ├── core/              # Core configuration
│   │   │   ├── config.py      # Settings management
│   │   │   ├── database.py    # Database connection
│   │   │   ├── security.py    # Security utilities
│   │   │   └── deps.py        # FastAPI dependencies
│   │   ├── models/            # Data models
│   │   │   ├── database_models.py  # SQLAlchemy models
│   │   │   └── schemas.py     # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   │   ├── auth_service.py     # OAuth authentication
│   │   │   └── mail_processor.py   # Email processing
│   │   ├── workers/           # Celery background tasks
│   │   ├── utils/             # Utility functions
│   │   └── main.py            # FastAPI application
│   ├── alembic/               # Database migrations
│   ├── tests/                 # Test suite
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Docker configuration
│   └── .env.example          # Environment template
├── frontend/                  # React/Next.js frontend (to be implemented)
├── docker-compose.new.yml    # Docker Compose for all services
├── pop3_forwarder.py         # Legacy single-user script
└── README.md                 # This file
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- PostgreSQL 15+
- Redis 7+
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

### Setup

1. **Clone and navigate to repository**
   ```bash
   git clone https://github.com/christianlouis/pop_puller_to_gmail.git
   cd pop_puller_to_gmail
   ```

2. **Configure backend environment**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with your settings
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose -f docker-compose.new.yml up -d
   ```

4. **Run database migrations**
   ```bash
   docker-compose -f docker-compose.new.yml exec backend alembic upgrade head
   ```

5. **Access the application**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/api/docs
   - Frontend: http://localhost:3000 (when implemented)

## 🔑 Key Features

### 1. Multi-Tenant User Management

- **User Registration**: Email/password and Google OAuth2
- **Subscription Tiers**: Free, Basic, Pro, Enterprise
- **Account Limits**: Based on subscription tier
- **Secure Storage**: Encrypted credentials with Fernet encryption

### 2. Mail Account Management

- **Protocols**: POP3, POP3+SSL, IMAP, IMAP+SSL
- **Auto-Detection**: Automatic server configuration for common providers
- **Provider Presets**: Gmail, Outlook, GMX, WEB.de, T-Online, Yahoo
- **Connection Testing**: Test before saving
- **Per-Account Settings**: Check interval, max emails, forwarding destination

### 3. Email Processing

- **Background Jobs**: Celery workers for async processing
- **Scheduled Checks**: Configurable intervals per account
- **Smart Forwarding**: Preserves metadata, handles MIME types
- **Error Handling**: Automatic retries with exponential backoff
- **Statistics**: Track success/failure rates, last check times

### 4. Subscription Management

- **Stripe Integration**: Secure payment processing
- **Tier-Based Limits**: Automatic enforcement
- **Upgrade/Downgrade**: Self-service subscription changes
- **Webhook Handling**: Real-time subscription updates

### 5. Notifications

- **Multi-Channel**: Email, Telegram, Webhook, Slack, Discord
- **Apprise Integration**: 70+ notification services
- **Smart Alerting**: Threshold-based notifications
- **Per-User Configuration**: Custom notification preferences

### 6. Security

- **JWT Authentication**: Secure API access
- **Encrypted Credentials**: All POP3/IMAP passwords encrypted at rest
- **OAuth2**: Google Sign-In support
- **Audit Logging**: Complete audit trail
- **RBAC**: Role-based access control
- **Rate Limiting**: Per-user and per-tier limits

## 🗄️ Database Schema

### Core Tables

- **users**: User accounts, OAuth info, subscription data
- **mail_accounts**: POP3/IMAP account configurations
- **processing_runs**: Email processing batch records
- **processing_logs**: Detailed processing logs
- **notification_configs**: User notification settings
- **subscription_plans**: Available subscription tiers
- **mail_server_presets**: Known provider configurations
- **audit_logs**: Security and compliance audit trail

## 🔌 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login with email/password
- `POST /api/v1/auth/google` - Google OAuth2 login
- `GET /api/v1/auth/google/authorize-url` - Get OAuth URL

### Users
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update user profile

### Mail Accounts
- `POST /api/v1/mail-accounts` - Create mail account
- `GET /api/v1/mail-accounts` - List user's accounts
- `GET /api/v1/mail-accounts/{id}` - Get account details
- `PUT /api/v1/mail-accounts/{id}` - Update account
- `DELETE /api/v1/mail-accounts/{id}` - Delete account
- `POST /api/v1/mail-accounts/test` - Test connection
- `POST /api/v1/mail-accounts/auto-detect` - Auto-detect settings

### Notifications
- `POST /api/v1/notifications` - Create notification config
- `GET /api/v1/notifications` - List notification configs

### Subscriptions
- `GET /api/v1/subscriptions/plans` - List available plans
- `GET /api/v1/subscriptions/current` - Get current subscription

### Admin
- `GET /api/v1/admin/stats` - System statistics (admin only)

See full API documentation at `/api/docs` when running.

## 🔧 Configuration

### Environment Variables

Key configuration options in `backend/.env`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# Security
SECRET_KEY=your-secret-key-min-32-chars
ENCRYPTION_KEY=your-encryption-key

# OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Stripe (optional)
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Limits
TIER_FREE_MAX_ACCOUNTS=1
TIER_BASIC_MAX_ACCOUNTS=5
TIER_PRO_MAX_ACCOUNTS=20
TIER_ENTERPRISE_MAX_ACCOUNTS=100

# Processing
CHECK_INTERVAL_MINUTES=5
MAX_EMAILS_PER_RUN=50
THROTTLE_EMAILS_PER_MINUTE=10
```

### Subscription Tiers

| Tier | Max Accounts | Price | Features |
|------|--------------|-------|----------|
| Free | 1 | $0/mo | Basic email forwarding |
| Basic | 5 | $9/mo | Multiple accounts, Priority support |
| Pro | 20 | $29/mo | Advanced features, API access |
| Enterprise | 100 | $99/mo | White-label, SLA, Dedicated support |

## 🧪 Testing

```bash
# Run tests
cd backend
pytest

# With coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py
```

## 📦 Deployment

### Production Deployment

1. **Set production environment variables**
2. **Use production database** (PostgreSQL with backups)
3. **Configure Redis** for caching and job queue
4. **Set up SSL/TLS** with reverse proxy (nginx/traefik)
5. **Enable monitoring** (Prometheus, Grafana)
6. **Configure logging** (structured JSON logs)

### Kubernetes Deployment

Coming soon: Kubernetes manifests and Helm charts.

## 🔄 Migration from Legacy Version

To migrate from the single-user `pop3_forwarder.py`:

1. **Export existing configuration** from `.env` file
2. **Create user account** via API or admin panel
3. **Add mail accounts** using the API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/mail-accounts \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d @account.json
   ```
4. **Verify processing** in the dashboard
5. **Stop legacy container** once confirmed working

## 🛠️ Development

### Local Development Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run database
docker-compose -f docker-compose.new.yml up postgres redis -d

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000

# Frontend (to be implemented)
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 📚 Additional Documentation

- [API Documentation](http://localhost:8000/api/docs) - Interactive API docs
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [ROADMAP.md](ROADMAP.md) - Future development plans
- [SECURITY.md](SECURITY.md) - Security policies

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 🆘 Support

- **Issues**: https://github.com/christianlouis/pop_puller_to_gmail/issues
- **Discussions**: https://github.com/christianlouis/pop_puller_to_gmail/discussions
- **Email**: support@example.com

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [Celery](https://docs.celeryq.dev/) - Distributed task queue
- [Stripe](https://stripe.com/) - Payment processing
- [Apprise](https://github.com/caronc/apprise) - Notification service
- [React](https://react.dev/) - Frontend framework

---

**Status**: 🚧 Active Development - Phase 1 Complete

For questions or feedback, please open an issue on GitHub.
