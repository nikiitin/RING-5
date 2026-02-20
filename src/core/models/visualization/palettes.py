"""
Unified palette registry — single source of truth for all color palettes.

All palettes are stored as pre-resolved ``List[str]`` of hex colors.
This module replaces the three disconnected palette systems that
previously existed in ``base_plot.BUILTIN_PALETTES``,
``builders._resolve_palette()``, and ``colors.get_palette_colors()``.

Usage::

    from src.core.models.visualization.palettes import resolve_palette, get_palette_names

    colors = resolve_palette("wong")       # List[str] of hex
    names  = get_palette_names()           # colorblind-safe first
"""

from __future__ import annotations

from typing import Dict, List

# ────────────────────────────────────────────────────────────────────
# Colorblind-safe palettes  (listed first in get_palette_names)
# ────────────────────────────────────────────────────────────────────

_COLORBLIND_PALETTES: Dict[str, List[str]] = {
    "wong": [
        "#000000",
        "#E69F00",
        "#56B4E9",
        "#009E73",
        "#F0E442",
        "#0072B2",
        "#D55E00",
        "#CC79A7",
    ],
    "okabe_ito": [
        "#E69F00",
        "#56B4E9",
        "#009E73",
        "#F0E442",
        "#0072B2",
        "#D55E00",
        "#CC79A7",
        "#000000",
    ],
    "tol_bright": [
        "#4477AA",
        "#EE6677",
        "#228833",
        "#CCBB44",
        "#66CCEE",
        "#AA3377",
        "#BBBBBB",
    ],
    "viridis_8": [
        "#440154",
        "#482878",
        "#3E4A89",
        "#31688E",
        "#26838E",
        "#1F9E89",
        "#6DCD59",
        "#FDE725",
    ],
    "seaborn_cb": [
        "#0173B2",
        "#DE8F05",
        "#029E73",
        "#D55E00",
        "#CC78BC",
        "#CA9161",
        "#FBAFE4",
        "#949494",
    ],
}


# ────────────────────────────────────────────────────────────────────
# Plotly qualitative palettes  (resolved to hex at module load)
# ────────────────────────────────────────────────────────────────────

