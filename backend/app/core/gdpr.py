"""
GDPR-compliant data masking utilities.

These helpers are used in admin-facing API responses to pseudonymise
personal data (email addresses, names) so that operators can audit
system behaviour without seeing full end-user PII.
"""

from __future__ import annotations

import re


def mask_email(email: str) -> str:
    """
    Partially mask an email address for GDPR-compliant display.

    Examples
    --------
    >>> mask_email("john.doe@example.com")
    'jo***@e***.com'
    >>> mask_email("ab@x.io")
    'ab***@x***.io'
    >>> mask_email("a@b.de")
    'a***@b***.de'
    """
    if not email or "@" not in email:
        return "***"

    local, _, domain = email.partition("@")

    # Local part: keep first 2 chars (or all if shorter), then "***"
    visible_local = local[:2] if len(local) >= 2 else local
    masked_local = f"{visible_local}***"

    # Domain part: keep first char of SLD and the TLD unchanged
    domain_parts = domain.rsplit(".", 1)
    if len(domain_parts) == 2:
        sld, tld = domain_parts
        visible_sld = sld[:1] if sld else ""
        masked_domain = f"{visible_sld}***.{tld}"
    else:
        masked_domain = "***"

    return f"{masked_local}@{masked_domain}"


def mask_name(name: str) -> str:
    """
    Partially mask a display name.

    Examples
    --------
    >>> mask_name("John Doe")
    'Jo*** D***'
    >>> mask_name("Alice")
    'Al***'
    """
    if not name:
        return "***"
    words = name.split()
    masked_words = []
    for word in words:
        visible = word[:2] if len(word) >= 2 else word
        masked_words.append(f"{visible}***")
    return " ".join(masked_words)


# RFC 5322 address pattern – extracts the bare email from strings like
# "John Doe <john@example.com>" or just "john@example.com".
_ADDR_RE = re.compile(r"<([^>]+)>|(\S+@\S+\.\S+)")


def mask_from_header(from_header: str) -> str:
    """
    Mask a raw RFC 5322 From header value for GDPR-compliant display.

    Examples
    --------
    >>> mask_from_header("John Doe <john.doe@example.com>")
    'Jo*** D*** <jo***@e***.com>'
    >>> mask_from_header("john.doe@example.com")
    'jo***@e***.com'
    """
    if not from_header:
        return "***"

    # Try to parse "Display Name <email>" form
    angle_match = re.search(r"^(.*?)<([^>]+)>", from_header.strip())
    if angle_match:
        display_name = angle_match.group(1).strip().strip('"')
        email_part = angle_match.group(2).strip()
        masked_email = mask_email(email_part)
        if display_name:
            masked_display = mask_name(display_name)
            return f"{masked_display} <{masked_email}>"
        return masked_email

    # Plain email address
    bare_match = _ADDR_RE.search(from_header)
    if bare_match:
        email_part = bare_match.group(1) or bare_match.group(2)
        return mask_email(email_part)

    # Fallback: mask the whole string
    return mask_name(from_header)
