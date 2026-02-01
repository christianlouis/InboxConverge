# POP3 to Gmail Forwarder

A Docker-based solution that automatically fetches emails from POP3 mailboxes and forwards them to Gmail, replacing Google's discontinued POP3 import feature.

## Features

- ✅ **Multiple POP3 Accounts**: Support for unlimited POP3 mailboxes via environment variables
- ✅ **Automatic Forwarding**: Sends emails to your Gmail account via SMTP
- ✅ **Smart Throttling**: Rate limiting to avoid Gmail quotas (configurable emails per minute)
- ✅ **Error Reporting**: Email notifications via Postmarkapp when issues occur
- ✅ **Scheduled Polling**: Configurable check intervals (default: every 5 minutes)
- ✅ **Docker Ready**: Fully containerized with docker-compose support
- ✅ **Secure**: Runs as non-root user, uses SSL/TLS for connections
- ✅ **Production Ready**: Comprehensive logging, error handling, and best practices

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- A Gmail account with [App Password](https://support.google.com/accounts/answer/185833) enabled
- POP3 account credentials
- (Optional) Postmarkapp account for error notifications

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/christianlouis/pop_puller_to_gmail.git
   cd pop_puller_to_gmail
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   nano .env
   ```

3. **Essential Configuration**
   
   Edit `.env` and set:
   
   ```bash
   # Your POP3 account(s)
   POP3_ACCOUNT_1_HOST=pop.yourprovider.com
   POP3_ACCOUNT_1_PORT=995
   POP3_ACCOUNT_1_USER=your-email@provider.com
   POP3_ACCOUNT_1_PASSWORD=your-password
   
   # Your Gmail SMTP settings
   SMTP_USER=your-gmail@gmail.com
   SMTP_PASSWORD=your-app-password  # Generate at myaccount.google.com/apppasswords
   GMAIL_DESTINATION=your-gmail@gmail.com
   
   # Optional: Postmarkapp for error notifications
   POSTMARK_API_TOKEN=your-token
   POSTMARK_FROM_EMAIL=errors@yourdomain.com
   POSTMARK_TO_EMAIL=admin@yourdomain.com
   ```

4. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

5. **Check logs**
   ```bash
   docker-compose logs -f
   ```

## Configuration

### POP3 Accounts

Add multiple POP3 accounts by incrementing the account number:

```bash
POP3_ACCOUNT_1_HOST=pop.provider1.com
POP3_ACCOUNT_1_USER=user1@provider1.com
POP3_ACCOUNT_1_PASSWORD=password1

POP3_ACCOUNT_2_HOST=pop.provider2.com
POP3_ACCOUNT_2_USER=user2@provider2.com
POP3_ACCOUNT_2_PASSWORD=password2

# ... add more as needed
```

### Gmail App Password

1. Go to your Google Account: https://myaccount.google.com/
2. Select Security
3. Under "Signing in to Google," select App Passwords
4. Generate a new app password for "Mail"
5. Use this password in `SMTP_PASSWORD`

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POP3_ACCOUNT_N_HOST` | Yes | - | POP3 server hostname |
| `POP3_ACCOUNT_N_PORT` | No | 995 | POP3 server port |
| `POP3_ACCOUNT_N_USER` | Yes | - | POP3 username |
| `POP3_ACCOUNT_N_PASSWORD` | Yes | - | POP3 password |
| `POP3_ACCOUNT_N_USE_SSL` | No | true | Use SSL/TLS |
| `SMTP_HOST` | No | smtp.gmail.com | SMTP server |
| `SMTP_PORT` | No | 587 | SMTP port |
| `SMTP_USER` | Yes | - | SMTP username |
| `SMTP_PASSWORD` | Yes | - | SMTP password (App Password) |
| `SMTP_USE_TLS` | No | true | Use STARTTLS |
| `GMAIL_DESTINATION` | Yes | - | Destination Gmail address |
| `CHECK_INTERVAL_MINUTES` | No | 5 | How often to check for new mail |
| `MAX_EMAILS_PER_RUN` | No | 50 | Max emails to process per account per run |
| `THROTTLE_EMAILS_PER_MINUTE` | No | 10 | Rate limit for sending emails |
| `POSTMARK_API_TOKEN` | No | - | Postmarkapp API token |
| `POSTMARK_FROM_EMAIL` | No | - | Error notification sender |
| `POSTMARK_TO_EMAIL` | No | - | Error notification recipient |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

## How It Works

1. **Polling**: The application checks configured POP3 mailboxes at regular intervals
2. **Fetching**: Retrieves new emails from each POP3 account
3. **Forwarding**: Sends emails to your Gmail account via SMTP with original metadata preserved
4. **Cleanup**: Deletes emails from POP3 server after successful forwarding
5. **Throttling**: Respects rate limits to avoid Gmail quota issues
6. **Error Handling**: Sends notifications via Postmarkapp if issues occur

## Email Format

Forwarded emails include:
- Original sender information in the subject line: `[Fwd from user@provider.com] Original Subject`
- Header section with original From, Date, Subject, and source account
- Original email body preserved

## Monitoring and Logs

### View logs
```bash
docker-compose logs -f pop3-forwarder
```

### Check container status
```bash
docker-compose ps
```

### Restart the service
```bash
docker-compose restart
```

## Troubleshooting

### Gmail Authentication Issues

**Problem**: "Username and Password not accepted"

**Solution**:
- Ensure 2FA is enabled on your Google account
- Generate an App Password (don't use your regular Gmail password)
- Use the 16-character app password without spaces

### POP3 Connection Issues

**Problem**: "Connection refused" or "SSL error"

**Solution**:
- Verify POP3 server hostname and port
- Check if POP3 is enabled in your email provider settings
- Try with `POP3_ACCOUNT_N_USE_SSL=false` for non-SSL connections (port 110)

### No Emails Being Forwarded

**Problem**: Container runs but no emails are forwarded

**Solution**:
- Check if there are emails in your POP3 mailbox
- Review logs for errors: `docker-compose logs -f`
- Verify `GMAIL_DESTINATION` is correct
- Check Gmail spam folder

### Rate Limiting

**Problem**: "Too many requests" or quota errors

**Solution**:
- Increase `CHECK_INTERVAL_MINUTES`
- Decrease `THROTTLE_EMAILS_PER_MINUTE`
- Reduce `MAX_EMAILS_PER_RUN`

## Security Best Practices

1. **Never commit `.env` file** - It contains sensitive credentials
2. **Use App Passwords** - Don't use your main Gmail password
3. **Rotate credentials regularly** - Update passwords periodically
4. **Enable 2FA** - On all email accounts
5. **Review logs** - Monitor for suspicious activity
6. **Use SSL/TLS** - Keep `USE_SSL` and `USE_TLS` enabled
7. **Limit network access** - Use firewall rules if needed

## Development

### Local Development (without Docker)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure .env
cp .env.example .env
# Edit .env with your settings

# Run the application
python pop3_forwarder.py
```

### Building the Docker Image

```bash
docker build -t pop3-gmail-forwarder .
```

### Running Tests

```bash
# Run with verbose logging
LOG_LEVEL=DEBUG docker-compose up
```

## Architecture

```
┌─────────────────┐
│  POP3 Server 1  │
└────────┬────────┘
         │
         │ (Fetch emails)
         │
         ▼
┌─────────────────┐      ┌──────────────┐      ┌─────────────┐
│  POP3 Server 2  │─────▶│  Forwarder   │─────▶│    Gmail    │
└─────────────────┘      │  Container   │      │   (SMTP)    │
         │               └──────┬───────┘      └─────────────┘
         │                      │
┌────────▼────────┐             │
│  POP3 Server N  │             │
└─────────────────┘             │
                                │ (Error notifications)
                                ▼
                      ┌─────────────────┐
                      │   Postmarkapp   │
                      └─────────────────┘
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

- **Issues**: https://github.com/christianlouis/pop_puller_to_gmail/issues
- **Discussions**: https://github.com/christianlouis/pop_puller_to_gmail/discussions

## Acknowledgments

Built to replace Gmail's discontinued POP3 import feature. Uses industry-standard Python libraries for email handling and Docker for easy deployment.
