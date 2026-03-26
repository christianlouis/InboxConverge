"""Helpers for Gmail import label configuration and rendering."""

from typing import Any, Iterable, Optional

SOURCE_EMAIL_LABEL_TEMPLATE = "{{source_email}}"
DEFAULT_IMPORT_LABEL_TEMPLATES = [SOURCE_EMAIL_LABEL_TEMPLATE, "imported"]
MAX_IMPORT_LABELS = 10


def _normalize_string_list(values: Optional[Iterable[str]]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for value in values or []:
        cleaned = value.strip()
        if not cleaned:
            continue
        lowered = cleaned.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(cleaned)

    return normalized


def normalize_import_label_templates(
    label_templates: Optional[Iterable[str]],
) -> list[str]:
    """Return a cleaned, de-duplicated label template list."""
    normalized = _normalize_string_list(label_templates)
    return normalized or DEFAULT_IMPORT_LABEL_TEMPLATES.copy()


def extract_granted_scopes(scopes_data: Any) -> list[str]:
    """Read granted scopes from legacy list or new JSON object storage."""
    if isinstance(scopes_data, list):
        return _normalize_string_list(
            value for value in scopes_data if isinstance(value, str)
        )

    if isinstance(scopes_data, dict):
        granted_scopes = scopes_data.get("granted_scopes", [])
        if isinstance(granted_scopes, list):
            return _normalize_string_list(
                value for value in granted_scopes if isinstance(value, str)
            )

    return []


def extract_import_label_templates(scopes_data: Any) -> list[str]:
    """Read import label templates from stored Gmail credential metadata."""
    if isinstance(scopes_data, dict):
        stored_templates = scopes_data.get("import_label_templates", [])
        if isinstance(stored_templates, list):
            return normalize_import_label_templates(
                value for value in stored_templates if isinstance(value, str)
            )

    return DEFAULT_IMPORT_LABEL_TEMPLATES.copy()


def build_gmail_credential_scopes(
    granted_scopes: Optional[Iterable[str]],
    import_label_templates: Optional[Iterable[str]] = None,
) -> dict[str, list[str]]:
    """Persist Gmail metadata in the existing JSON column."""
    return {
        "granted_scopes": _normalize_string_list(granted_scopes),
        "import_label_templates": normalize_import_label_templates(
            import_label_templates
        ),
    }


def render_import_labels(
    import_label_templates: Optional[Iterable[str]],
    source_email: Optional[str],
) -> list[str]:
    """Render label templates into actual Gmail label names."""
    rendered_labels: list[str] = []
    seen: set[str] = set()
    resolved_source_email = source_email.strip() if source_email else ""

    for template in normalize_import_label_templates(import_label_templates):
        rendered = template.replace(SOURCE_EMAIL_LABEL_TEMPLATE, resolved_source_email)
        rendered = rendered.strip()
        if not rendered:
            continue
        lowered = rendered.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        rendered_labels.append(rendered)

    return rendered_labels
