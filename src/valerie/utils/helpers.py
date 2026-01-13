"""Helper utility functions."""

from typing import Any

from ..models import Supplier


def format_supplier_list(suppliers: list[Supplier]) -> str:
    """Format a list of suppliers for display."""
    if not suppliers:
        return "No suppliers found."

    lines = []
    for i, supplier in enumerate(suppliers, 1):
        lines.append(f"{i}. **{supplier.name}**")
        if supplier.location:
            lines.append(f"   Location: {supplier.location}")
        if supplier.capabilities:
            lines.append(f"   Capabilities: {', '.join(supplier.capabilities)}")
        if supplier.quality_rate is not None:
            lines.append(f"   Quality Rate: {supplier.quality_rate}%")
        lines.append("")

    return "\n".join(lines)


def format_risk_level(score: float) -> tuple[str, str]:
    """Convert risk score to level and color.

    Returns:
        Tuple of (level_name, color_code)
    """
    if score < 0.2:
        return "Low", "green"
    elif score < 0.4:
        return "Moderate", "yellow"
    elif score < 0.6:
        return "Elevated", "orange"
    elif score < 0.8:
        return "High", "red"
    else:
        return "Critical", "darkred"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary values."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current
