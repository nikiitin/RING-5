"""Native Plotly projection of the shared bar hatch vocabulary."""

from typing import Any

from src.core.common.plot_payload import BAR_HATCH_PATTERNS

# Plotly pattern paths describe filled regions of an eight-pixel tile. Opposite
# ring winding keeps the circle interiors empty without a separate fill rule.
_CUSTOM_PATHS = {
    "o": (
        "M 5.5 4 A 1.5 1.5 0 1 1 2.5 4 A 1.5 1.5 0 1 1 5.5 4 Z "
        "M 5 4 A 1 1 0 1 0 3 4 A 1 1 0 1 0 5 4 Z"
    ),
    "O": (
        "M 7 4 A 3 3 0 1 1 1 4 A 3 3 0 1 1 7 4 Z "
        "M 6.2 4 A 2.2 2.2 0 1 0 1.8 4 A 2.2 2.2 0 1 0 6.2 4 Z"
    ),
    "*": (
        "M 4 0.6 L 4.823 2.867 L 7.234 2.949 L 5.331 4.432 L 5.998 6.751 "
        "L 4 5.4 L 2.002 6.751 L 2.669 4.432 L 0.766 2.949 L 3.177 2.867 Z"
    ),
}


def plotly_hatch(pattern: str) -> dict[str, Any]:
    """Project one current token, clearing incompatible prior native pattern state.

    Args:
        pattern: A token from the shared bar hatch vocabulary, including Solid.

    Returns:
        Native shape or custom SVG path properties. Unrelated marker styling is
        left to its existing owners.

    Raises:
        ValueError: The token is not an exact supported string.
    """
    # [impl->req~ring5.figure.series-styling~2]
    if type(pattern) is not str or pattern not in BAR_HATCH_PATTERNS:
        raise ValueError(f"A bar hatch must be a string from {BAR_HATCH_PATTERNS!r}.")
    if pattern in _CUSTOM_PATHS:
        return {"shape": None, "solidity": None, "path": _CUSTOM_PATHS[pattern], "size": 8}
    return {"shape": pattern, "path": None}
