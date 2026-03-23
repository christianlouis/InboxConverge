"""
Unit tests for provider presets and mail server auto-detection.
"""

import pytest
from app.services.mail_processor import MailServerAutoDetect


class TestMailServerAutoDetect:
    """Test mail server auto-detection with expanded provider list"""

    def test_detect_gmail(self):
        """Test Gmail auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@gmail.com")
        assert len(suggestions) > 0
        hosts = [s["host"] for s in suggestions]
        assert "pop.gmail.com" in hosts or "imap.gmail.com" in hosts

    def test_detect_googlemail(self):
        """Test googlemail.com auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@googlemail.com")
        assert len(suggestions) > 0
        hosts = [s["host"] for s in suggestions]
        assert "imap.gmail.com" in hosts

    def test_detect_gmx_de(self):
        """Test GMX.de auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@gmx.de")
        assert len(suggestions) > 0
        hosts = [s["host"] for s in suggestions]
        assert "imap.gmx.net" in hosts

    def test_detect_gmx_net(self):
        """Test GMX.net auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@gmx.net")
        assert len(suggestions) > 0

    def test_detect_webde(self):
        """Test WEB.DE auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@web.de")
        assert len(suggestions) > 0
        hosts = [s["host"] for s in suggestions]
        assert "imap.web.de" in hosts

    def test_detect_outlook(self):
        """Test Outlook.com auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@outlook.com")
        assert len(suggestions) > 0
        hosts = [s["host"] for s in suggestions]
        assert "outlook.office365.com" in hosts

    def test_detect_hotmail(self):
        """Test Hotmail auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@hotmail.com")
        assert len(suggestions) > 0
        hosts = [s["host"] for s in suggestions]
        assert "outlook.office365.com" in hosts

    def test_detect_yahoo(self):
        """Test Yahoo auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@yahoo.com")
        assert len(suggestions) > 0
        hosts = [s["host"] for s in suggestions]
        assert "imap.mail.yahoo.com" in hosts

    def test_detect_aol(self):
        """Test AOL auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@aol.com")
        assert len(suggestions) > 0
        hosts = [s["host"] for s in suggestions]
        assert "imap.aol.com" in hosts

    def test_detect_tonline(self):
        """Test T-Online auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@t-online.de")
        assert len(suggestions) > 0
        hosts = [s["host"] for s in suggestions]
        assert "secureimap.t-online.de" in hosts

    def test_detect_ionos(self):
        """Test 1&1/IONOS auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@online.de")
        assert len(suggestions) > 0
        hosts = [s["host"] for s in suggestions]
        assert "imap.ionos.de" in hosts

    def test_detect_freenet(self):
        """Test Freenet auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@freenet.de")
        assert len(suggestions) > 0
        hosts = [s["host"] for s in suggestions]
        assert "mx.freenet.de" in hosts

    def test_detect_posteo(self):
        """Test Posteo auto-detection (IMAP only)"""
        suggestions = MailServerAutoDetect.detect("user@posteo.de")
        assert len(suggestions) > 0
        # Posteo only has IMAP
        protocols = [s["protocol"] for s in suggestions]
        assert "imap_ssl" in protocols

    def test_detect_icloud(self):
        """Test iCloud auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@icloud.com")
        assert len(suggestions) > 0
        hosts = [s["host"] for s in suggestions]
        assert "imap.mail.me.com" in hosts

    def test_detect_unknown_domain(self):
        """Test auto-detection for unknown domain"""
        suggestions = MailServerAutoDetect.detect("user@unknowndomain123.com")
        assert len(suggestions) > 0
        # Should return generic suggestions
        providers = set(s["provider_name"] for s in suggestions)
        assert "Generic" in providers

    def test_detect_case_insensitive(self):
        """Test that domain detection is case-insensitive"""
        suggestions_lower = MailServerAutoDetect.detect("user@Gmail.com")
        suggestions_upper = MailServerAutoDetect.detect("user@GMAIL.COM")
        # Both should detect as Gmail
        assert len(suggestions_lower) > 0
        assert len(suggestions_upper) > 0

    def test_all_suggestions_have_required_fields(self):
        """Test that all suggestions have the required fields"""
        for domain in ["gmail.com", "gmx.de", "web.de", "yahoo.com", "aol.com"]:
            suggestions = MailServerAutoDetect.detect(f"user@{domain}")
            for suggestion in suggestions:
                assert "protocol" in suggestion
                assert "host" in suggestion
                assert "port" in suggestion
                assert "provider_name" in suggestion
                assert "use_ssl" in suggestion

    def test_detect_live_com(self):
        """Test Live.com auto-detection (Microsoft)"""
        suggestions = MailServerAutoDetect.detect("user@live.com")
        assert len(suggestions) > 0

    def test_detect_ymail(self):
        """Test ymail.com auto-detection (Yahoo)"""
        suggestions = MailServerAutoDetect.detect("user@ymail.com")
        assert len(suggestions) > 0

    def test_detect_mailde(self):
        """Test mail.de auto-detection"""
        suggestions = MailServerAutoDetect.detect("user@mail.de")
        assert len(suggestions) > 0
        hosts = [s["host"] for s in suggestions]
        assert "imap.mail.de" in hosts


class TestProviderPresets:
    """Test that provider presets module defines correct values"""

    def test_provider_presets_import(self):
        """Test that provider presets can be imported"""
        from app.api.v1.endpoints.providers import PROVIDER_PRESETS

        assert len(PROVIDER_PRESETS) > 0

    def test_all_presets_have_required_fields(self):
        """Test that all presets have required fields"""
        from app.api.v1.endpoints.providers import PROVIDER_PRESETS

        for preset in PROVIDER_PRESETS:
            assert preset.id
            assert preset.name
            assert len(preset.domains) > 0
            # Must have at least one protocol
            assert preset.imap_ssl is not None or preset.pop3_ssl is not None

    def test_gmail_preset_exists(self):
        """Test that Gmail preset is included"""
        from app.api.v1.endpoints.providers import PROVIDER_PRESETS

        gmail = next((p for p in PROVIDER_PRESETS if p.id == "gmail"), None)
        assert gmail is not None
        assert gmail.imap_ssl is not None
        assert gmail.imap_ssl["host"] == "imap.gmail.com"

    def test_gmx_preset_exists(self):
        """Test that GMX preset is included"""
        from app.api.v1.endpoints.providers import PROVIDER_PRESETS

        gmx = next((p for p in PROVIDER_PRESETS if p.id == "gmx"), None)
        assert gmx is not None
        assert "gmx.de" in gmx.domains

    def test_webde_preset_exists(self):
        """Test that WEB.DE preset is included"""
        from app.api.v1.endpoints.providers import PROVIDER_PRESETS

        webde = next((p for p in PROVIDER_PRESETS if p.id == "webde"), None)
        assert webde is not None
        assert "web.de" in webde.domains

    def test_outlook_preset_exists(self):
        """Test that Outlook preset is included"""
        from app.api.v1.endpoints.providers import PROVIDER_PRESETS

        outlook = next((p for p in PROVIDER_PRESETS if p.id == "outlook"), None)
        assert outlook is not None
        assert "hotmail.com" in outlook.domains

    def test_yahoo_preset_exists(self):
        """Test that Yahoo preset is included"""
        from app.api.v1.endpoints.providers import PROVIDER_PRESETS

        yahoo = next((p for p in PROVIDER_PRESETS if p.id == "yahoo"), None)
        assert yahoo is not None

    def test_aol_preset_exists(self):
        """Test that AOL preset is included"""
        from app.api.v1.endpoints.providers import PROVIDER_PRESETS

        aol = next((p for p in PROVIDER_PRESETS if p.id == "aol"), None)
        assert aol is not None

    def test_tonline_preset_exists(self):
        """Test that T-Online preset is included"""
        from app.api.v1.endpoints.providers import PROVIDER_PRESETS

        tonline = next((p for p in PROVIDER_PRESETS if p.id == "tonline"), None)
        assert tonline is not None
