from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go

from .applicator import StyleApplicator
from .factory import StyleUIFactory


class StyleManager:
    """
    Facade for managing plot styling.
    Delegates to StyleUIFactory (UI) and StyleApplicator (Plotly).
    """

    def __init__(self, plot_id: int, plot_type: str):
        self.plot_id = plot_id
        self.plot_type = plot_type
        # Use Factory to get specific UI strategy
        self.ui_manager = StyleUIFactory.get_strategy(plot_id, plot_type)
        self.applicator = StyleApplicator(plot_type)

    def render_layout_options(self, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render layout options UI."""
        return self.ui_manager.render_layout_options(saved_config)

    def render_style_ui(
        self,
        saved_config: Dict[str, Any],
        data: Optional[pd.DataFrame] = None,
        items: Optional[List[str]] = None,
        key_prefix: str = "",
    ) -> Dict[str, Any]:
        """Render generic style UI."""
        return self.ui_manager.render_style_ui(
            saved_config, data, items=items, key_prefix=key_prefix
        )

    def render_theme_options(
        self,
        saved_config: Dict[str, Any],
        data: Optional[pd.DataFrame] = None,
        items: Optional[List[str]] = None,
        key_prefix: str = "",
    ) -> Dict[str, Any]:
        """Alias for render_style_ui to maintain compatibility with BasePlot."""
        return self.render_style_ui(saved_config, data, items=items, key_prefix=key_prefix)

    def render_series_colors_ui(
        self,
        saved_config: Dict[str, Any],
        data: Optional[pd.DataFrame] = None,
        key_prefix: str = "",
    ) -> Dict[str, Any]:
        """Render series color UI."""
        return self.ui_manager.render_series_colors_ui(saved_config, data, key_prefix=key_prefix)

    def render_series_renaming_ui(
        self,
        saved_config: Dict[str, Any],
        data: Optional[pd.DataFrame] = None,
        items: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Render series renaming UI."""
        # Renaming doesn't usually conflict as it's not reused in the same way, but could add prefix if needed.
        return self.ui_manager.render_series_renaming_ui(saved_config, data, items=items)

    def render_xaxis_labels_ui(
        self,
        saved_config: Dict[str, Any],
        data: Optional[pd.DataFrame] = None,
        key_prefix: str = "xlabel",
    ) -> Dict[str, str]:
        """Render X-axis label UI."""
        return self.ui_manager.render_xaxis_labels_ui(saved_config, data, key_prefix)

    def render_data_labels_ui(
        self,
        saved_config: Dict[str, Any],
        key_prefix: str = "",
    ) -> Dict[str, Any]:
        """Render data labels UI."""
        return self.ui_manager.render_data_labels_ui(saved_config, key_prefix)

    def apply_styles(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
        """Apply styles to figure."""
        return self.applicator.apply_styles(fig, config)

    # Helper proxy if needed directly
    def _get_unique_values(self, saved_config, data, items):
        return self.ui_manager._get_unique_values(saved_config, data, items)
