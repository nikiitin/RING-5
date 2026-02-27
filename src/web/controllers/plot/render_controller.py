"""
Plot Render Controller — orchestrates config gathering, figure generation, display.

Handles:
    - Gathering config from plot's render methods (inline)
    - Detecting config changes
    - Figure generation and caching
    - Delegating chart display to ChartDisplayComponent
    - Plot type changes via PlotLifecycleService

Dependencies are injected via protocols (no concrete imports from pages.ui).

Architecture Note — Streamlit usage:
    This controller uses ``st.rerun()`` after plot type changes and relayout
    events (flow control) and ``st.exception()`` for config rendering errors.
    All chart display (engine selector, chart rendering, download) is
    delegated to ``ChartDisplayComponent``.
"""

import hashlib
import json
import logging
from typing import Any, cast

import pandas as pd
import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.performance import get_plot_cache
from src.web.components.common.chart_display import ChartDisplayComponent
from src.web.models.plot_protocols import (
    PlotLifecycleService,
    PlotTypeRegistry,
    RenderablePlot,
)
from src.web.pages.ui.plotting.settings_pills import render_settings_pills
from src.web.rendering.engine_manager import EngineManager, EngineMode
from src.web.state.ui_state_manager import UIStateManager

logger = logging.getLogger(__name__)


