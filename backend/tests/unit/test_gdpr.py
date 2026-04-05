"""
Unit tests for GDPR data masking utilities (core/gdpr.py).
No database or HTTP layer required – pure function tests.
"""


from app.core.gdpr import mask_email, mask_name, mask_from_header


class TestMaskEmail:
    def test_typical_address(self):
        assert mask_email("john.doe@example.com") == "jo***@e***.com"

    def test_short_local(self):
        # local part has only 1 char; still returns that char + ***
        result = mask_email("a@b.de")
        assert result == "a***@b***.de"

    def test_two_char_local(self):
        result = mask_email("ab@x.io")
        assert result == "ab***@x***.io"

    def test_domain_with_subdomain_tld(self):
        # rsplit('.', 1) splits on the last dot only
        result = mask_email("user@mail.example.org")
        assert result == "us***@m***.org"

    def test_empty_string(self):
        assert mask_email("") == "***"

    def test_no_at_sign(self):
        assert mask_email("notanemail") == "***"

    def test_preserves_tld(self):
        result = mask_email("hello@world.co.uk")
        assert result.endswith(".uk")

    def test_single_char_sld(self):
        result = mask_email("user@x.com")
        assert result == "us***@x***.com"


class TestMaskName:
    def test_single_word(self):
        assert mask_name("Alice") == "Al***"

    def test_two_words(self):
        assert mask_name("John Doe") == "Jo*** Do***"

    def test_single_char_word(self):
        result = mask_name("X")
        assert result == "X***"

    def test_empty_string(self):
        assert mask_name("") == "***"

    def test_three_words(self):
        result = mask_name("Jean-Luc Picard")
        # Two words separated by space
        parts = result.split(" ")
        assert len(parts) == 2
        assert all(p.endswith("***") for p in parts)

    def test_long_name(self):
        result = mask_name("Alexander")
        assert result == "Al***"


class TestMaskFromHeader:
    def test_display_name_with_angle_email(self):
        result = mask_from_header("John Doe <john.doe@example.com>")
        assert "<" in result
        assert "jo***" in result
        assert "Jo***" in result

    def test_plain_email(self):
        result = mask_from_header("john.doe@example.com")
        assert result == "jo***@e***.com"

    def test_empty_string(self):
        assert mask_from_header("") == "***"

    def test_no_display_name_angle_email(self):
        result = mask_from_header("<user@example.com>")
        assert result == "us***@e***.com"

    def test_fallback_no_email_pattern(self):
        # String with no recognisable email → falls back to mask_name
        result = mask_from_header("JustAName")
        assert result == "Ju***"

    def test_quoted_display_name(self):
        result = mask_from_header('"Alice Smith" <alice@example.com>')
        assert "Al***" in result
        assert "al***" in result

    def test_angle_email_no_display(self):
        # Edge: angle brackets but empty display part
        result = mask_from_header("   <admin@site.org>")
        # No display name → returns masked email only
        assert "@" in result
        assert "***" in result
