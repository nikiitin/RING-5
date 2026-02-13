"""Tests for plot adapters -- delegation correctness to underlying services."""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pandas as pd

from tests.ui_logic.conftest import StubPlotHandle


# ---------------------------------------------------------------------------
# PlotLifecycleAdapter
# ---------------------------------------------------------------------------
class TestPlotLifecycleAdapter:
    """Verify PlotLifecycleAdapter delegates to PlotService."""

    def test_create_plot_delegates(self) -> None:
        """create_plot passes name, type, state_manager through."""
        from src.web.pages.plot_adapters import PlotLifecycleAdapter

        adapter = PlotLifecycleAdapter()
        mock_sm = MagicMock()
        sentinel = StubPlotHandle(plot_id=42)

        with patch(
            "src.web.pages.plot_adapters.PlotService.create_plot",
            return_value=sentinel,
        ) as mock_create:
            result = adapter.create_plot("My Plot", "bar", mock_sm)
            mock_create.assert_called_once_with("My Plot", "bar", mock_sm)
            assert result is sentinel

    def test_delete_plot_delegates(self) -> None:
        """delete_plot passes plot_id and state_manager through."""
        from src.web.pages.plot_adapters import PlotLifecycleAdapter

        adapter = PlotLifecycleAdapter()
        mock_sm = MagicMock()

        with patch(
            "src.web.pages.plot_adapters.PlotService.delete_plot",
        ) as mock_delete:
            adapter.delete_plot(7, mock_sm)
            mock_delete.assert_called_once_with(7, mock_sm)

    def test_duplicate_plot_delegates(self) -> None:
        """duplicate_plot passes plot handle and state_manager through."""
        from src.web.pages.plot_adapters import PlotLifecycleAdapter

        adapter = PlotLifecycleAdapter()
        mock_sm = MagicMock()
        plot = StubPlotHandle(plot_id=5)
        dup = StubPlotHandle(plot_id=55)

        with patch(
            "src.web.pages.plot_adapters.PlotService.duplicate_plot",
            return_value=dup,
        ) as mock_dup:
            result = adapter.duplicate_plot(plot, mock_sm)
            mock_dup.assert_called_once_with(plot, mock_sm)
            assert result is dup

    def test_change_plot_type_delegates(self) -> None:
        """change_plot_type passes plot, new_type, state_manager through."""
        from src.web.pages.plot_adapters import PlotLifecycleAdapter

        adapter = PlotLifecycleAdapter()
        mock_sm = MagicMock()
        plot = StubPlotHandle(plot_id=3)
        changed = StubPlotHandle(plot_type="line")

        with patch(
            "src.web.pages.plot_adapters.PlotService.change_plot_type",
            return_value=changed,
        ) as mock_change:
            result = adapter.change_plot_type(plot, "line", mock_sm)
            mock_change.assert_called_once_with(plot, "line", mock_sm)
            assert result is changed


# ---------------------------------------------------------------------------
# PlotTypeRegistryAdapter
# ---------------------------------------------------------------------------
class TestPlotTypeRegistryAdapter:
    """Verify PlotTypeRegistryAdapter delegates to PlotFactory."""

    def test_get_available_types_delegates(self) -> None:
        """get_available_types returns PlotFactory.get_available_plot_types()."""
        from src.web.pages.plot_adapters import PlotTypeRegistryAdapter

        adapter = PlotTypeRegistryAdapter()
        expected = ["bar", "line", "scatter"]

        with patch(
            "src.web.pages.plot_adapters.PlotFactory.get_available_plot_types",
            return_value=expected,
        ) as mock_types:
            result = adapter.get_available_types()
            mock_types.assert_called_once()
            assert result == expected

    def test_returns_list_type(self) -> None:
        """Return value is a list of strings."""
        from src.web.pages.plot_adapters import PlotTypeRegistryAdapter

        adapter = PlotTypeRegistryAdapter()

        with patch(
            "src.web.pages.plot_adapters.PlotFactory.get_available_plot_types",
            return_value=["grouped_bar"],
        ):
            result = adapter.get_available_types()
            assert isinstance(result, list)
            assert all(isinstance(t, str) for t in result)


