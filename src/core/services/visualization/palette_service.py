"""Palette service — lookup and resolution functions for color palettes.

Functions moved from ``src.core.models.visualization.palettes`` (Phase 3.5)
to comply with P2 (models = data only, services = logic).

The palette *data* (``PALETTE_REGISTRY``, ``_COLORBLIND_PALETTES``, etc.)
stays in the models layer.  This module provides the *logic* that
consumers need: resolving names, listing names, checking properties.

Usage::

    from src.core.services.visualization.palette_service import (
        resolve_palette,
        get_palette_names,
        is_colorblind_safe,
    )

    colors = resolve_palette("wong")       # List[str] of hex
    names  = get_palette_names()           # colorblind-safe first
"""

from __future__ import annotations

from src.core.models.visualization.palettes import (
    _COLORBLIND_PALETTES,
    _PALETTE_ORDER,
    PALETTE_REGISTRY,
)


def resolve_palette(name: object) -> list[str]:
    """Resolve a palette to a list of hex color strings.

    Accepts **either** a registry name (string) **or** an explicit sequence of
    color strings (e.g. ``["#66c2a5", "#fc8d62", ...]``), which is returned as a
    cleaned copy. Falls back to the Wong colorblind-safe palette when *name* is
    ``None``, empty, an unknown name, or a sequence with no usable colors.

    Args:
        name: Palette name (string), an explicit list/tuple of color strings,
            or ``None``.

    Returns:
        A **copy** of the hex color list (safe to mutate).
    """
    # Explicit list/tuple of colors -> cleaned copy (passthrough). Checked
    # before the string branch so a custom palette is no longer silently
    # ignored (the previous behaviour fell back to Wong for any non-str).
    if isinstance(name, (list, tuple)):
        colors = [c.strip() for c in name if isinstance(c, str) and c.strip()]
        return colors if colors else list(PALETTE_REGISTRY["wong"])

    if not name or not isinstance(name, str):
        return list(PALETTE_REGISTRY["wong"])

    # Exact match
    if name in PALETTE_REGISTRY:
        return list(PALETTE_REGISTRY[name])

    # Case-insensitive match
    lower = name.lower()
    for key, colors in PALETTE_REGISTRY.items():
        if key.lower() == lower:
            return list(colors)

    return list(PALETTE_REGISTRY["wong"])


def get_palette_names() -> list[str]:
    """Return palette names with colorblind-safe palettes listed first.

    Returns:
        Ordered list of palette name strings.
    """
    return list(_PALETTE_ORDER)


def is_colorblind_safe(name: str) -> bool:
    """Check whether a palette name belongs to the colorblind-safe group.

    Args:
        name: Palette name string.

    Returns:
        ``True`` if the palette is in the colorblind-safe set.
    """
    return name in _COLORBLIND_PALETTES
