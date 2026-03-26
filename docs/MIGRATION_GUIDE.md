# Migration Guide: Single-User to Multi-Tenant SaaS

This guide helps you migrate from the legacy single-user `inbox_converge.py` script to the new multi-tenant SaaS application.

## Overview

The migration involves:
1. Understanding the architectural changes
2. Exporting existing configuration
3. Setting up the new system
4. Importing mail accounts
5. Verifying functionality
6. Decommissioning the old system

## Architectural Changes

### Before (Legacy)
- Single Docker container
- Environment variable configuration
- Direct POP3 fetching and SMTP forwarding
- No user accounts or authentication
- Limited to one Gmail destination

### After (New System)
- Multi-container architecture (API, workers, database)
- Database-backed configuration
- User accounts with authentication
- Multiple users with separate configurations
- Web dashboard and API access
- Subscription tiers and limits

## Prerequisites

- Access to existing `.env` file
- Docker and Docker Compose installed
- Basic understanding of REST APIs
- Access to Google Cloud Console (for OAuth)

## Step-by-Step Migration

### Step 1: Backup Existing Configuration

```bash
# Save your existing .env file
cp .env .env.legacy.backup

# Document your mail accounts
cat .env | grep POP3_ACCOUNT
```

### Step 2: Set Up New System

```bash
# Pull latest changes
git pull origin main

# Create new environment file
cp backend/.env.example backend/.env

# Generate secure keys
echo "SECRET_KEY=$(openssl rand -hex 32)" >> backend/.env
echo "ENCRYPTION_KEY=$(openssl rand -hex 32)" >> backend/.env
```

### Step 3: Start New Services

```bash
# Start all services
docker-compose -f docker-compose.new.yml up -d

# Wait for services to be ready
sleep 10

# Run database migrations
docker-compose -f docker-compose.new.yml exec backend alembic upgrade head
```

### Step 4: Create Your User Account

**Option A: Via API**

```bash
# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-secure-password",
    "full_name": "Your Name"
  }'

# Login to get access token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "username=your-email@example.com&password=your-secure-password"

# Save the access_token from response
export TOKEN="your-access-token-here"
```

**Option B: Via Google OAuth**

1. Set up Google OAuth credentials (see IMPLEMENTATION_GUIDE.md)
2. Use the web interface or OAuth flow to register

### Step 5: Import Mail Accounts

Create a migration script to import your existing accounts:

```bash
# Create migration script
cat > migrate_accounts.sh << 'EOF'
#!/bin/bash

TOKEN="your-access-token"
API_URL="http://localhost:8000/api/v1"

# Function to add a mail account
add_account() {
    local name=$1
    local host=$2
    local port=$3
    local user=$4
    local pass=$5
    local forward_to=$6
    
    curl -X POST "$API_URL/mail-accounts" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"name\": \"$name\",
        \"email_address\": \"$user\",
        \"protocol\": \"pop3_ssl\",
        \"host\": \"$host\",
        \"port\": $port,
        \"use_ssl\": true,
        \"use_tls\": false,
        \"username\": \"$user\",
        \"password\": \"$pass\",
        \"forward_to\": \"$forward_to\",
        \"is_enabled\": true,
        \"check_interval_minutes\": 5,
        \"max_emails_per_check\": 50,
        \"delete_after_forward\": true
      }"
    
    echo ""
}

# Import accounts from old .env
# Account 1
add_account \
    "My Email Account" \
    "$POP3_ACCOUNT_1_HOST" \
    "$POP3_ACCOUNT_1_PORT" \
    "$POP3_ACCOUNT_1_USER" \
    "$POP3_ACCOUNT_1_PASSWORD" \
    "$GMAIL_DESTINATION"

# Account 2 (if exists)
if [ -n "$POP3_ACCOUNT_2_HOST" ]; then
    add_account \
        "Second Account" \
        "$POP3_ACCOUNT_2_HOST" \
        "$POP3_ACCOUNT_2_PORT" \
        "$POP3_ACCOUNT_2_USER" \
        "$POP3_ACCOUNT_2_PASSWORD" \
        "$GMAIL_DESTINATION"
fi

# Add more accounts as needed...

EOF

chmod +x migrate_accounts.sh

# Source old environment and run migration
source .env.legacy.backup
./migrate_accounts.sh
```

### Step 6: Verify Configuration

```bash
# List imported accounts
curl -X GET http://localhost:8000/api/v1/mail-accounts \
  -H "Authorization: Bearer $TOKEN" | jq .

# Test connection for first account
curl -X POST http://localhost:8000/api/v1/mail-accounts/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @test_connection.json
```

### Step 7: Monitor Processing

```bash
# Check Celery worker logs
docker-compose -f docker-compose.new.yml logs -f celery-worker

# Watch for processing runs
watch -n 5 'curl -s -X GET http://localhost:8000/api/v1/mail-accounts \
  -H "Authorization: Bearer $TOKEN" | jq ".[].last_check_at"'
```

### Step 8: Parallel Testing (Recommended)

Run both systems in parallel for a few days:

```bash
# Keep old system running
docker-compose -f docker-compose.yml ps

# Run new system on different ports
# Edit docker-compose.new.yml to use port 8001 if needed

# Compare logs and results
diff <(docker-compose -f docker-compose.yml logs) \
     <(docker-compose -f docker-compose.new.yml logs)
```

