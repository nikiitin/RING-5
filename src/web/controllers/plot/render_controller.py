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
from copy import deepcopy
from collections.abc import Mapping
from typing import Any, cast

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models.visualization.engine import EngineMode
from src.web.components.common.chart_display import ChartDisplayComponent
from src.web.components.plotting.drill_down_panel import DrillDownPanel, point_label
from src.web.models.plot_models import PlotConfig
from src.web.models.plot_protocols import (
    PlotLifecycleService,
    PlotTypeRegistry,
    RenderablePlot,
)
from src.web.pages.ui.plotting.settings_pills import render_settings_pills
from src.web.rendering.engine_manager import EngineManager
from src.web.rendering.small_multiples_builder import render_small_multiples
from src.web.state.ui_state_manager import UIStateManager

logger = logging.getLogger(__name__)


def _drill_down_key(plot_id: int, suffix: str) -> str:
    """Return a plot-scoped key for transient drill-down browser state."""
    return f"plot.{plot_id}.drill_down.{suffix}"


def _supports_drill_down(figure: go.Figure) -> bool:
    """Return whether any trace carries point-aligned source filters."""
    for trace in figure.data:
        meta = getattr(trace, "meta", None)
        if isinstance(meta, Mapping) and isinstance(meta.get("ring5_drilldown"), list):
            return True
    return False


