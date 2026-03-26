# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 2.x     | ✅ Yes             |
| 1.x     | ❌ No              |
| < 1.0   | ❌ No              |

## Reporting a Vulnerability

**Please do NOT open public issues for security vulnerabilities.**

If you discover a security vulnerability, please report it responsibly:

1. **Email**: Send details to the repository maintainer via the email listed on the [GitHub profile](https://github.com/christianlouis).
2. **GitHub Private Vulnerability Reporting**: Use [GitHub's security advisory feature](https://github.com/christianlouis/inboxconverge/security/advisories/new) to report privately.

### What to Include

- A description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix & Disclosure**: Coordinated with the reporter

## Security Best Practices for Users

- **Never commit `.env` files** containing credentials
- **Use App Passwords** for Gmail instead of your main password
- **Enable 2FA** on all email accounts
- **Rotate credentials** regularly
- **Use SSL/TLS** for all mail connections
- **Run containers as non-root** (default in provided Dockerfile)
- **Keep dependencies updated** — Dependabot is enabled on this repository
