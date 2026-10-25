"""Type-specific series controls used by the Colors settings component."""

from typing import Any

from src.web.state.ui_state_manager import WidgetKeyBuilder


class BaseStyleUI:
    """Provide the series-visual extension hook for registered plot strategies."""

    def __init__(self, plot_id: int, plot_type: str) -> None:
        self.plot_id = plot_id
        self.plot_type = plot_type

    def render_series_visuals(self, current_style: dict[str, Any], key_suffix: str) -> None:
        # [impl->req~ring5.figure.series-styling~1]
        """Render type-specific series controls in the active Colors panel."""
        self._render_specific_series_visuals(
            current_style,
            key_suffix,
            key_prefix=f"{WidgetKeyBuilder.plot_key(self.plot_id, 'series')}.",
        )

    def _render_specific_series_visuals(
        self, current_style: dict[str, Any], key_suffix: str, key_prefix: str = ""
    ) -> None:
        """Hook for subclasses to render specific style options."""
