"""Tests for plot lifecycle operations."""

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
            cloned.invalidate_figure.assert_called_once()
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
        # [test->req~ring5.plots.change-type~1]
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


class TestRing5ExportFile:
    """Unit tests for ring5._export.export_file (subsumed export_plot_to_file)."""

    def test_pdf_export_writes_bytes(self, tmp_path: Path) -> None:
        import plotly.graph_objects as go

        from ring5._export import export_file

        fig = go.Figure()
        with patch(
            "ring5._export.plotly_download_bytes", return_value=b"%PDF-fake"
        ) as mock_download:
            result = export_file(fig, str(tmp_path / "ipc.pdf"))

        assert result.endswith("ipc.pdf")
        assert Path(result).read_bytes() == b"%PDF-fake"
        mock_download.assert_called_once()

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        import plotly.graph_objects as go

        from ring5._export import export_file
        from ring5.errors import ExportError

        with pytest.raises(ExportError, match="not supported"):
            export_file(go.Figure(), str(tmp_path / "x.pgf"))

    def test_chrome_missing_becomes_typed_error(self, tmp_path: Path) -> None:
        import plotly.graph_objects as go
        from kaleido.errors import ChromeNotFoundError

        from ring5._export import export_file
        from ring5.errors import DependencyMissingError

        with patch(
            "ring5._export.plotly_download_bytes",
            side_effect=ChromeNotFoundError("no chrome"),
        ):
            with pytest.raises(DependencyMissingError, match="chrome"):
                export_file(go.Figure(), str(tmp_path / "x.png"))

    def test_unknown_object_raises(self, tmp_path: Path) -> None:
        from ring5._export import export_file
        from ring5.errors import ExportError

        with pytest.raises(ExportError, match="Cannot export"):
            export_file(object(), str(tmp_path / "x.png"))  # type: ignore[arg-type]