class PlotRenderController:
    """
    Orchestrates the visualization section: config → generation → display.

    Single Responsibility: turning plot config + data into a rendered chart.
    Does NOT handle pipeline editing or plot lifecycle.

    Architecture:
        - Config gathered inline (type-specific + advanced + theme)
        - Controller owns figure generation + caching
        - ChartDisplayComponent renders engine selector, chart display, and downloads
        - PlotLifecycleService handles plot type changes

    Dependencies are injected via protocols — no concrete imports from
    ``pages.ui.plotting.*``.
    """

    def __init__(
        self,
        api: ApplicationAPI,
        ui_state: UIStateManager,
        lifecycle: PlotLifecycleService,
        registry: PlotTypeRegistry,
    ) -> None:
        """
        Initialize with dependency injection.

        Args:
            api: Application API for domain operations.
            ui_state: UI state manager for transient state.
            lifecycle: Plot lifecycle service (for type changes).
            registry: Plot type registry (available types).
        """
        self._api: ApplicationAPI = api
        self._ui: UIStateManager = ui_state
        self._lifecycle: PlotLifecycleService = lifecycle
        self._registry: PlotTypeRegistry = registry

    def render(self, plot: RenderablePlot) -> None:
        """
        Render the full visualization section for a plot.

        Steps:
            1. Guard: check processed data exists
            2. Plot type selector (inline)
            3. Type-specific config (via plot.render_config_ui)
            4. Advanced + theme config (inline)
            5. Detect config changes
            6. Refresh controls (via ChartDisplayComponent)
            7. Figure generation + caching (direct)
            8. Engine selector + chart display (via ChartDisplayComponent)

        Args:
            plot: The plot to render (must satisfy both PlotHandle
                  and ConfigRenderer protocols).
        """
        if plot.processed_data is None:
            st.warning("No processed data available.")
            return

        st.markdown("### Visualization")
        st.markdown("---")
        st.markdown("### Plot Configuration")
        saved_config: dict[str, Any] = plot.config
        current_config: dict[str, Any] = saved_config.copy()
        config_error: bool = False

        # 1. Plot type selector (inline)
        available_types: list[str] = self._registry.get_available_types()
        new_type: str | None = st.selectbox(
            "Plot Type",
            options=available_types,
            index=(
                available_types.index(plot.plot_type) if plot.plot_type in available_types else 0
            ),
            key=f"plot_type_sel_{plot.plot_id}",
        )
        type_changed: bool = new_type is not None and new_type != plot.plot_type

        if type_changed and new_type is not None:
            self._lifecycle.change_plot_type(plot, new_type, self._api.state_manager)
            st.rerun()

        # 2. Type-specific config (via plot.render_config_ui)
        data: pd.DataFrame = plot.processed_data
        # plot satisfies RenderablePlot (PlotHandle + ConfigRenderer)
        try:
            ui_config: dict[str, Any] = plot.render_config_ui(data, saved_config)
            current_config.update(ui_config)
        except Exception as e:
            st.exception(e)
            logger.error(
                "RENDER: Type config failed for plot %r: %s",
                str(plot.name).replace("\n", ""),
                e,
                exc_info=True,
            )
            config_error = True

        # 3. Advanced & Theme (inline)
        try:
            show_adv: bool = st.toggle(
                "Show advanced settings",
                value=False,
                key=f"show_advanced_{plot.plot_id}",
            )
            selected_section: str | None = render_settings_pills(show_advanced=show_adv)
            extra_config: dict[str, Any] = plot.render_settings_section(
                selected_section, current_config, data
            )
            current_config.update(extra_config)
        except Exception as e:
            st.exception(e)
            logger.error(
                "RENDER: Advanced config failed for plot %r: %s",
                str(plot.name).replace("\n", ""),
                e,
                exc_info=True,
            )
            config_error = True

        # 4. Refresh logic (via ChartDisplayComponent)
        config_changed: bool = current_config != saved_config
        auto_refresh: bool = self._ui.plot.get_auto_refresh(plot.plot_id)

        controls = ChartDisplayComponent.render_refresh_controls(
            plot_id=plot.plot_id,
            auto_refresh=auto_refresh,
            config_changed=config_changed,
        )

        # Update auto-refresh in UI state
        self._ui.plot.set_auto_refresh(plot.plot_id, controls["auto_refresh"])

        should_gen: bool = controls["should_generate"] and not config_error
        plot.config = current_config

        # 5. Figure generation, caching, and chart display
        self._render_visualization(plot, should_gen)

    # ── Private helpers ──────────────────────────────────────────

    def _render_visualization(self, plot: RenderablePlot, should_generate: bool) -> None:
        """
        Generate figure (with caching) and delegate display to component.

        This method owns the figure lifecycle:
            1. Cache check (skip regeneration if config/data unchanged)
            2. Figure generation via ``FigureEngine``
            3. Engine selector via ``ChartDisplayComponent``
            4. Chart display via ``ChartDisplayComponent`` (Plotly or Matplotlib)
            5. Relayout handling for Plotly interactive charts

        Args:
            plot: The plot instance (``BasePlot`` at runtime).
            should_generate: Whether to force figure regeneration.
        """
        if plot.processed_data is None:
            return

        # ── Cache check ──────────────────────────────────────────
        data_hash: str = self._compute_data_hash(plot.processed_data)
        cache_key: str = self._compute_figure_cache_key(plot.plot_id, plot.config, data_hash)
        cache = get_plot_cache()

        if not should_generate and plot.last_generated_fig is None:
            cached_fig = cache.get(cache_key)
            if cached_fig is not None:
                plot.last_generated_fig = cached_fig

        # ── Generate figure if needed ────────────────────────────
        if should_generate or plot.last_generated_fig is None:
            try:
                fig = plot.create_figure(plot.processed_data, plot.config)
                fig = plot.apply_common_layout(fig, plot.config)
                legend_labels: dict[str, str] | None = plot.config.get("legend_labels")
                if legend_labels:
                    fig.for_each_trace(
                        lambda t: t.update(  # type: ignore[attr-defined]
                            name=legend_labels.get(t.name, t.name)  # type: ignore[attr-defined]
                        )
                    )
                plot.last_generated_fig = fig
                cache.set(cache_key, fig)
            except Exception as e:
                ChartDisplayComponent.render_error(e)
                return

        # ── Display ──────────────────────────────────────────────
        fig = plot.last_generated_fig
        if fig is None:  # type: ignore[redundant-expr]
            return

        # Engine selector (component renders st.pills)
        engine_choice: str | None = ChartDisplayComponent.render_engine_selector(
            plot.plot_id, EngineManager.get_engine()
        )
        if engine_choice is not None:
            EngineManager.set_engine(cast("EngineMode", engine_choice))

        # Branch on engine mode
        try:
            if EngineManager.is_matplotlib():
                # Use pre-computed traces when available (B7 forward path)
                _traces_result = plot.last_traces
                pre_traces = list(_traces_result.traces) if _traces_result is not None else None
                ChartDisplayComponent.render_matplotlib_chart(
                    fig,
                    plot.plot_id,
                    plot.name,
                    plot.config,
                    plot.plot_type,
                    traces=pre_traces,
                )
            else:
                relayout_data = ChartDisplayComponent.render_plotly_chart(
                    fig,
                    plot.plot_id,
                    plot.name,
                    plot.config,
                )
                # Handle relayout events (zoom, pan, legend drag)
                if relayout_data:
                    last_event_key = f"plot.{plot.plot_id}.last_relayout"
                    last_event = st.session_state.get(last_event_key)
                    if relayout_data != last_event:
                        if plot.update_from_relayout(relayout_data):
                            st.session_state[last_event_key] = relayout_data
                            st.rerun()
        except Exception as e:
            ChartDisplayComponent.render_error(e)

    @staticmethod
    def _compute_figure_cache_key(plot_id: int, config: dict[str, Any], data_hash: str) -> str:
        """
        Compute stable cache key for plot figure.

        Uses config hash + data hash to detect when regeneration is needed.
        Ignores transient UI state (legend positions, zoom/pan).

        Args:
            plot_id: Unique plot identifier.
            config: Plot configuration dict.
            data_hash: Hash of the processed data.

        Returns:
            Cache key string.
        """
        cache_relevant_config = {
            k: v for k, v in config.items() if k not in {"xaxis_range", "yaxis_range"}
        }
        config_json = json.dumps(cache_relevant_config, sort_keys=True, default=str)
        config_hash = hashlib.md5(config_json.encode(), usedforsecurity=False).hexdigest()[:8]
        return f"plot_{plot_id}_{config_hash}_{data_hash}"

    @staticmethod
    def _compute_data_hash(data: pd.DataFrame) -> str:
        """
        Compute fast hash of DataFrame for cache invalidation.

        Uses shape + first/last row hashes for speed.

        Args:
            data: DataFrame to hash.

        Returns:
            Hash string.
        """
        shape_str = f"{data.shape[0]}x{data.shape[1]}"

        if len(data) > 0:
            first_row = str(data.iloc[0].values.tolist())
            last_row = str(data.iloc[-1].values.tolist())
            columns = str(data.columns.tolist())
            content = f"{shape_str}|{columns}|{first_row}|{last_row}"
        else:
            content = shape_str

        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:12]