_PLOTLY_PALETTES: Dict[str, List[str]] = {
    "Plotly": [
        "#636EFA",
        "#EF553B",
        "#00CC96",
        "#AB63FA",
        "#FFA15A",
        "#19D3F3",
        "#FF6692",
        "#B6E880",
        "#FF97FF",
        "#FECB52",
    ],
    "D3": [
        "#1F77B4",
        "#FF7F0E",
        "#2CA02C",
        "#D62728",
        "#9467BD",
        "#8C564B",
        "#E377C2",
        "#7F7F7F",
        "#BCBD22",
        "#17BECF",
    ],
    "G10": [
        "#3366CC",
        "#DC3912",
        "#FF9900",
        "#109618",
        "#990099",
        "#0099C6",
        "#DD4477",
        "#66AA00",
        "#B82E2E",
        "#316395",
    ],
    "T10": [
        "#4C78A8",
        "#F58518",
        "#E45756",
        "#72B7B2",
        "#54A24B",
        "#EECA3B",
        "#B279A2",
        "#FF9DA6",
        "#9D755D",
        "#BAB0AC",
    ],
    "Alphabet": [
        "#AA0DFE",
        "#3283FE",
        "#85660D",
        "#782AB6",
        "#565656",
        "#1C8356",
        "#16FF32",
        "#F7E1A0",
        "#E2E2E2",
        "#1CBE4F",
        "#C4451C",
        "#DEA0FD",
        "#FE00FA",
        "#325A9B",
        "#FEAF16",
        "#F8A19F",
        "#90AD1C",
        "#F6222E",
        "#1CFFCE",
        "#2ED9FF",
        "#B10DA1",
        "#C075A6",
        "#FC1CBF",
        "#B00068",
        "#FBE426",
        "#FA0087",
    ],
    "Dark24": [
        "#2E91E5",
        "#E15F99",
        "#1CA71C",
        "#FB0D0D",
        "#DA16FF",
        "#222A2A",
        "#B68100",
        "#750D86",
        "#EB663B",
        "#511CFB",
        "#00A08B",
        "#FB00D1",
        "#FC0080",
        "#B2828D",
        "#6C7C32",
        "#778AAE",
        "#862A16",
        "#A777F1",
        "#620042",
        "#1616A7",
        "#DA60CA",
        "#6C4516",
        "#0D2A63",
        "#AF0038",
    ],
    "Light24": [
        "#FD3216",
        "#00FE35",
        "#6A76FC",
        "#FED4C4",
        "#FE00CE",
        "#0DF9FF",
        "#F6F926",
        "#FF9616",
        "#479B55",
        "#EEA6FB",
        "#DC587D",
        "#D626FF",
        "#6E899C",
        "#00B5F7",
        "#B68E00",
        "#C9FBE5",
        "#FF0092",
        "#22FFA7",
        "#E3EE9E",
        "#86CE00",
        "#BC7196",
        "#7E7DCD",
        "#FC6955",
        "#E48F72",
    ],
    "Set1": [
        "#e41a1c",
        "#377eb8",
        "#4daf4a",
        "#984ea3",
        "#ff7f00",
        "#ffff33",
        "#a65628",
        "#f781bf",
        "#999999",
    ],
    "Set2": [
        "#66c2a5",
        "#fc8d62",
        "#8da0cb",
        "#e78ac3",
        "#a6d854",
        "#ffd92f",
        "#e5c494",
        "#b3b3b3",
    ],
    "Set3": [
        "#8dd3c7",
        "#ffffb3",
        "#bebada",
        "#fb8072",
        "#80b1d3",
        "#fdb462",
        "#b3de69",
        "#fccde5",
        "#d9d9d9",
        "#bc80bd",
        "#ccebc5",
        "#ffed6f",
    ],
    "Pastel": [
        "#66c5cc",
        "#f6cf71",
        "#f89c74",
        "#dcb0f2",
        "#87c55f",
        "#9eb9f3",
        "#fe88b1",
        "#c9db74",
        "#8be0a4",
        "#b497e7",
        "#b3b3b3",
    ],
    "Safe": [
        "#88ccee",
        "#cc6677",
        "#ddcc77",
        "#117733",
        "#332288",
        "#aa4499",
        "#44aa99",
        "#999933",
        "#882255",
        "#661100",
        "#888888",
    ],
    "Vivid": [
        "#e58606",
        "#5d69b1",
        "#52bca3",
        "#99c945",
        "#cc61b0",
        "#24796c",
        "#daa51b",
        "#2f8ac4",
        "#764e9f",
        "#ed645a",
        "#a5aa99",
    ],
    "Bold": [
        "#7f3c8d",
        "#11a579",
        "#3969ac",
        "#f2b701",
        "#e73f74",
        "#80ba5a",
        "#e68310",
        "#008695",
        "#cf1c90",
        "#f97b72",
        "#a5aa99",
    ],
}


# ────────────────────────────────────────────────────────────────────
# Combined registry
# ────────────────────────────────────────────────────────────────────

PALETTE_REGISTRY: Dict[str, List[str]] = {
    **_COLORBLIND_PALETTES,
    **_PLOTLY_PALETTES,
}

# Ordered list: colorblind-safe first, then Plotly alphabetical
_PALETTE_ORDER: List[str] = list(_COLORBLIND_PALETTES.keys()) + sorted(_PLOTLY_PALETTES.keys())


def resolve_palette(name: object) -> List[str]:
    """Resolve a palette name to a list of hex color strings.

    Falls back to the Wong colorblind-safe palette when *name* is
    ``None``, empty, or not found in the registry.

    Args:
        name: Palette name (string) or ``None``.

    Returns:
        A **copy** of the hex color list (safe to mutate).
    """
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


def get_palette_names() -> List[str]:
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
