# Quick Start Guide

Get your InboxConverge instance running in under 10 minutes!

## Prerequisites

- Docker and Docker Compose installed
- Gmail account with 2FA enabled
- POP3 email account credentials

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/christianlouis/inboxconverge.git
cd inboxconverge
```

### 2. Generate Gmail App Password

1. Visit: https://myaccount.google.com/apppasswords
2. Sign in to your Google Account
3. Select "App passwords" under Security
4. Choose "Mail" and "Other (Custom name)"
5. Enter "InboxConverge" as the name
6. Click "Generate"
7. **Copy the 16-character password** (you'll need this in step 3)

### 3. Create Configuration File

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

Edit the following required fields:

```bash
# Your POP3 mailbox
POP3_ACCOUNT_1_HOST=pop.yourprovider.com
POP3_ACCOUNT_1_USER=your-email@provider.com
POP3_ACCOUNT_1_PASSWORD=your-pop3-password

# Your Gmail account
SMTP_USER=youremail@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # The 16-char app password from step 2
GMAIL_DESTINATION=youremail@gmail.com
```

**Important**: Keep the same email for `SMTP_USER` and `GMAIL_DESTINATION`

### 4. Start the Container

```bash
docker-compose up -d
```

### 5. Verify It's Working

Check the logs:

```bash
docker-compose logs -f
```

You should see:
```
inboxconverge | INFO - InboxConverge starting...
inboxconverge | INFO - Loaded POP3 account: ...
inboxconverge | INFO - Configuration validated successfully
inboxconverge | INFO - Starting email processing cycle
```

### 6. Test the Forwarder

1. Send a test email to your POP3 account
2. Wait up to 5 minutes (or check the logs)
3. Check your Gmail inbox
4. You should see: `[Fwd from your-email@provider.com] Test Subject`

## Common Issues

### "Username and Password not accepted"

**Problem**: Gmail rejects login

**Fix**:
1. Make sure 2FA is enabled on your Google account
2. Generate a new App Password (don't use your regular Gmail password)
3. Copy it exactly without spaces into `SMTP_PASSWORD`

### "No address associated with hostname"

**Problem**: Can't connect to POP3 server

**Fix**:
1. Verify `POP3_ACCOUNT_1_HOST` is correct
2. Check if POP3 is enabled in your email provider's settings
3. Try port 110 with `POP3_ACCOUNT_1_USE_SSL=false` if port 995 doesn't work

### Container stops immediately

**Problem**: Container exits right after starting

**Fix**:
```bash
# Check logs for errors
docker-compose logs

# Common fixes:
# 1. Check .env file exists and has correct values
# 2. Verify all required fields are set
# 3. Check Docker has internet access
```

## Adding More POP3 Accounts

To forward from multiple email accounts:

```bash
# Edit .env and add more accounts:
POP3_ACCOUNT_2_HOST=pop.another.com
POP3_ACCOUNT_2_USER=user@another.com
POP3_ACCOUNT_2_PASSWORD=another-password

POP3_ACCOUNT_3_HOST=pop.yetanother.com
POP3_ACCOUNT_3_USER=user@yetanother.com
POP3_ACCOUNT_3_PASSWORD=yetanother-password

# Restart the container
docker-compose restart
```

## Managing the Service

```bash
# View logs
docker-compose logs -f

# Stop the service
docker-compose down

# Restart after config changes
docker-compose restart

# Rebuild after code updates
docker-compose up -d --build
```

## Optional: Error Notifications

To receive email alerts when errors occur:

1. Sign up at https://postmarkapp.com (free tier available)
2. Get your Server API Token
3. Add to `.env`:

```bash
POSTMARK_API_TOKEN=your-token-here
POSTMARK_FROM_EMAIL=errors@yourdomain.com
POSTMARK_TO_EMAIL=admin@yourdomain.com
```

4. Restart: `docker-compose restart`

## Customizing Settings

All settings in `.env` can be adjusted:

```bash
# Check every 10 minutes instead of 5
CHECK_INTERVAL_MINUTES=10

# Process up to 100 emails per run
MAX_EMAILS_PER_RUN=100

# Send up to 20 emails per minute
THROTTLE_EMAILS_PER_MINUTE=20

# Enable debug logging
LOG_LEVEL=DEBUG
```

Restart after changes: `docker-compose restart`

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Review [MVP.md](MVP.md) for current features
- Check [ROADMAP.md](ROADMAP.md) for planned features

## Need Help?

- Open an issue: https://github.com/christianlouis/inboxconverge/issues
- Check existing discussions
- Review troubleshooting section in README.md

## Success! 🎉

Your InboxConverge instance is now running. Emails will be automatically forwarded every 5 minutes (or your configured interval).

**Remember**: 
- The forwarder deletes emails from POP3 after successful forwarding
- Check Gmail spam folder if emails don't appear in inbox
- Monitor logs occasionally to ensure everything is working
