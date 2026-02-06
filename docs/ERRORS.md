# Error Codes and Messages

This document catalogs all error codes used in the POP3 to Gmail Forwarder application.

## Error Code Format

Error codes follow this pattern: `[DOMAIN]_[NUMBER]`

- **AUTH**: Authentication and authorization errors (001-099)
- **MAIL**: Mail processing errors (100-199)
- **SUB**: Subscription and billing errors (200-299)
- **USER**: User management errors (300-399)
- **NOTIFY**: Notification errors (400-499)
- **SYS**: System and infrastructure errors (500-599)

---

## Authentication & Authorization (AUTH_001-099)

### AUTH_001: Invalid Credentials
- **HTTP Status**: 401 Unauthorized
- **Message**: "Invalid email or password"
- **Cause**: Wrong email/password combination during login
- **Action**: Verify credentials, reset password if needed

### AUTH_002: Token Expired
- **HTTP Status**: 401 Unauthorized
- **Message**: "Authentication token has expired"
- **Cause**: JWT token lifetime exceeded
- **Action**: Refresh token or re-authenticate

### AUTH_003: Token Invalid
- **HTTP Status**: 401 Unauthorized
- **Message**: "Invalid authentication token"
- **Cause**: Malformed or tampered JWT token
- **Action**: Clear tokens and re-authenticate

### AUTH_004: Insufficient Permissions
- **HTTP Status**: 403 Forbidden
- **Message**: "You don't have permission to perform this action"
- **Cause**: User role lacks required permissions
- **Action**: Contact administrator for access

### AUTH_005: Email Already Registered
- **HTTP Status**: 409 Conflict
- **Message**: "An account with this email already exists"
- **Cause**: Registration with existing email
- **Action**: Use different email or login instead

### AUTH_006: OAuth Provider Error
- **HTTP Status**: 502 Bad Gateway
- **Message**: "Failed to authenticate with OAuth provider"
- **Cause**: Google OAuth service unavailable
- **Action**: Retry or use email/password login

### AUTH_007: Invalid OAuth State
- **HTTP Status**: 400 Bad Request
- **Message**: "Invalid OAuth state parameter"
- **Cause**: CSRF token mismatch in OAuth flow
- **Action**: Restart OAuth flow from beginning

### AUTH_008: Email Not Verified
- **HTTP Status**: 403 Forbidden
- **Message**: "Please verify your email address"
- **Cause**: Attempting action before email verification
- **Action**: Check email and click verification link

---

## Mail Processing (MAIL_100-199)

### MAIL_100: Connection Failed
- **HTTP Status**: 502 Bad Gateway
- **Message**: "Failed to connect to POP3/IMAP server"
- **Cause**: Network error, wrong host/port, firewall
- **Action**: Verify host, port, network connectivity

### MAIL_101: Authentication Failed
- **HTTP Status**: 401 Unauthorized
- **Message**: "POP3/IMAP authentication failed"
- **Cause**: Invalid credentials for mail account
- **Action**: Update mail account credentials

### MAIL_102: SSL/TLS Error
- **HTTP Status**: 502 Bad Gateway
- **Message**: "SSL/TLS connection error"
- **Cause**: Certificate issues, SSL not supported
- **Action**: Verify SSL settings, check certificate

### MAIL_103: Mailbox Not Found
- **HTTP Status**: 404 Not Found
- **Message**: "Mailbox or folder not found"
- **Cause**: IMAP folder doesn't exist
- **Action**: Check folder name, create if needed

### MAIL_104: Message Retrieval Failed
- **HTTP Status**: 500 Internal Server Error
- **Message**: "Failed to retrieve email message"
- **Cause**: Corrupt message, server error
- **Action**: Skip message, contact mail provider

### MAIL_105: Forward Failed
- **HTTP Status**: 502 Bad Gateway
- **Message**: "Failed to forward email"
- **Cause**: SMTP error, network issue
- **Action**: Retry, check SMTP settings

### MAIL_106: Rate Limit Exceeded
- **HTTP Status**: 429 Too Many Requests
- **Message**: "Email forwarding rate limit exceeded"
- **Cause**: Too many emails sent too quickly
- **Action**: Wait, upgrade plan, adjust throttling

### MAIL_107: Message Too Large
- **HTTP Status**: 413 Payload Too Large
- **Message**: "Email message exceeds size limit"
- **Cause**: Message larger than allowed size
- **Action**: Filter large messages, upgrade plan

### MAIL_108: Invalid Email Format
- **HTTP Status**: 422 Unprocessable Entity
- **Message**: "Email message format is invalid"
- **Cause**: Malformed email headers or body
- **Action**: Check source email, skip if necessary

### MAIL_109: Encryption Failed
- **HTTP Status**: 500 Internal Server Error
- **Message**: "Failed to encrypt mail credentials"
- **Cause**: Encryption key issue
- **Action**: Check ENCRYPTION_KEY configuration

### MAIL_110: Decryption Failed
- **HTTP Status**: 500 Internal Server Error
- **Message**: "Failed to decrypt mail credentials"
- **Cause**: Wrong encryption key or corrupt data
- **Action**: Re-save credentials with correct key

---

## Subscription & Billing (SUB_200-299)

### SUB_200: Subscription Required
- **HTTP Status**: 402 Payment Required
- **Message**: "This feature requires an active subscription"
- **Cause**: Attempting premium feature without subscription
- **Action**: Subscribe to a plan