# ---------------------------------------------------------------------------
# ChartDisplayAdapter
# ---------------------------------------------------------------------------
class TestChartDisplayAdapter:
    """Verify ChartDisplayAdapter delegates to PlotRenderer."""

    def test_render_chart_delegates(self) -> None:
        """render_chart passes plot and should_generate through."""
        from src.web.pages.plot_adapters import ChartDisplayAdapter

        adapter = ChartDisplayAdapter()
        plot = StubPlotHandle(plot_id=1)

        with patch(
            "src.web.pages.plot_adapters.PlotRenderer.render_plot",
        ) as mock_render:
            adapter.render_chart(plot, True)
            mock_render.assert_called_once_with(plot, True)

    def test_render_chart_with_false(self) -> None:
        """render_chart passes should_generate=False correctly."""
        from src.web.pages.plot_adapters import ChartDisplayAdapter

        adapter = ChartDisplayAdapter()
        plot = StubPlotHandle(plot_id=2)

        with patch(
            "src.web.pages.plot_adapters.PlotRenderer.render_plot",
        ) as mock_render:
            adapter.render_chart(plot, False)
            mock_render.assert_called_once_with(plot, False)


# ---------------------------------------------------------------------------
# PipelineExecutorAdapter
# ---------------------------------------------------------------------------
class TestPipelineExecutorAdapter:
    """Verify PipelineExecutorAdapter delegates to shaper functions."""

    def test_apply_shapers_delegates(self, sample_data: pd.DataFrame) -> None:
        """apply_shapers passes data and configs through."""
        from src.web.pages.plot_adapters import PipelineExecutorAdapter

        adapter = PipelineExecutorAdapter()
        configs: List[Dict[str, Any]] = [{"type": "sort", "config": {}}]

        with patch(
            "src.web.pages.plot_adapters.apply_shapers",
            return_value=sample_data,
        ) as mock_apply:
            result = adapter.apply_shapers(sample_data, configs)
            mock_apply.assert_called_once_with(sample_data, configs)
            assert result is sample_data

    def test_configure_shaper_delegates(self, sample_data: pd.DataFrame) -> None:
        """configure_shaper passes all args including optional owner_id."""
        from src.web.pages.plot_adapters import PipelineExecutorAdapter

        adapter = PipelineExecutorAdapter()
        existing: Dict[str, Any] = {"type": "normalize"}

        with patch(
            "src.web.pages.plot_adapters.configure_shaper",
            return_value={"type": "normalize", "target": "x"},
        ) as mock_cfg:
            result = adapter.configure_shaper("normalize", sample_data, "s1", existing, owner_id=5)
            mock_cfg.assert_called_once_with("normalize", sample_data, "s1", existing, owner_id=5)
            assert result["type"] == "normalize"

    def test_configure_shaper_no_owner_id(self, sample_data: pd.DataFrame) -> None:
        """configure_shaper defaults owner_id to None."""
        from src.web.pages.plot_adapters import PipelineExecutorAdapter

        adapter = PipelineExecutorAdapter()

        with patch(
            "src.web.pages.plot_adapters.configure_shaper",
            return_value={"type": "sort"},
        ) as mock_cfg:
            adapter.configure_shaper("sort", sample_data, "s2", None)
            mock_cfg.assert_called_once_with("sort", sample_data, "s2", None, owner_id=None)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------
class TestAdapterProtocolConformance:
    """Verify adapters satisfy their protocol contracts."""

    def test_lifecycle_has_required_methods(self) -> None:
        """PlotLifecycleAdapter has create/delete/duplicate/change methods."""
        from src.web.pages.plot_adapters import PlotLifecycleAdapter

        adapter = PlotLifecycleAdapter()
        assert callable(getattr(adapter, "create_plot", None))
        assert callable(getattr(adapter, "delete_plot", None))
        assert callable(getattr(adapter, "duplicate_plot", None))
        assert callable(getattr(adapter, "change_plot_type", None))

    def test_registry_has_required_methods(self) -> None:
        """PlotTypeRegistryAdapter has get_available_types method."""
        from src.web.pages.plot_adapters import PlotTypeRegistryAdapter

        adapter = PlotTypeRegistryAdapter()
        assert callable(getattr(adapter, "get_available_types", None))

    def test_chart_display_has_required_methods(self) -> None:
        """ChartDisplayAdapter has render_chart method."""
        from src.web.pages.plot_adapters import ChartDisplayAdapter

        adapter = ChartDisplayAdapter()
        assert callable(getattr(adapter, "render_chart", None))

    def test_pipeline_executor_has_required_methods(self) -> None:
        """PipelineExecutorAdapter has apply_shapers and configure_shaper."""
        from src.web.pages.plot_adapters import PipelineExecutorAdapter

        adapter = PipelineExecutorAdapter()
        assert callable(getattr(adapter, "apply_shapers", None))
        assert callable(getattr(adapter, "configure_shaper", None))
