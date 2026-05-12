"""Shared JSON parsing helpers."""

from __future__ import annotations

import json
from typing import Any


def parse_json_field(val: Any) -> Any:
    """Parse a JSON string field from DB, or return as-is if already parsed."""
    if val is None:
        return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    return val
