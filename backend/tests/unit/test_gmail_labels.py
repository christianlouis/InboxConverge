"""
Unit tests for Gmail label utilities (utils/gmail_labels.py).
Pure function tests – no database or HTTP layer required.
"""

from app.utils.gmail_labels import (
    DEFAULT_IMPORT_LABEL_TEMPLATES,
    MAX_IMPORT_LABELS,
    _normalize_string_list,
    normalize_import_label_templates,
    extract_granted_scopes,
    extract_import_label_templates,
    build_gmail_credential_scopes,
    render_import_labels,
)


class TestNormalizeStringList:
    def test_basic_dedup(self):
        result = _normalize_string_list(["a", "A", "b"])
        assert result == ["a", "b"]

    def test_strips_whitespace(self):
        result = _normalize_string_list(["  hello  ", "world"])
        assert result == ["hello", "world"]

    def test_empty_strings_filtered(self):
        result = _normalize_string_list(["", "  ", "real"])
        assert result == ["real"]

    def test_none_returns_empty(self):
        assert _normalize_string_list(None) == []

    def test_preserves_case_in_output(self):
        # Case-insensitive dedup but preserves original casing
        result = _normalize_string_list(["Hello", "hello"])
        assert result == ["Hello"]

    def test_order_preserved(self):
        items = ["c", "a", "b"]
        assert _normalize_string_list(items) == ["c", "a", "b"]


class TestNormalizeImportLabelTemplates:
    def test_none_returns_defaults(self):
        result = normalize_import_label_templates(None)
        assert result == DEFAULT_IMPORT_LABEL_TEMPLATES

    def test_empty_list_returns_defaults(self):
        result = normalize_import_label_templates([])
        assert result == DEFAULT_IMPORT_LABEL_TEMPLATES

    def test_custom_templates(self):
        result = normalize_import_label_templates(["archive", "inbox"])
        assert result == ["archive", "inbox"]

    def test_deduplicates(self):
        result = normalize_import_label_templates(["tag", "TAG"])
        assert result == ["tag"]

    def test_returns_copy_of_defaults(self):
        result = normalize_import_label_templates(None)
        result.append("extra")
        assert "extra" not in DEFAULT_IMPORT_LABEL_TEMPLATES


class TestExtractGrantedScopes:
    def test_list_format(self):
        result = extract_granted_scopes(["scope1", "scope2"])
        assert result == ["scope1", "scope2"]

    def test_list_filters_non_strings(self):
        result = extract_granted_scopes(["valid", 42, None, "other"])
        assert result == ["valid", "other"]

    def test_dict_format(self):
        data = {"granted_scopes": ["https://mail.google.com/", "openid"]}
        result = extract_granted_scopes(data)
        assert result == ["https://mail.google.com/", "openid"]

    def test_dict_missing_granted_scopes(self):
        result = extract_granted_scopes({})
        assert result == []

    def test_dict_non_list_granted_scopes(self):
        result = extract_granted_scopes({"granted_scopes": "not-a-list"})
        assert result == []

    def test_unrecognized_type(self):
        assert extract_granted_scopes(None) == []
        assert extract_granted_scopes(42) == []
        assert extract_granted_scopes("string") == []


class TestExtractImportLabelTemplates:
    def test_dict_with_templates(self):
        data = {"import_label_templates": ["archive", "imported"]}
        result = extract_import_label_templates(data)
        assert result == ["archive", "imported"]

    def test_dict_missing_key(self):
        result = extract_import_label_templates({})
        assert result == DEFAULT_IMPORT_LABEL_TEMPLATES

    def test_non_dict(self):
        assert extract_import_label_templates(None) == DEFAULT_IMPORT_LABEL_TEMPLATES
        assert extract_import_label_templates([]) == DEFAULT_IMPORT_LABEL_TEMPLATES

    def test_empty_templates_falls_back_to_defaults(self):
        result = extract_import_label_templates({"import_label_templates": []})
        assert result == DEFAULT_IMPORT_LABEL_TEMPLATES

    def test_filters_non_strings(self):
        data = {"import_label_templates": ["valid", 123, None]}
        result = extract_import_label_templates(data)
        assert result == ["valid"]


class TestBuildGmailCredentialScopes:
    def test_basic(self):
        result = build_gmail_credential_scopes(
            ["https://mail.google.com/"], ["{{source_email}}", "imported"]
        )
        assert "granted_scopes" in result
        assert "import_label_templates" in result
        assert result["granted_scopes"] == ["https://mail.google.com/"]

    def test_none_granted_scopes(self):
        result = build_gmail_credential_scopes(None)
        assert result["granted_scopes"] == []
        assert result["import_label_templates"] == DEFAULT_IMPORT_LABEL_TEMPLATES

    def test_deduplication(self):
        result = build_gmail_credential_scopes(["scope", "SCOPE"])
        assert result["granted_scopes"] == ["scope"]


class TestRenderImportLabels:
    def test_source_email_substitution(self):
        result = render_import_labels(["{{source_email}}"], "user@example.com")
        assert result == ["user@example.com"]

    def test_literal_template(self):
        result = render_import_labels(["imported"], "user@example.com")
        assert result == ["imported"]

    def test_mixed_templates(self):
        result = render_import_labels(
            ["{{source_email}}", "imported"], "user@example.com"
        )
        assert result == ["user@example.com", "imported"]

    def test_deduplication(self):
        result = render_import_labels(["tag", "TAG"], "user@example.com")
        assert result == ["tag"]

    def test_none_source_email(self):
        # Template containing source_email placeholder with no email → empty string,
        # gets stripped, filtered out.
        result = render_import_labels(["{{source_email}}"], None)
        assert result == []

    def test_empty_source_email(self):
        result = render_import_labels(["{{source_email}}"], "")
        assert result == []

    def test_none_templates_uses_defaults(self):
        result = render_import_labels(None, "user@example.com")
        assert "user@example.com" in result
        assert "imported" in result

    def test_whitespace_only_template_filtered(self):
        # Whitespace-only entries are stripped to empty strings and then filtered
        # by normalize_import_label_templates. When no valid templates remain,
        # defaults are returned. The source_email template then renders to the
        # source email, and "imported" is included too.
        result = render_import_labels(["   "], "user@example.com")
        # normalize_import_label_templates falls back to defaults → includes
        # {{source_email}} (renders to "user@example.com") and "imported"
        assert result == ["user@example.com", "imported"]

    def test_max_labels_constant(self):
        assert MAX_IMPORT_LABELS == 10
