"""Tests for PlotService — branch coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.web.pages.ui.plotting.plot_service import PlotService


@pytest.fixture
def mock_state() -> MagicMock:
    sm = MagicMock()
    sm.start_next_plot_id.return_value = 42
    sm.get_current_plot_id.return_value = 42
    return sm


class TestCreatePlot:
    """Test PlotService.create_plot."""

    @patch("src.web.pages.ui.plotting.plot_service.PlotFactory")
    def test_creates_and_registers(self, mock_factory: MagicMock, mock_state: MagicMock) -> None:
        mock_plot = MagicMock()
        mock_factory.create_plot.return_value = mock_plot

        result = PlotService.create_plot("My Plot", "bar", mock_state)

        mock_state.start_next_plot_id.assert_called_once()
        mock_factory.create_plot.assert_called_once_with(
            plot_type="bar", plot_id=42, name="My Plot"
        )
        mock_state.add_plot.assert_called_once_with(mock_plot)
        mock_state.set_current_plot_id.assert_called_once_with(42)
        assert result is mock_plot


class TestDeletePlot:
    """Test PlotService.delete_plot."""

    def test_delete_current_plot_resets(self, mock_state: MagicMock) -> None:
        p1 = MagicMock()
        p1.plot_id = 42
        p2 = MagicMock()
        p2.plot_id = 99
        mock_state.get_plots.return_value = [p1, p2]
        mock_state.get_current_plot_id.return_value = 42

        PlotService.delete_plot(42, mock_state)

        # Should set current to the remaining plot
        mock_state.set_current_plot_id.assert_called_once_with(99)

    def test_delete_non_current_plot(self, mock_state: MagicMock) -> None:
        p1 = MagicMock()
        p1.plot_id = 42
        p2 = MagicMock()
        p2.plot_id = 99
        mock_state.get_plots.return_value = [p1, p2]
        mock_state.get_current_plot_id.return_value = 99

        PlotService.delete_plot(42, mock_state)

        # Current plot shouldn't change
        mock_state.set_current_plot_id.assert_not_called()

    def test_delete_last_plot_sets_none(self, mock_state: MagicMock) -> None:
        p1 = MagicMock()
        p1.plot_id = 42
        mock_state.get_plots.return_value = [p1]
        mock_state.get_current_plot_id.return_value = 42

        PlotService.delete_plot(42, mock_state)

        mock_state.set_current_plot_id.assert_called_once_with(None)


class TestDuplicatePlot:
    """Test PlotService.duplicate_plot."""

    def test_duplicates_with_copy_name(self, mock_state: MagicMock) -> None:
        original = MagicMock()
        original.name = "IPC"
        original.plot_id = 1

        with patch("src.web.pages.ui.plotting.plot_service.copy") as mock_copy:
            cloned = MagicMock()
            mock_copy.deepcopy.return_value = cloned
            mock_state.start_next_plot_id.return_value = 99

            PlotService.duplicate_plot(original, mock_state)

            assert cloned.name == "IPC (copy)"
            assert cloned.plot_id == 99
            assert cloned.last_generated_fig is None
            mock_state.add_plot.assert_called_once_with(cloned)


class TestChangePlotType:
    """Test PlotService.change_plot_type."""

    @patch("src.web.pages.ui.plotting.plot_service.PlotFactory")
    def test_same_type_noop(self, mock_factory: MagicMock, mock_state: MagicMock) -> None:
        plot = MagicMock()
        plot.plot_type = "bar"

        result = PlotService.change_plot_type(plot, "bar", mock_state)
        assert result is plot
        mock_factory.create_plot.assert_not_called()

    @patch("src.web.pages.ui.plotting.plot_service.PlotFactory")
    def test_different_type_replaces(self, mock_factory: MagicMock, mock_state: MagicMock) -> None:
        old_plot = MagicMock()
        old_plot.plot_type = "bar"
        old_plot.plot_id = 5
        old_plot.name = "My"
        old_plot.pipeline = [{"type": "rename"}]
        old_plot.pipeline_counter = 3
        old_plot.processed_data = MagicMock()

        new_plot = MagicMock()
        mock_factory.create_plot.return_value = new_plot

        p_list = [old_plot]
        mock_state.get_plots.return_value = p_list

        result = PlotService.change_plot_type(old_plot, "line", mock_state)

        assert result is new_plot
        assert new_plot.pipeline == old_plot.pipeline
        assert new_plot.config == {}
        mock_state.set_plots.assert_called_once()

    @patch("src.web.pages.ui.plotting.plot_service.PlotFactory")
    def test_plot_not_found_no_crash(self, mock_factory: MagicMock, mock_state: MagicMock) -> None:
        old_plot = MagicMock()
        old_plot.plot_type = "bar"
        old_plot.plot_id = 5

        new_plot = MagicMock()
        mock_factory.create_plot.return_value = new_plot

        # Return empty list so StopIteration is raised
        mock_state.get_plots.return_value = []

        result = PlotService.change_plot_type(old_plot, "line", mock_state)
        assert result is new_plot


class TestExportPlotToFile:
    """Test PlotService.export_plot_to_file."""

    def test_html_export(self, tmp_path: Path) -> None:
        plot = MagicMock()
        plot.name = "My Plot"
        plot.config = {}
        fig = MagicMock()
        plot.generate_figure.return_value = fig

        result = PlotService.export_plot_to_file(plot, str(tmp_path), format="html")

        assert result is not None
        assert result.endswith(".html")
        fig.write_html.assert_called_once()

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        plot = MagicMock()
        plot.name = "My Plot"
        plot.config = {}
        plot.generate_figure.return_value = MagicMock()

        with pytest.raises(ValueError, match="Unsupported export format"):
            PlotService.export_plot_to_file(plot, str(tmp_path), format="svg")

    def test_generate_figure_fails_returns_none(self, tmp_path: Path) -> None:
        plot = MagicMock()
        plot.name = "X"
        plot.generate_figure.side_effect = RuntimeError("no data")

        result = PlotService.export_plot_to_file(plot, str(tmp_path))

        assert result is None

    @patch("src.web.pages.ui.plotting.plot_service.LaTeXExportService")
    def test_pdf_export_success(self, mock_latex_cls: MagicMock, tmp_path: Path) -> None:
        plot = MagicMock()
        plot.name = "IPC"
        plot.config = {}
        fig = MagicMock()
        plot.generate_figure.return_value = fig

        service_instance = MagicMock()
        mock_latex_cls.return_value = service_instance
        service_instance.export.return_value = {
            "success": True,
            "data": b"%PDF-fake",
        }

        result = PlotService.export_plot_to_file(plot, str(tmp_path), format="pdf")

        assert result is not None
        assert result.endswith(".pdf")
        # Verify the file was written
        written = open(result, "rb").read()
        assert written == b"%PDF-fake"

    @patch("src.web.pages.ui.plotting.plot_service.LaTeXExportService")
    def test_pdf_export_failure_raises(self, mock_latex_cls: MagicMock, tmp_path: Path) -> None:
        plot = MagicMock()
        plot.name = "IPC"
        plot.config = {}
        fig = MagicMock()
        plot.generate_figure.return_value = fig

        service_instance = MagicMock()
        mock_latex_cls.return_value = service_instance
        service_instance.export.return_value = {
            "success": False,
            "error": "no kpsewhich",
        }

        with pytest.raises(RuntimeError, match="LaTeX export failed"):
            PlotService.export_plot_to_file(plot, str(tmp_path), format="pdf")

    @patch("src.web.pages.ui.plotting.plot_service.LaTeXExportService")
    def test_pdf_export_none_data_raises(self, mock_latex_cls: MagicMock, tmp_path: Path) -> None:
        plot = MagicMock()
        plot.name = "IPC"
        plot.config = {}
        fig = MagicMock()
        plot.generate_figure.return_value = fig

        service_instance = MagicMock()
        mock_latex_cls.return_value = service_instance
        service_instance.export.return_value = {
            "success": True,
            "data": None,
        }

        with pytest.raises(RuntimeError, match="returned no data"):
            PlotService.export_plot_to_file(plot, str(tmp_path), format="pdf")

    def test_default_format_from_config(self, tmp_path: Path) -> None:
        plot = MagicMock()
        plot.name = "X"
        plot.config = {"download_format": "html"}
        fig = MagicMock()
        plot.generate_figure.return_value = fig

        result = PlotService.export_plot_to_file(plot, str(tmp_path))

        assert result is not None
        assert result.endswith(".html")
