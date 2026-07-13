"""Public, engine-agnostic grouped-bar geometry.

Plot decorations (over-cap value labels, callout arrows, …) need the x-positions of the
individual sub-bars. Those are computed by RING-5's internal ``GroupedBarUtils``; this
module is the supported public entry point so scripts don't import ``src.*``::

    from ring5 import grouped_bar_coordinates
    coords = grouped_bar_coordinates(categories, groups, config)
    x = coords["coord_map"][(category, group)]

The returned dict is plain data (no engine objects): ``coord_map`` (``{(cat, grp): x}``),
``tick_vals``/``tick_text``, ``cat_centers``, ``category_group_centers``,
``category_group_rules``, ``separator_lines``, ``shaded_regions``, ``bar_width``.
"""

from __future__ import annotations

from typing import Any

from src.web.pages.ui.plotting.utils import GroupedBarUtils


def grouped_bar_coordinates(
    categories: list[str],
    groups: list[str],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Compute sub-bar coordinates + layout geometry for a grouped(-stacked) bar figure.

    Args:
        categories: ordered major-axis categories (the ``x_order``).
        groups: ordered minor groups within each category (the ``group_order``).
        config: the flat plot config (``spec.to_config()``) — reads ``bargap``,
            ``bargroupgap``, ``isolate_last_group``, ``isolation_gap``, separators, etc.

    Returns:
        The geometry dict described in the module docstring (``coord_map`` is the field
        most callers want).
    """
    return GroupedBarUtils.calculate_grouped_coordinates(categories, groups, config)
