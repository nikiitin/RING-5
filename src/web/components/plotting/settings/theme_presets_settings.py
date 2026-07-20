"""Human-first figure-theme presets, customization, and JSON exchange."""

from __future__ import annotations

import streamlit as st

from src.core.models.figure_theme_models import FigureThemeContext
from src.core.services.visualization.figure_theme_service import FigureThemeService
from src.web.models.plot_models import PlotConfig


class ThemePresetsSettingsComponent:
    """Apply built-ins and exchange the appearance subset of a plot config."""

    def __init__(self, plot_id: int, plot_type: str) -> None:
        self.plot_id = plot_id
        self.plot_type = plot_type

    def render(self, saved_config: PlotConfig) -> PlotConfig:
        """Render apply, import, and export controls for coherent figure themes."""
        # [impl->req~ring5.figure.theme-presets~1]
        st.markdown("#### Figure Theme")
        active_name = saved_config.get("figure_theme_name")
        if active_name:
            st.info(f"Active theme: {active_name}. Further settings are customizations.")
        themes = FigureThemeService.available_themes()
        by_id = {theme.identifier: theme for theme in themes}
        options = list(by_id)
        saved_identifier = str(saved_config.get("figure_theme_id", "paper"))
        selected_default = saved_identifier if saved_identifier in by_id else "paper"
        selected = st.selectbox(
            "Theme preset",
            options,
            index=options.index(selected_default),
            format_func=lambda identifier: by_id[identifier].name,
            key=f"figure_theme_select_{self.plot_id}",
            help="Apply a complete appearance profile without changing data columns or filters.",
        )
        selected = selected or "paper"
        theme = by_id[selected]
        st.caption(theme.description)
        st.markdown(
            f"**Context:** {theme.context.title()}  ·  "
            f"**Canvas:** {theme.config['width']} × {theme.config['height']} px"
        )

        applied: PlotConfig = {}
        if st.button(
            "Apply theme",
            key=f"apply_figure_theme_{self.plot_id}",
            type="primary",
        ):
            self._clear_appearance_widget_state()
            applied = FigureThemeService.apply(saved_config, theme, self.plot_type)
            applied["_ring5_request_refresh"] = True
            st.success(f"Applied {theme.name}. Data mappings and filters were kept.")

        st.info(
            "Customize the applied theme in Layout, Typography, Legends, Axes, and Colors. "
            "Download below captures those appearance settings only."
        )

        st.markdown("#### Import a theme")
        uploaded = st.file_uploader(
            "Theme JSON",
            type=["json"],
            key=f"import_figure_theme_{self.plot_id}",
            help="Imports one RING-5 figure-theme document up to 256 KiB.",
        )
        imported = None
        if uploaded is not None:
            try:
                imported = FigureThemeService.loads(uploaded.getvalue())
                st.success(f"Imported {imported.name}. Review it before applying.")
                st.caption(imported.description)
            except (TypeError, ValueError) as exc:
                st.error(str(exc))
        if imported is not None and st.button(
            "Apply imported theme",
            key=f"apply_imported_figure_theme_{self.plot_id}",
        ):
            self._clear_appearance_widget_state()
            applied = FigureThemeService.apply(saved_config, imported, self.plot_type)
            applied["_ring5_request_refresh"] = True
            st.success(f"Applied imported theme {imported.name}.")

        st.markdown("#### Download the current customization")
        export_name = st.text_input(
            "Theme name",
            value=str(saved_config.get("figure_theme_name", "My figure theme")),
            max_chars=80,
            key=f"export_figure_theme_name_{self.plot_id}",
        )
        source_config = {**saved_config, **applied}
        context_value = source_config.get("figure_theme_context", theme.context)
        context: FigureThemeContext = (
            context_value
            if context_value in {"paper", "presentation", "dashboard", "dark"}
            else theme.context
        )
        try:
            exported_theme = FigureThemeService.from_config(
                export_name,
                source_config,
                context=context,
            )
            st.download_button(
                "Download current theme",
                data=FigureThemeService.dumps(exported_theme),
                file_name=f"{exported_theme.identifier}.ring5-theme.json",
                mime="application/json",
                key=f"export_figure_theme_{self.plot_id}",
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))

        return applied

    def _clear_appearance_widget_state(self) -> None:
        """Discard stale widget values so the applied profile becomes each panel's default."""
        suffix = f"_{self.plot_id}"
        framed = f"_{self.plot_id}_"
        exact_prefixes = (
            "accessible_theme_",
            "col_preset_",
            "hi_",
            "palette_select_",
            "wi_",
            "wi_disabled_",
            "_ring5_accessibility_mode_seen_",
        )
        for key in list(st.session_state):
            if not isinstance(key, str):
                continue
            is_theme_widget = key.startswith("theme_") and (key.endswith(suffix) or framed in key)
            is_exact_widget = key.startswith(exact_prefixes) and key.endswith(suffix)
            if is_theme_widget or is_exact_widget:
                del st.session_state[key]
