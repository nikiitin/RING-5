"""
Config Presenter — renders plot configuration UI sections.

Wraps the existing BasePlot.render_config_ui/render_advanced_options/
render_theme_options methods in a presenter interface, establishing
the architectural boundary even while the internals are still delegated.

Migration Strategy:
    Phase 1 (current): Delegates to BasePlot methods but presents a clean
    presenter interface to controllers.
    Phase 2 (future): Extract individual config widgets from BasePlot into
    standalone presenter methods, one plot type at a time.
"""

from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from src.web.models.plot_protocols import ConfigRenderer


class ConfigPresenter:
    """
    Renders plot configuration sections.

    Currently delegates to BasePlot methods to preserve existing behavior.
    Controllers call this instead of reaching into BasePlot directly.

    Usage::

        config = ConfigPresenter.render_type_config(plot, data, saved_config)
        config.update(ConfigPresenter.render_advanced(plot, config, data))
        config.update(ConfigPresenter.render_theme(plot, config))
    """

    @staticmethod
    def render_type_config(
        renderer: ConfigRenderer,
        data: pd.DataFrame,
        saved_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Render type-specific configuration widgets.

        Args:
            renderer: Object with render_config_ui method (BasePlot).
            data: Processed DataFrame for column discovery.
            saved_config: Current saved configuration.

        Returns:
            Updated configuration dict from type-specific widgets.
        """
        return renderer.render_config_ui(data, saved_config)

    @staticmethod
    def render_section_headers() -> None:
        """Render section headers for the visualization area."""
        st.markdown("### Visualization")
        st.markdown("---")
        st.markdown("### Plot Configuration")

    @staticmethod
    def render_no_data_warning() -> None:
        """Render warning when no processed data available."""
        st.warning("No processed data available.")

    @staticmethod
    def render_advanced_and_theme(
        renderer: ConfigRenderer,
        current_config: Dict[str, Any],
        data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Render advanced and theme options side by side in columns.

        Args:
            renderer: Object with render_advanced_options/render_theme_options.
            current_config: Current accumulated configuration.
            data: Processed DataFrame.

        Returns:
            Combined advanced + theme configuration dict.
        """
        combined: Dict[str, Any] = {}
        a1, a2 = st.columns(2)
        with a1:
            with st.expander("Advanced Options"):
                advanced: Dict[str, Any] = renderer.render_advanced_options(current_config, data)
                combined.update(advanced)
        with a2:
            with st.expander("Theme & Style"):
                layout: Dict[str, Any] = renderer.render_display_options(current_config)
                combined.update(layout)
                st.markdown("---")
                theme: Dict[str, Any] = renderer.render_theme_options(current_config)
                combined.update(theme)
        return combined

    @staticmethod
    def render_advanced(
        renderer: ConfigRenderer,
        current_config: Dict[str, Any],
        data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Render advanced options inside an expander.

        Args:
            renderer: Object with render_advanced_options method.
            current_config: Current accumulated configuration.
            data: Processed DataFrame.

        Returns:
            Advanced options configuration dict.
        """
        with st.expander("Advanced Options"):
            return renderer.render_advanced_options(current_config, data)

    @staticmethod
    def render_theme(
        renderer: ConfigRenderer,
        current_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Render theme/style options inside an expander.

        Args:
            renderer: Object with render_display_options/render_theme_options.
            current_config: Current accumulated configuration.

        Returns:
            Combined layout + theme configuration dict.
        """
        with st.expander("Theme & Style"):
            layout: Dict[str, Any] = renderer.render_display_options(current_config)
            st.markdown("---")
            theme: Dict[str, Any] = renderer.render_theme_options(current_config)
            combined: Dict[str, Any] = {}
            combined.update(layout)
            combined.update(theme)
            return combined

    @staticmethod
    def render_plot_type_selector(
        plot_type: str,
        available_types: list[str],
        plot_id: int,
    ) -> Dict[str, Any]:
        """
        Render the plot type selector dropdown.

        Args:
            plot_type: Current plot type.
            available_types: Available plot type keys.
            plot_id: Plot ID for widget key.

        Returns:
            Dict with:
                - new_type (Optional[str]): Selected plot type.
                - type_changed (bool): Whether the type changed.
        """
        new_type: Optional[str] = st.selectbox(
            "Plot Type",
            options=available_types,
            index=(available_types.index(plot_type) if plot_type in available_types else 0),
            key=f"plot_type_sel_{plot_id}",
        )

        return {
            "new_type": new_type,
            "type_changed": new_type is not None and new_type != plot_type,
        }
