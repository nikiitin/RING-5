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

import logging
from copy import deepcopy
from dataclasses import replace
from collections.abc import Mapping
from typing import cast

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.web.state.ui_state_manager import WidgetKeyBuilder

from src.core.application_api import ApplicationAPI
from src.core.common.content_identity import content_signature, frame_signature
from src.core.models.visualization.engine import EngineMode
from src.web.components.common.chart_display import ChartDisplayComponent
from src.web.components.plotting.drill_down_panel import DrillDownPanel, point_label
from src.core.models.plot_config import PlotConfig
from src.web.models.plot_protocols import (
    PlotLifecycleService,
    PlotTypeRegistry,
    RenderablePlot,
)
from src.web.pages.ui.plotting.settings_pills import render_settings_pills
from src.web.rendering.engine_manager import EngineManager
from src.web.rendering.plot_renderer import build_render_artifact
from src.web.state.ui_state_manager import UIStateManager

logger = logging.getLogger(__name__)


def _drill_down_key(plot_id: int, suffix: str) -> str:
    """Return a plot-scoped key for transient drill-down browser state."""
    return WidgetKeyBuilder.plot_key(plot_id, f"drill_down.{suffix}")


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
            key=WidgetKeyBuilder.plot_key(plot.plot_id, "widgets.plot_type_sel"),
        )
        type_changed: bool = (
            isinstance(new_type, str) and new_type in available_types and new_type != plot.plot_type
        )

        if type_changed and new_type is not None:
            self._lifecycle.change_plot_type(plot, new_type, self._api.state_manager)
            self._ui.plot.reset_widgets(plot.plot_id)
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
                key=WidgetKeyBuilder.plot_key(plot.plot_id, "widgets.show_advanced"),
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

        # 4. Refresh logic (via ChartDisplayComponent)
        config_changed: bool = current_config != saved_config
        auto_refresh: bool = self._ui.plot.get_auto_refresh(plot.plot_id)

        controls = ChartDisplayComponent.render_refresh_controls(
            plot_id=plot.plot_id,
            auto_refresh=auto_refresh,
            config_changed=config_changed,
        )

        should_gen: bool = (controls["should_generate"] or refresh_requested) and not config_error
        artifact = plot.render_artifact
        effective = (
            current_config
            if not config_error and (should_gen or artifact.figure is None)
            else saved_config
        )
        if artifact.figure is None and config_error:
            return
        self._render_visualization(plot, effective, should_gen)

    # Private helpers
    def _render_visualization(
        self, plot: RenderablePlot, config: PlotConfig, should_generate: bool
    ) -> None:
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
            plot: Registered neutral strategy and artifact owner.
            config: Detached candidate or previously published configuration.
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

        data_hash = self._compute_data_hash(plot.processed_data)
        cache_key = self._compute_figure_cache_key(plot.plot_id, config, data_hash, active_engine)
        artifact = plot.render_artifact
        cache_matches = (
            cache_key is not None
            and artifact.figure is not None
            and artifact.engine == active_engine
            and artifact.cache_key == cache_key
        )
        if should_generate or not cache_matches:
            try:
                multiples_spec = None
                if config.get("small_multiples_enabled"):
                    facet_columns = config.get("small_multiples_by", [])
                    if isinstance(facet_columns, list) and facet_columns:
                        columns = int(config.get("small_multiples_columns", 3))
                        multiples_spec = self._api.create_small_multiples(
                            plot.plot_id,
                            facet_columns,
                            title=str(config.get("title", plot.name)),
                            columns=columns,
                            width=max(int(config.get("width", 800)), columns * 360),
                            panel_height=int(config.get("small_multiples_panel_height", 320)),
                            shared_xaxes=bool(config.get("small_multiples_shared_xaxes", True)),
                            shared_yaxes=bool(config.get("small_multiples_shared_yaxes", True)),
                            shared_legend=bool(config.get("small_multiples_shared_legend", True)),
                        )
                built = build_render_artifact(plot, config, active_engine, multiples=multiples_spec)
                artifact = replace(
                    built,
                    cache_key=self._compute_figure_cache_key(
                        plot.plot_id,
                        built.config,
                        (
                            self._compute_data_hash(built.source_data)
                            if built.source_data is not None
                            else None
                        ),
                        active_engine,
                    ),
                )
                plot.publish_render_artifact(artifact)
            except Exception as exc:
                ChartDisplayComponent.render_error(exc)
                artifact = plot.render_artifact
        display_fig = artifact.figure
        if display_fig is None:
            return
        artifact_generation = artifact.generation

        # Branch on engine mode
        try:
            if artifact.engine == "matplotlib":
                ChartDisplayComponent.render_matplotlib_chart(artifact, plot.plot_id, plot.name)
            else:
                if not isinstance(display_fig, go.Figure):
                    raise TypeError("The Plotly artifact must own a Plotly figure.")
                drill_enabled = False
                generation_key = _drill_down_key(plot.plot_id, "generation")
                generation = int(st.session_state.get(generation_key, 0))
                result_key = _drill_down_key(plot.plot_id, "result")
                event_key = _drill_down_key(plot.plot_id, "last_event")

                if _supports_drill_down(display_fig):
                    drill_enabled = DrillDownPanel.render_toggle(plot.plot_id)
                stored = st.session_state.get(result_key)
                if (
                    isinstance(stored, dict)
                    and stored.get("artifact_generation") != artifact_generation
                ):
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
                    artifact,
                    plot.plot_id,
                    plot.name,
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
                                    "artifact_generation": artifact_generation,
                                    "point_label": point_label(interaction_data),
                                    "result": result,
                                }
                                st.rerun()
                                return
                # Handle relayout events (zoom, pan, legend drag)
                elif interaction_data:
                    last_event_key = WidgetKeyBuilder.plot_key(plot.plot_id, "last_relayout")
                    last_event = st.session_state.get(last_event_key)
                    if interaction_data != last_event:
                        if plot.update_from_relayout(interaction_data):
                            st.session_state[last_event_key] = interaction_data
                            st.rerun()

                stored = st.session_state.get(result_key)
                if (
                    isinstance(stored, dict)
                    and stored.get("artifact_generation") == artifact_generation
                ):
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
        data_hash: str | None,
        engine: EngineMode = "plotly",
    ) -> str | None:
        """Identify retained data, configuration and engine for figure reuse.

        All persisted configuration, including zoom and legend positions,
        affects the identity. Transient widgets and browser events are stored
        separately. Unsupported metadata bypasses this optimization cache.

        Args:
            plot_id: Unique plot identifier.
            config: Plot configuration dict.
            data_hash: Hash of the processed data.
            engine: Active rendering engine.

        Returns:
            Cache identity, or ``None`` when reuse cannot be verified.
        """
        # [impl->req~ring5.plots.independent-state~1]
        if data_hash is None:
            return None
        try:
            return content_signature(
                {"plot_id": plot_id, "config": config, "data": data_hash, "engine": engine}
            )
        except ValueError:
            return None

    @staticmethod
    def _compute_data_hash(data: pd.DataFrame) -> str | None:
        """Identify all retained frame content without coercing unsupported values.

        Args:
            data: DataFrame to hash.

        Returns:
            Frame identity, or ``None`` to bypass figure reuse.
        """
        try:
            return frame_signature(data)
        except ValueError:
            return None
