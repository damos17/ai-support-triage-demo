from __future__ import annotations

from html import escape
from typing import Any


def escape_dynamic_text(value: Any) -> Any:
    """Recursively HTML-escape strings before they reach the dashboard.

    The public demo renders some API values inside HTML fragments in the browser.
    Keeping raw state in the application while escaping response payload strings
    prevents user/model-provided markup from becoming executable DOM content.
    """
    if isinstance(value, str):
        return escape(value, quote=True)
    if isinstance(value, list):
        return [escape_dynamic_text(item) for item in value]
    if isinstance(value, tuple):
        return [escape_dynamic_text(item) for item in value]
    if isinstance(value, dict):
        return {key: escape_dynamic_text(item) for key, item in value.items()}
    return value