### Step 9: Decommission Old System

Once confident the new system works:

```bash
# Stop old container
docker-compose -f docker-compose.yml down

# Archive old configuration
mkdir -p archive
mv inbox_converge.py archive/
mv .env.legacy.backup archive/
mv docker-compose.yml archive/docker-compose.legacy.yml

# Update main docker-compose
mv docker-compose.new.yml docker-compose.yml
```

## Multi-User Migration

If migrating for multiple users (e.g., family members):

### For Your Wife's Account

```bash
# She needs to register her own account
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "wife@example.com",
    "password": "her-secure-password",
    "full_name": "Wife Name"
  }'

# She logs in to get her token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "username=wife@example.com&password=her-secure-password"

WIFE_TOKEN="her-access-token"

# Add her mail accounts using her token
curl -X POST http://localhost:8000/api/v1/mail-accounts \
  -H "Authorization: Bearer $WIFE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wife Email",
    "email_address": "wife@provider.com",
    "protocol": "pop3_ssl",
    "host": "pop.provider.com",
    "port": 995,
    "use_ssl": true,
    "username": "wife@provider.com",
    "password": "her-email-password",
    "forward_to": "wife@gmail.com",
    "is_enabled": true
  }'
```

## Configuration Mapping

### Environment Variables to Database

| Legacy (`.env`) | New System (Database) |
|----------------|----------------------|
| `POP3_ACCOUNT_N_*` | `mail_accounts` table per user |
| `GMAIL_DESTINATION` | `forward_to` field in `mail_accounts` |
| `CHECK_INTERVAL_MINUTES` | Per-account `check_interval_minutes` |
| `MAX_EMAILS_PER_RUN` | Per-account `max_emails_per_check` |
| `SMTP_USER` / `SMTP_PASSWORD` | To be configured per user or globally |

### Feature Mapping

| Legacy Feature | New Feature | Notes |
|---------------|-------------|-------|
| Multiple POP3 accounts | Mail Accounts API | Per-user, unlimited (based on tier) |
| Single Gmail destination | Per-account forwarding | Each account can forward to different address |
| Fixed check interval | Configurable per account | More flexibility |
| Postmark notifications | Apprise notifications | More channels (Telegram, Slack, etc.) |
| Environment config | Database + Web UI | Easier management |
| No authentication | JWT + OAuth2 | Secure multi-user access |
| No user limits | Subscription tiers | Free: 1, Basic: 5, Pro: 20, Enterprise: 100 |

## Troubleshooting Migration

### Issue: Cannot connect to database

```bash
# Check database is running
docker-compose -f docker-compose.new.yml ps postgres

# Check connection
docker-compose -f docker-compose.new.yml exec postgres psql -U postgres -c "SELECT 1;"
```

### Issue: Migrations fail

```bash
# Reset database (⚠️ deletes all data)
docker-compose -f docker-compose.new.yml down -v
docker-compose -f docker-compose.new.yml up -d postgres
sleep 5
docker-compose -f docker-compose.new.yml exec backend alembic upgrade head
```

### Issue: Emails not being processed

```bash
# Check Celery worker
docker-compose -f docker-compose.new.yml logs celery-worker

# Manually trigger processing
curl -X POST http://localhost:8000/api/v1/admin/trigger-processing \
  -H "Authorization: Bearer $TOKEN"
```

### Issue: Authentication fails

```bash
# Verify token is valid
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN"

# If expired, login again
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "username=your-email&password=your-password"
```

## Rollback Plan

If you need to rollback to the old system:

```bash
# Stop new system
docker-compose -f docker-compose.new.yml down

# Restore old configuration
cp archive/.env.legacy.backup .env
cp archive/docker-compose.legacy.yml docker-compose.yml

# Start old system
docker-compose up -d

# Verify it's working
docker-compose logs -f
```

## Post-Migration Checklist

- [ ] All mail accounts imported and tested
- [ ] Email processing verified
- [ ] Notifications configured
- [ ] Old system stopped and archived
- [ ] Documentation updated
- [ ] Users trained on new interface
- [ ] Monitoring set up
- [ ] Backups configured
- [ ] SSL/TLS certificates installed (for production)
- [ ] OAuth credentials configured

## Getting Help

If you encounter issues during migration:

1. Check logs: `docker-compose -f docker-compose.new.yml logs`
2. Review [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)
3. Check [ARCHITECTURE.md](ARCHITECTURE.md) for system overview
4. Open an issue on GitHub with:
   - Error messages
   - Steps to reproduce
   - Configuration (without passwords)

## Benefits After Migration

- ✅ **Multi-user support**: Each user has own accounts
- ✅ **Better security**: Encrypted credentials, JWT auth
- ✅ **Web interface**: Easy configuration (when implemented)
- ✅ **API access**: Programmatic control
- ✅ **Better monitoring**: Statistics, logs per account
- ✅ **Scalability**: Can handle many users
- ✅ **Subscription management**: Monetization ready
- ✅ **More protocols**: POP3 and IMAP support
- ✅ **Auto-detection**: Server settings for common providers
- ✅ **Flexible notifications**: Multiple channels via Apprise

---

**Need Help?** Open an issue or discussion on GitHub!

Last Updated: 2026-02-01