### SUB_201: Limit Reached
- **HTTP Status**: 403 Forbidden
- **Message**: "You've reached your plan limit for [resource]"
- **Cause**: Plan limits exceeded (accounts, emails, etc.)
- **Action**: Upgrade plan or remove unused resources

### SUB_202: Payment Failed
- **HTTP Status**: 402 Payment Required
- **Message**: "Payment processing failed"
- **Cause**: Invalid payment method, insufficient funds
- **Action**: Update payment method

### SUB_203: Subscription Expired
- **HTTP Status**: 402 Payment Required
- **Message**: "Your subscription has expired"
- **Cause**: Subscription period ended
- **Action**: Renew subscription

### SUB_204: Invalid Plan
- **HTTP Status**: 404 Not Found
- **Message**: "Subscription plan not found"
- **Cause**: Requesting non-existent plan
- **Action**: Choose valid plan from available options

### SUB_205: Downgrade Not Allowed
- **HTTP Status**: 409 Conflict
- **Message**: "Cannot downgrade: usage exceeds new plan limits"
- **Cause**: Current usage > target plan limits
- **Action**: Reduce usage before downgrading

---

## User Management (USER_300-399)

### USER_300: User Not Found
- **HTTP Status**: 404 Not Found
- **Message**: "User account not found"
- **Cause**: Invalid user ID or deleted account
- **Action**: Verify user ID or create account

### USER_301: Profile Update Failed
- **HTTP Status**: 500 Internal Server Error
- **Message**: "Failed to update user profile"
- **Cause**: Database error, validation failure
- **Action**: Retry, check input data

### USER_302: Password Too Weak
- **HTTP Status**: 422 Unprocessable Entity
- **Message**: "Password does not meet security requirements"
- **Cause**: Password too short or simple
- **Action**: Use stronger password (8+ chars, mixed case, numbers)

### USER_303: Deletion Restricted
- **HTTP Status**: 409 Conflict
- **Message**: "Cannot delete user: active subscription"
- **Cause**: User has active subscription
- **Action**: Cancel subscription first

---

## Notifications (NOTIFY_400-499)

### NOTIFY_400: Notification Failed
- **HTTP Status**: 500 Internal Server Error
- **Message**: "Failed to send notification"
- **Cause**: Notification service error
- **Action**: Check notification service configuration

### NOTIFY_401: Invalid Channel
- **HTTP Status**: 422 Unprocessable Entity
- **Message**: "Invalid notification channel"
- **Cause**: Unsupported notification type
- **Action**: Use supported channel (email, webhook, etc.)

### NOTIFY_402: Channel Not Configured
- **HTTP Status**: 424 Failed Dependency
- **Message**: "Notification channel not configured"
- **Cause**: Required channel settings missing
- **Action**: Configure notification settings

---

## System Errors (SYS_500-599)

### SYS_500: Database Error
- **HTTP Status**: 500 Internal Server Error
- **Message**: "Database operation failed"
- **Cause**: Database connection or query error
- **Action**: Retry, check database status

### SYS_501: Redis Error
- **HTTP Status**: 500 Internal Server Error
- **Message**: "Cache service unavailable"
- **Cause**: Redis connection error
- **Action**: Check Redis service status

### SYS_502: Celery Task Failed
- **HTTP Status**: 500 Internal Server Error
- **Message**: "Background task processing failed"
- **Cause**: Celery worker error
- **Action**: Check worker logs, retry task

### SYS_503: Configuration Error
- **HTTP Status**: 500 Internal Server Error
- **Message**: "System configuration error"
- **Cause**: Invalid or missing configuration
- **Action**: Check environment variables

### SYS_504: External Service Timeout
- **HTTP Status**: 504 Gateway Timeout
- **Message**: "External service request timed out"
- **Cause**: Slow response from external API
- **Action**: Retry, check service status

---

## Usage in Code

### Example: Raising Errors
```python
from fastapi import HTTPException, status
from app.core.errors import ErrorCode, ErrorResponse

# Structured error response
raise HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail=ErrorResponse(
        code=ErrorCode.SUB_201,
        message="You've reached your plan limit for mail accounts",
        details={
            "current": 5,
            "limit": 5,
            "plan": "basic",
            "upgrade_url": "/pricing"
        }
    ).dict()
)
```

### Example: Error Response Schema
```python
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    code: str  # e.g., "MAIL_100"
    message: str  # Human-readable message
    details: dict = {}  # Additional context
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: str = ""  # For tracing
```

### Example: Client Handling
```javascript
// Frontend error handling
try {
  const response = await fetch('/api/v1/mail-accounts/', options);
  if (!response.ok) {
    const error = await response.json();
    
    switch(error.code) {
      case 'SUB_201':
        showUpgradeModal(error.details);
        break;
      case 'MAIL_100':
        showConnectionErrorDialog(error.message);
        break;
      default:
        showGenericError(error.message);
    }
  }
} catch (err) {
  console.error('Request failed:', err);
}
```

---

## Adding New Error Codes

When adding new error codes:

1. Choose appropriate category (AUTH, MAIL, SUB, USER, NOTIFY, SYS)
2. Assign next available number in that range
3. Document in this file with:
   - HTTP status code
   - Message template
   - Cause
   - Recommended action
4. Update `app/core/errors.py` with the code constant
5. Add to API documentation examples

---

**Last Updated**: 2026-02-06
**Maintainer**: Development Team
