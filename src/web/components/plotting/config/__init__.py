"""Per-plot-type configuration components.

Each module exposes a ``render(data, saved_config, plot_id)`` function that
renders the Streamlit widgets for its plot type and returns a typed config dict.

Shared utilities live in :mod:`base_plot_config`.
"""

from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
    render_color_selector,
    render_common_config,
    render_common_with_color,
    render_xy_selectors,
)

__all__ = [
    "detect_column_types",
    "render_color_selector",
    "render_common_config",
    "render_common_with_color",
    "render_xy_selectors",
]
