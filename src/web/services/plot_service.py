import copy
import os
from typing import Optional

from src.plotting import BasePlot, PlotFactory
from src.web.repositories import PlotRepository


class PlotService:
    """Service to handle plot lifecycle and management."""

    @staticmethod
    def create_plot(name: str, plot_type: str) -> BasePlot:
        """Create a new plot and add it to the session state."""
        plot_id = PlotRepository.increment_plot_counter()
        plot = PlotFactory.create_plot(plot_type=plot_type, plot_id=plot_id, name=name)

        PlotRepository.add_plot(plot)
        PlotRepository.set_current_plot_id(plot_id)

        return plot

    @staticmethod
    def delete_plot(plot_id: int) -> None:
        """Delete a plot by ID."""
        PlotRepository.remove_plot(plot_id)

        # If deleted current plot, reset selection
        if PlotRepository.get_current_plot_id() == plot_id:
            remaining_plots = PlotRepository.get_plots()
            PlotRepository.set_current_plot_id(
                None if not remaining_plots else remaining_plots[0].plot_id
            )

    @staticmethod
    def duplicate_plot(plot: BasePlot) -> BasePlot:
        """Duplicate an existing plot."""
        new_plot = copy.deepcopy(plot)
        new_plot.plot_id = PlotRepository.increment_plot_counter()
        new_plot.name = f"{plot.name} (copy)"
        # Clear non-serializable data
        new_plot.last_generated_fig = None

        PlotRepository.add_plot(new_plot)

        return new_plot

    @staticmethod
    def change_plot_type(plot: BasePlot, new_type: str) -> BasePlot:
        """Change the type of an existing plot, preserving configuration where possible."""
        if plot.plot_type == new_type:
            return plot

        new_plot = PlotFactory.create_plot(new_type, plot.plot_id, plot.name)
        new_plot.pipeline = plot.pipeline
        new_plot.pipeline_counter = plot.pipeline_counter
        new_plot.processed_data = plot.processed_data
        new_plot.config = {}  # Reset config when type changes

        # Replace in session state
        plots = PlotRepository.get_plots()
        try:
            # Find index by object identity or ID
            idx = next(i for i, p in enumerate(plots) if p.plot_id == plot.plot_id)
            plots[idx] = new_plot
            PlotRepository.set_plots(plots)
        except StopIteration:
            # Should not happen if checking logic is correct
            pass

        return new_plot

    @staticmethod
    def export_plot_to_file(
        plot: BasePlot, directory: str, format: Optional[str] = None
    ) -> Optional[str]:
        """
        Export a plot to a file in the specified directory.

        Supports HTML and PDF export. PDF export uses matplotlib/LaTeX backend
        for publication-quality output.

        Args:
            plot: The plot to export
            directory: Output directory path
            format: Export format ("html", "pdf", "pgf", or "eps"). Defaults to "pdf"

        Returns:
            Path to exported file, or None if export failed

        Note:
            For publication-quality exports, use LaTeXExportService directly.
        """
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Ensure figure is generated
        try:
            fig = plot.generate_figure()
        except Exception:
            # If generation fails (e.g. no data), skip
            return None

        fmt = format or plot.config.get("download_format", "pdf")

        # Validate format BEFORE constructing path (security: prevent path traversal)
        allowed_formats = ["html", "pdf", "pgf", "eps"]
        if fmt not in allowed_formats:
            raise ValueError(
                f"Unsupported export format '{fmt}'. "
                f"Supported formats: {', '.join(allowed_formats)}"
            )

        # Clean name
        safe_name = "".join([c if c.isalnum() else "_" for c in plot.name])
        filename = f"{safe_name}.{fmt}"
        path = os.path.join(directory, filename)

        if fmt == "html":
            fig.write_html(path)
        elif fmt in ["pdf", "pgf", "eps"]:
            # Use LaTeX export service for publication-quality output
            from src.plotting.export.latex_export_service import LaTeXExportService

            service = LaTeXExportService()
            result = service.export(fig=fig, preset="single_column", format=fmt)

            if result["success"]:
                data = result["data"]
                if data is None:
                    raise RuntimeError("LaTeX export succeeded but returned no data")
                with open(path, "wb") as f:
                    f.write(data)
            else:
                raise RuntimeError(f"LaTeX export failed: {result.get('error', 'Unknown error')}")

        return path
