"""Small display helpers."""

from collections.abc import Mapping
from typing import Any

NA = "N/A"


def format_metric(metrics: Mapping[str, Any], key: str, digits: int = 4) -> str:
    """Format a scalar metric, tolerating numpy scalars and missing keys."""
    value = metrics.get(key)
    if value is None:
        return NA
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)
