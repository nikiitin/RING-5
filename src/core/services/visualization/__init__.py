"""Visualization services — config resolution, palette lookup, interaction.

This package centralizes all visualization-related business logic that was
previously scattered across the models layer (violating P2).

Modules:
    config_resolver — Sentinel resolution for ``FigureConfig`` trees.
    palette_service — Palette lookup, ordering, colorblind-safe filtering.
    plot_interaction — Relayout event processing, item ordering.
"""

from src.core.services.visualization.config_resolver import (  # noqa: F401
    resolve_config,
)
from src.core.services.visualization.palette_service import (  # noqa: F401
    get_palette_names,
    is_colorblind_safe,
    resolve_palette,
)
from src.core.services.visualization.plot_interaction import (  # noqa: F401
    resolve_item_order,
    try_float,
    try_float_edit,
    update_config_from_relayout,
)