class PlotRenderController:
    """Gather configuration, generate figures, and render the active plot.

    Pipeline editing and plot lifecycle operations are handled by their own
    controllers. Rendering dependencies are injected through protocols.
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
        # [impl->req~ring5.plots.change-type~1]
        # [impl->req~ring5.plots.refresh-cache~1]
        # [impl->req~ring5.figure.theme-presets~1]
        if plot.processed_data is None:
            st.warning("No processed data available.")
            return

        st.markdown("### Visualization")
        st.markdown("---")
        st.markdown("### Plot Configuration")
        saved_config: PlotConfig = plot.config
        # Deep copy so no settings component can mutate the live persisted
        # config in place; edits are detected via ``current_config != saved_config``.
        current_config: PlotConfig = deepcopy(saved_config)
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
        type_changed: bool = (
            isinstance(new_type, str) and new_type in available_types and new_type != plot.plot_type
        )

        if type_changed and new_type is not None:
            self._lifecycle.change_plot_type(plot, new_type, self._api.state_manager)
            st.rerun()
            return

        # 2. Type-specific config (via plot.render_config_ui)
        data: pd.DataFrame = plot.processed_data
        # plot satisfies RenderablePlot (PlotHandle + ConfigRenderer)
        try:
            ui_config: PlotConfig = plot.render_config_ui(data, saved_config)
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
        refresh_requested = False
        try:
            show_adv: bool = st.toggle(
                "Show advanced settings",
                value=False,
                key=f"show_advanced_{plot.plot_id}",
            )
            selected_section: str | None = render_settings_pills(show_advanced=show_adv)
            extra_config: PlotConfig = plot.render_settings_section(
                selected_section, current_config, data
            )
            refresh_requested = bool(extra_config.pop("_ring5_request_refresh", False))
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

        # Publication preset selection was removed from plot configuration.
        current_config.pop("preset_applied", None)

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

        should_gen: bool = (controls["should_generate"] or refresh_requested) and not config_error
        # With auto-refresh disabled, keep the persisted config paired with the
        # visible figure until the user explicitly refreshes. Widget values
        # remain in Streamlit state and are gathered again on that refresh.
        if not config_error and (should_gen or plot.last_generated_fig is None):
            plot.config = current_config

        # 5. Figure generation, caching, and chart display
        self._render_visualization(plot, should_gen)

    # Private helpers
    def _render_visualization(self, plot: RenderablePlot, should_generate: bool) -> None:
        # [impl->req~ring5.render.engine-selection~1]
        # [impl->req~ring5.plots.drill-down~1]
        # [impl->req~ring5.plots.small-multiples~1]
        """
        Generate figure (with caching) and delegate display to component.

        This method owns the figure lifecycle:
            1. Engine selection and state reconciliation
            2. Cache check (skip regeneration if config/data unchanged)
            3. Figure generation through the plot model
            4. Chart display via ``ChartDisplayComponent`` (Plotly or Matplotlib)
            5. Relayout handling for Plotly interactive charts

        Args:
            plot: The plot instance (``BasePlot`` at runtime).
            should_generate: Whether to force figure regeneration.
        """
        # [impl->req~ring5.plots.refresh-cache~1]
        if plot.processed_data is None:
            return

        # The engine is part of the render identity. Select it before deciding
        # whether the existing figure can be reused.
        current_engine = EngineManager.get_engine()
        engine_choice: str | None = ChartDisplayComponent.render_engine_selector(
            plot.plot_id, current_engine
        )
        active_engine = current_engine
        if engine_choice is not None:
            active_engine = cast("EngineMode", engine_choice)
            if active_engine != current_engine:
                EngineManager.set_engine(active_engine)
                # Rebuild the selector from the persisted engine before
                # rendering so the control and chart cannot disagree.
                st.rerun()
                return

        # Cache identity
        data_hash: str = self._compute_data_hash(plot.processed_data)
        cache_key: str = self._compute_figure_cache_key(
            plot.plot_id,
            plot.config,
            data_hash,
            active_engine,
        )
        cache_matches = (
            plot.last_generated_fig is not None and plot.last_figure_cache_key == cache_key
        )

        multiples_spec = None
        if plot.config.get("small_multiples_enabled"):
            facet_columns = plot.config.get("small_multiples_by", [])
            if isinstance(facet_columns, list) and facet_columns:
                try:
                    panel_columns = int(plot.config.get("small_multiples_columns", 3))
                    multiples_spec = self._api.create_small_multiples(
                        plot.plot_id,
                        facet_columns,
                        columns=panel_columns,
                        width=max(int(plot.config.get("width", 800)), panel_columns * 360),
                        panel_height=int(plot.config.get("small_multiples_panel_height", 320)),
                        shared_xaxes=bool(plot.config.get("small_multiples_shared_xaxes", True)),
                        shared_yaxes=bool(plot.config.get("small_multiples_shared_yaxes", True)),
                        shared_legend=bool(plot.config.get("small_multiples_shared_legend", True)),
                    )
                except (TypeError, ValueError) as exc:
                    ChartDisplayComponent.render_error(exc)
                    return

        # Generate figure if needed
        if should_generate or not cache_matches:
            try:
                # create_figure relabels legend names engine-agnostically
                # (on TraceConfig.name), so both engines stay consistent — no
                # Plotly-only for_each_trace pass here.
                if multiples_spec is not None:
                    fig = cast(
                        go.Figure,
                        render_small_multiples([cast(Any, plot)], multiples_spec, engine="plotly"),
                    )
                else:
                    fig = plot.create_figure(plot.processed_data, plot.config)
                    fig = plot.apply_common_layout(fig, plot.config)
                plot.last_generated_fig = fig
                plot.last_figure_cache_key = cache_key
            except Exception as e:
                ChartDisplayComponent.render_error(e)
                return

        # Display
        display_fig = plot.last_generated_fig
        if display_fig is None:
            return

        # Branch on engine mode
        try:
            if active_engine == "matplotlib":
                if multiples_spec is not None:
                    mpl_fig = render_small_multiples(
                        [cast(Any, plot)], multiples_spec, engine="matplotlib"
                    )
                    ChartDisplayComponent.render_prebuilt_matplotlib_chart(
                        mpl_fig,
                        display_fig,
                        plot.plot_id,
                        plot.name,
                    )
                    return
                # Reuse traces computed during plot generation when available.
                _traces_result = plot.last_traces
                pre_traces = list(_traces_result.traces) if _traces_result is not None else None
                sep_lines = list(_traces_result.separator_lines) if _traces_result else None
                shades = list(_traces_result.shaded_regions) if _traces_result else None
                rules = list(_traces_result.rule_lines) if _traces_result else None
                ChartDisplayComponent.render_matplotlib_chart(
                    display_fig,
                    plot.plot_id,
                    plot.name,
                    plot.config,
                    plot.plot_type,
                    traces=pre_traces,
                    separator_lines=sep_lines,
                    shaded_regions=shades,
                    rule_lines=rules,
                )
            else:
                drill_enabled = False
                generation_key = _drill_down_key(plot.plot_id, "generation")
                generation = int(st.session_state.get(generation_key, 0))
                result_key = _drill_down_key(plot.plot_id, "result")
                event_key = _drill_down_key(plot.plot_id, "last_event")

                if _supports_drill_down(display_fig):
                    drill_enabled = DrillDownPanel.render_toggle(plot.plot_id)
                stored = st.session_state.get(result_key)
                if isinstance(stored, dict) and stored.get("cache_key") != cache_key:
                    st.session_state.pop(result_key, None)
                    st.session_state.pop(event_key, None)
                    generation += 1
                    st.session_state[generation_key] = generation
                    stored = None
                if not drill_enabled and stored is not None:
                    st.session_state.pop(result_key, None)
                    st.session_state.pop(event_key, None)
                    generation += 1
                    st.session_state[generation_key] = generation
                    stored = None

                interaction_data = ChartDisplayComponent.render_plotly_chart(
                    display_fig,
                    plot.plot_id,
                    plot.name,
                    plot.config,
                    plot.processed_data,
                    capture_click=drill_enabled,
                    component_generation=generation,
                )
                if (
                    drill_enabled
                    and interaction_data
                    and interaction_data.get("kind") == "drill_down"
                ):
                    last_event = st.session_state.get(event_key)
                    if interaction_data != last_event:
                        filters = interaction_data.get("filters")
                        if isinstance(filters, Mapping):
                            st.session_state[event_key] = interaction_data
                            try:
                                result = self._api.drill_down_plot(plot.plot_id, filters)
                            except (TypeError, ValueError) as exc:
                                DrillDownPanel.render_error(exc)
                            else:
                                st.session_state[result_key] = {
                                    "cache_key": cache_key,
                                    "point_label": point_label(interaction_data),
                                    "result": result,
                                }
                                st.rerun()
                                return
                # Handle relayout events (zoom, pan, legend drag)
                elif interaction_data:
                    last_event_key = f"plot.{plot.plot_id}.last_relayout"
                    last_event = st.session_state.get(last_event_key)
                    if interaction_data != last_event:
                        if plot.update_from_relayout(interaction_data):
                            st.session_state[last_event_key] = interaction_data
                            st.rerun()

                stored = st.session_state.get(result_key)
                if isinstance(stored, dict) and stored.get("cache_key") == cache_key:
                    stored_result = stored.get("result")
                    if stored_result is not None and DrillDownPanel.render_result(
                        stored_result, str(stored.get("point_label", ""))
                    ):
                        st.session_state.pop(result_key, None)
                        st.session_state.pop(event_key, None)
                        st.session_state[generation_key] = generation + 1
                        st.rerun()
        except Exception as e:
            ChartDisplayComponent.render_error(e)

    @staticmethod
    def _compute_figure_cache_key(
        plot_id: int,
        config: PlotConfig,
        data_hash: str,
        engine: EngineMode = "plotly",
    ) -> str:
        """
        Compute stable cache key for plot figure.

        Uses config hash + data hash to detect when regeneration is needed.
        Ignores transient UI state (legend positions, zoom/pan).

        Args:
            plot_id: Unique plot identifier.
            config: Plot configuration dict.
            data_hash: Hash of the processed data.
            engine: Active rendering engine.

        Returns:
            Cache key string.
        """
        # [impl->req~ring5.plots.independent-state~1]
        cache_relevant_config = {
            k: v for k, v in config.items() if k not in {"xaxis_range", "yaxis_range"}
        }
        config_json = json.dumps(cache_relevant_config, sort_keys=True, default=str)
        config_hash = hashlib.md5(config_json.encode(), usedforsecurity=False).hexdigest()[:8]
        return f"plot_{plot_id}_{engine}_{config_hash}_{data_hash}"

    @staticmethod
    def _compute_data_hash(data: pd.DataFrame) -> str:
        """
        Compute a full-content hash of a DataFrame for cache invalidation.

        Args:
            data: DataFrame to hash.

        Returns:
            Hash string.
        """
        schema = json.dumps(
            {
                "shape": data.shape,
                "columns": [str(column) for column in data.columns],
                "dtypes": [str(dtype) for dtype in data.dtypes],
            },
            sort_keys=True,
        ).encode()
        digest = hashlib.md5(schema, usedforsecurity=False)
        try:
            row_hashes = pd.util.hash_pandas_object(data, index=True)
            digest.update(row_hashes.to_numpy().tobytes())
        except (TypeError, ValueError):
            # Object columns may contain unhashable containers. JSON provides
            # a deterministic fallback while still inspecting every value.
            serialized = data.to_json(
                orient="split",
                date_format="iso",
                default_handler=str,
            )
            digest.update(serialized.encode())
        return digest.hexdigest()[:12]
