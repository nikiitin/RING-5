"""
Plot Service - Plot Lifecycle Management.

Handles creation, rendering, and management of plot objects in the web UI.
Coordinates plot factory, state persistence, and configuration updates.
"""

import copy
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from src.core.common.utils import normalize_user_path, validate_path_within
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory

if TYPE_CHECKING:
    from src.core.state.repository_state_manager import RepositoryStateManager

logger = logging.getLogger(__name__)


class PlotService:
    """Service to handle plot lifecycle and management."""

    @staticmethod
    def create_plot(name: str, plot_type: str, state_manager: "RepositoryStateManager") -> BasePlot:
        """Create a new plot and add it to the session state."""
        plot_id = state_manager.start_next_plot_id()
        plot = PlotFactory.create_plot(plot_type=plot_type, plot_id=plot_id, name=name)

        state_manager.add_plot(plot)
        state_manager.set_current_plot_id(plot_id)

        return plot

    @staticmethod
    def delete_plot(plot_id: int, state_manager: "RepositoryStateManager") -> None:
        """Delete a plot by ID."""
        plots = state_manager.get_plots()
        plots = [p for p in plots if p.plot_id != plot_id]
        state_manager.set_plots(plots)

        # If deleted current plot, reset selection
        if state_manager.get_current_plot_id() == plot_id:
            state_manager.set_current_plot_id(None if not plots else plots[0].plot_id)

    @staticmethod
    def duplicate_plot(plot: BasePlot, state_manager: "RepositoryStateManager") -> BasePlot:
        """Duplicate an existing plot."""
        new_plot = copy.deepcopy(plot)
        new_plot.plot_id = state_manager.start_next_plot_id()
        new_plot.name = f"{plot.name} (copy)"
        # Clear non-serializable data
        new_plot.last_generated_fig = None

        state_manager.add_plot(new_plot)

        return new_plot

    @staticmethod
    def change_plot_type(
        plot: BasePlot, new_type: str, state_manager: "RepositoryStateManager"
    ) -> BasePlot:
        """Change the type of an existing plot, preserving configuration where possible."""
        if plot.plot_type == new_type:
            return plot

        new_plot = PlotFactory.create_plot(new_type, plot.plot_id, plot.name)
        new_plot.pipeline = plot.pipeline
        new_plot.pipeline_counter = plot.pipeline_counter
        new_plot.processed_data = plot.processed_data
        new_plot.config = {}  # Reset config when type changes

        # Replace in session state
        plots = state_manager.get_plots()
        try:
            # Find index by object identity or ID
            idx = next(i for i, p in enumerate(plots) if p.plot_id == plot.plot_id)
            plots[idx] = new_plot
            state_manager.set_plots(plots)
        except StopIteration:
            logger.warning("Plot ID %d not found in plots list during type change", plot.plot_id)

        return new_plot

    @staticmethod
    def export_plot_to_file(
        plot: BasePlot, directory: str, format: str | None = None
    ) -> str | None:
        """
        Export a plot to a file in the specified directory.

        Supports HTML and PDF export. PDF export uses matplotlib/LaTeX backend
        for publication-quality output.

        Args:
            plot: The plot to export
            directory: Output directory path
            format: Export format ("html", "pdf", "png", or "svg"). Defaults to "pdf"

        Returns:
            Path to exported file, or None if export failed

        Note:
            Uses Kaleido for vector/raster export of Plotly figures.
        """
        # Normalize and validate directory path before any filesystem ops
        safe_dir: str = os.path.normpath(directory) if directory else "."
        resolved_dir_path = normalize_user_path(safe_dir)
        if not resolved_dir_path.exists():
            resolved_dir_path.mkdir(parents=True, exist_ok=True)

        # Ensure figure is generated
        try:
            fig = plot.generate_figure()
        except Exception:
            logger.warning("Figure generation failed for plot '%s', skipping export", plot.name)
            return None

        fmt = format or plot.config.get("download_format", "pdf")

        # Validate format BEFORE constructing path (security: prevent path traversal)
        allowed_formats = ["html", "pdf", "png", "svg"]
        if fmt not in allowed_formats:
            raise ValueError(
                f"Unsupported export format '{fmt}'. "
                f"Supported formats: {', '.join(allowed_formats)}"
            )

        # Clean name
        safe_name = "".join([c if c.isalnum() else "_" for c in plot.name])
        filename = f"{safe_name}.{fmt}"
        validated_path = validate_path_within(resolved_dir_path / filename, resolved_dir_path)
        path = os.path.normpath(str(validated_path))

        if fmt == "html":
            fig.write_html(Path(path))
        elif fmt in ("pdf", "png", "svg"):
            from typing import cast

            from src.web.pages.ui.plotting.download_section import (
                PlotlyFormat,
                plotly_download_bytes,
            )

            data = plotly_download_bytes(fig, fmt=cast(PlotlyFormat, fmt))
            with open(path, "wb") as f:
                f.write(data)

        return path
