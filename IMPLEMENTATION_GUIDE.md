# Implementation Guide

This guide provides step-by-step instructions for setting up and deploying the multi-tenant POP3 Forwarder SaaS application.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Setup](#development-setup)
3. [Production Deployment](#production-deployment)
4. [Configuration](#configuration)
5. [Database Setup](#database-setup)
6. [Google OAuth Setup](#google-oauth-setup)
7. [Stripe Integration](#stripe-integration)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Docker & Docker Compose**: v20.10 or higher
- **PostgreSQL**: v15 or higher (included in Docker Compose)
- **Redis**: v7 or higher (included in Docker Compose)
- **Python**: 3.11+ (for local development)
- **Node.js**: 18+ (for frontend development)

### Required Accounts

- **Google Cloud Console**: For OAuth2 authentication
- **Stripe Account**: For payment processing (optional for development)
- **Email SMTP Server**: For sending forwarded emails and notifications

## Development Setup

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/christianlouis/pop_puller_to_gmail.git
cd pop_puller_to_gmail

# Create backend environment file
cp backend/.env.example backend/.env
```

### 2. Configure Environment

Edit `backend/.env` with your settings:

```bash
# Minimum required for development
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/pop3_forwarder
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

### 3. Start Services

```bash
# Start all services
docker-compose -f docker-compose.new.yml up -d

# View logs
docker-compose -f docker-compose.new.yml logs -f
```

### 4. Initialize Database

```bash
# Run migrations
docker-compose -f docker-compose.new.yml exec backend alembic upgrade head

# Create admin user (optional)
docker-compose -f docker-compose.new.yml exec backend python -c "
from app.core.database import async_session_maker
from app.models.database_models import User, SubscriptionTier
from app.core.security import get_password_hash
import asyncio

async def create_admin():
    async with async_session_maker() as db:
        admin = User(
            email='admin@example.com',
            full_name='Admin User',
            hashed_password=get_password_hash('admin123'),
            subscription_tier=SubscriptionTier.ENTERPRISE,
            is_superuser=True,
            is_active=True
        )
        db.add(admin)
        await db.commit()
        print('Admin user created')

asyncio.run(create_admin())
"
```

### 5. Access Application

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health

### 6. Test API

```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "username=test@example.com&password=testpass123"

# Use returned token in subsequent requests
TOKEN="your-access-token"
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN"
```

## Production Deployment

### 1. Server Requirements

- **Minimum**: 2 vCPU, 4GB RAM, 40GB SSD
- **Recommended**: 4 vCPU, 8GB RAM, 100GB SSD
- **OS**: Ubuntu 22.04 LTS or similar

### 2. Security Configuration

```bash
# Generate secure keys
openssl rand -hex 32  # For SECRET_KEY
openssl rand -hex 32  # For ENCRYPTION_KEY

# Set strong database password
openssl rand -base64 32
```

### 3. Environment Configuration

```bash
# Production .env
DATABASE_URL=postgresql+asyncpg://produser:strongpass@db-host:5432/pop3_prod
SECRET_KEY=<generated-secret>
ENCRYPTION_KEY=<generated-encryption-key>
DEBUG=false
LOG_LEVEL=INFO

# OAuth
GOOGLE_CLIENT_ID=prod-client-id
GOOGLE_CLIENT_SECRET=prod-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/callback/google

# Stripe
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# CORS
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Email (for notifications and admin)
ADMIN_EMAIL=admin@yourdomain.com
```

### 4. SSL/TLS Setup

Use nginx or Traefik as reverse proxy:

```nginx
# /etc/nginx/sites-available/pop3-forwarder
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. Database Backup

```bash
# Automated daily backup
cat > /etc/cron.daily/backup-postgres << 'EOF'
#!/bin/bash
BACKUP_DIR=/var/backups/postgres
DATE=$(date +%Y%m%d_%H%M%S)
docker exec pop3-postgres pg_dump -U postgres pop3_forwarder | gzip > $BACKUP_DIR/backup_$DATE.sql.gz
find $BACKUP_DIR -type f -mtime +7 -delete  # Keep 7 days
EOF

chmod +x /etc/cron.daily/backup-postgres
```

### 6. Monitoring

```bash
# Docker healthchecks
docker-compose -f docker-compose.new.yml ps

# Application logs
docker-compose -f docker-compose.new.yml logs -f backend

# Celery worker status
docker-compose -f docker-compose.new.yml exec celery-worker celery -A app.workers.celery_app inspect active
```

## Database Setup

### Running Migrations

```bash
# Check current migration status
docker-compose -f docker-compose.new.yml exec backend alembic current

# Upgrade to latest
docker-compose -f docker-compose.new.yml exec backend alembic upgrade head

# Downgrade one version
docker-compose -f docker-compose.new.yml exec backend alembic downgrade -1

# View migration history
docker-compose -f docker-compose.new.yml exec backend alembic history
```

### Creating Migrations

```bash
# Auto-generate migration from model changes
docker-compose -f docker-compose.new.yml exec backend alembic revision --autogenerate -m "Description of changes"

# Create empty migration
docker-compose -f docker-compose.new.yml exec backend alembic revision -m "Manual migration"
```

## Google OAuth Setup

### 1. Create OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create or select a project
3. Enable "Google+ API"
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Application type: "Web application"
6. Authorized redirect URIs:
   - Development: `http://localhost:3000/auth/callback/google`
   - Production: `https://yourdomain.com/auth/callback/google`

### 2. Configure Application

Add to `backend/.env`:

```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/callback/google
```

### 3. Test OAuth Flow

```bash
# Get authorization URL
curl http://localhost:8000/api/v1/auth/google/authorize-url?redirect_uri=http://localhost:3000/auth/callback/google

# After user authorization, exchange code for tokens
curl -X POST http://localhost:8000/api/v1/auth/google \
  -H "Content-Type: application/json" \
  -d '{
    "code": "authorization-code-from-google",
    "redirect_uri": "http://localhost:3000/auth/callback/google"
  }'
```

## Stripe Integration

### 1. Setup Stripe Account

1. Create account at [stripe.com](https://stripe.com)
2. Get API keys from Dashboard → Developers → API keys
3. Set up webhook endpoint

### 2. Configure Webhook

1. Dashboard → Developers → Webhooks → Add endpoint
2. Endpoint URL: `https://yourdomain.com/api/v1/webhooks/stripe`
3. Select events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`

### 3. Add to Environment

```bash
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
```

### 4. Create Products and Prices

Use Stripe Dashboard or API to create subscription products for each tier.

## Monitoring

### Application Metrics

```bash
# Prometheus metrics endpoint (to be implemented)
curl http://localhost:8000/metrics

# Health check
curl http://localhost:8000/health
```

### Celery Monitoring

```bash
# Check worker status
docker-compose -f docker-compose.new.yml exec celery-worker celery -A app.workers.celery_app inspect stats

# Check scheduled tasks
docker-compose -f docker-compose.new.yml exec celery-beat celery -A app.workers.celery_app inspect scheduled

# Monitor tasks in real-time
docker-compose -f docker-compose.new.yml exec celery-worker celery -A app.workers.celery_app events
```

### Database Monitoring

```bash
# Check connections
docker exec pop3-postgres psql -U postgres -d pop3_forwarder -c "SELECT count(*) FROM pg_stat_activity;"

# Check table sizes
docker exec pop3-postgres psql -U postgres -d pop3_forwarder -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

## Troubleshooting

### Common Issues

#### Database Connection Errors

```bash
# Check database is running
docker-compose -f docker-compose.new.yml ps postgres

# Check database logs
docker-compose -f docker-compose.new.yml logs postgres

# Test connection
docker exec pop3-postgres psql -U postgres -c "SELECT version();"
```

#### Celery Worker Not Processing

```bash
# Check worker logs
docker-compose -f docker-compose.new.yml logs celery-worker

# Restart worker
docker-compose -f docker-compose.new.yml restart celery-worker

# Check Redis connection
docker-compose -f docker-compose.new.yml exec redis redis-cli ping
```

#### OAuth Authentication Failing

```bash
# Verify environment variables
docker-compose -f docker-compose.new.yml exec backend printenv | grep GOOGLE

# Check redirect URI matches exactly
# Common issue: http vs https, trailing slash
```

#### Email Processing Errors

```bash
# Check mail account configuration
curl -X GET http://localhost:8000/api/v1/mail-accounts \
  -H "Authorization: Bearer $TOKEN"

# Test connection
curl -X POST http://localhost:8000/api/v1/mail-accounts/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "host": "pop.gmail.com",
    "port": 995,
    "protocol": "pop3_ssl",
    "username": "user@gmail.com",
    "password": "app-password",
    "use_ssl": true
  }'
```

### Debug Mode

Enable debug logging:

```bash
# In .env
LOG_LEVEL=DEBUG
DEBUG=true

# Restart services
docker-compose -f docker-compose.new.yml restart
```

### Reset Database

```bash
# ⚠️ WARNING: This deletes all data
docker-compose -f docker-compose.new.yml down -v
docker-compose -f docker-compose.new.yml up -d postgres redis
sleep 5
docker-compose -f docker-compose.new.yml exec backend alembic upgrade head
```

## Performance Tuning

### Database Optimization

```sql
-- Add indexes for frequently queried fields
CREATE INDEX idx_mail_accounts_user_enabled ON mail_accounts(user_id, is_enabled);
CREATE INDEX idx_processing_runs_account_date ON processing_runs(mail_account_id, started_at DESC);
```

### Celery Optimization

```python
# In celery_app.py
celery_app.conf.update(
    worker_prefetch_multiplier=4,  # Increase for better throughput
    worker_max_tasks_per_child=100,  # Restart workers periodically
    task_acks_late=True,  # Only ack after completion
)
```

### Redis Optimization

```bash
# In docker-compose.new.yml
redis:
  command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

## Support

For additional help:

- **Documentation**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Issues**: https://github.com/christianlouis/pop_puller_to_gmail/issues
- **Discussions**: https://github.com/christianlouis/pop_puller_to_gmail/discussions

---

Last Updated: 2026-02-01
