"""
Figure Engine — Orchestrates Figure Creation + Styling.

This is the **single entry point** for all figure generation in the web layer.
Controllers call ``engine.build(plot_type, data, config)`` instead of reaching
into BasePlot subclasses or StyleApplicator directly.

Architecture:
    FigureEngine
        ├── Registry of FigureCreator instances (one per plot type)
        └── FigureStyler instance (shared StyleApplicator)

    build(plot_type, data, config) → go.Figure
        1. Look up creator for plot_type
        2. creator.create_figure(data, config) → raw figure
        3. styler.apply_styles(fig, config) → styled figure
        4. Apply legend labels if present
        5. Return final figure

Migration Strategy:
    Initially, existing BasePlot subclasses serve as FigureCreators (they
    already satisfy the protocol). Over time, the create_figure logic can
    be extracted to standalone classes with no BasePlot dependency.
"""

from typing import Any, Dict, Optional

import pandas as pd
import plotly.graph_objects as go

from src.web.figures.protocols import FigureCreator, FigureStyler


class FigureEngine:
    """
    Facade for figure generation: type dispatch + styling.

    Usage::

        engine = FigureEngine()
        engine.register("bar", bar_plot_instance)
        engine.register("line", line_plot_instance)

        fig = engine.build("bar", data, config)

    Or with existing BasePlot instances::

        engine = FigureEngine.from_plot(plot_instance)
        fig = engine.build(plot_instance.plot_type, data, config)
    """

    def __init__(self) -> None:
        """Initialize with empty creator registry and default styler."""
        self._creators: Dict[str, FigureCreator] = {}
        self._stylers: Dict[str, FigureStyler] = {}

    # ─── Registry ────────────────────────────────────────────────────────

    def register(
        self,
        plot_type: str,
        creator: FigureCreator,
        styler: Optional[FigureStyler] = None,
    ) -> None:
        """
        Register a figure creator (and optional styler) for a plot type.

        If no styler is provided, the caller must register one later via
        ``register_styler()`` before calling ``build()`` for this type.

        Args:
            plot_type: Type key (e.g., "bar", "line", "grouped_stacked_bar").
            creator: Any object with ``create_figure(data, config) -> Figure``.
            styler: Optional styler; if provided, also registers the styler.
        """
        self._creators[plot_type] = creator
        if styler is not None:
            self._stylers[plot_type] = styler

    def register_styler(self, plot_type: str, styler: FigureStyler) -> None:
        """
        Register a custom styler for a plot type (for testing or overrides).

        Args:
            plot_type: Type key.
            styler: Any object with ``apply_styles(fig, config) -> Figure``.
        """
        self._stylers[plot_type] = styler

    @property
    def registered_types(self) -> list[str]:
        """Return all registered plot type keys."""
        return list(self._creators.keys())

    def has_creator(self, plot_type: str) -> bool:
        """Check if a creator is registered for a plot type."""
        return plot_type in self._creators

    # ─── Build ───────────────────────────────────────────────────────────

    def build(
        self,
        plot_type: str,
        data: pd.DataFrame,
        config: Dict[str, Any],
    ) -> go.Figure:
        """
        Build a complete, styled figure.

        Steps:
            1. Dispatch to type-specific creator → raw figure
            2. Apply shared style applicator → styled figure
            3. Apply legend labels if present → final figure

        Args:
            plot_type: Registered type key.
            data: Processed DataFrame.
            config: Combined plot + style configuration dict.

        Returns:
            Fully styled Plotly figure.

        Raises:
            KeyError: If plot_type is not registered.
        """
        if plot_type not in self._creators:
            available: str = ", ".join(sorted(self._creators.keys()))
            raise KeyError(
                f"No figure creator registered for '{plot_type}'. " f"Available: [{available}]"
            )

        creator: FigureCreator = self._creators[plot_type]

        # Step 1: Type-specific figure creation
        fig: go.Figure = creator.create_figure(data, config)

        # Step 2: Apply visual styles (if a styler is registered)
        styler: Optional[FigureStyler] = self._stylers.get(plot_type)
        if styler is not None:
            fig = styler.apply_styles(fig, config)

        # Step 3: Legend label overrides
        legend_labels: Optional[Dict[str, str]] = config.get("legend_labels")
        if legend_labels:
            fig = self._apply_legend_labels(fig, legend_labels)

        return fig

    # ─── Convenience Factory ─────────────────────────────────────────────

    @classmethod
    def from_plot(
        cls,
        plot: FigureCreator,
        plot_type: str,
        styler: Optional[FigureStyler] = None,
    ) -> "FigureEngine":
        """
        Create a FigureEngine pre-loaded with a single plot creator.

        Convenience for the common case where you have one BasePlot instance
        and want to generate its figure through the engine.

        Args:
            plot: A BasePlot instance (satisfies FigureCreator protocol).
            plot_type: The plot type key.
            styler: Optional styler for this plot type.

        Returns:
            FigureEngine with the plot registered.
        """
        engine: FigureEngine = cls()
        engine.register(plot_type, plot, styler=styler)
        return engine

    # ─── Internal ────────────────────────────────────────────────────────

    @staticmethod
    def _apply_legend_labels(fig: go.Figure, legend_labels: Dict[str, str]) -> go.Figure:
        """
        Apply custom legend label mappings to trace names.

        Args:
            fig: Figure to modify.
            legend_labels: Mapping of original trace names to display names.

        Returns:
            Figure with updated trace names.
        """
        fig.for_each_trace(lambda t: t.update(name=legend_labels.get(t.name, t.name)))
        return fig
