"""Visualization services — config resolution, palette lookup, interaction.

This package centralizes all visualization-related business logic that was
previously scattered across the models layer (violating P2).

Modules:
    config_resolver — Sentinel resolution for ``FigureConfig`` trees.
    palette_service — Palette lookup, ordering, colorblind-safe filtering.
    plot_interaction — Item ordering and value-conversion utilities.
"""

from src.core.services.visualization.config_resolver import (  # noqa: F401
    resolve_config,
)
from src.core.services.visualization.accessibility_service import AccessibilityService  # noqa: F401
from src.core.services.visualization.figure_theme_service import FigureThemeService  # noqa: F401
from src.core.services.visualization.drill_down_service import drill_down_rows  # noqa: F401
from src.core.services.visualization.small_multiples_service import (  # noqa: F401
    create_small_multiples_spec,
)
from src.core.services.visualization.plot_transfer_service import (  # noqa: F401
    SETTING_SECTIONS,
    configuration_replacement_reason,
    copy_plot_content,
)
from src.core.services.visualization.plot_configuration_comparison_service import (  # noqa: F401
    compare_plot_configurations,
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
)
