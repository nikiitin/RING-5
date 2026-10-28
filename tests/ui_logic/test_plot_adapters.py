"""Tests for plot adapters -- delegation correctness to underlying services."""

from typing import cast
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models.shaper_models import ShaperStepConfig
from tests.ui_logic.conftest import StubPlotHandle
from src.core.services.shapers.shapers_impl import DefaultShapersAPI


# PlotLifecycleAdapter
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


# PlotTypeRegistryAdapter
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


# PipelineExecutorAdapter
class TestPipelineExecutorAdapter:
    """Verify PipelineExecutorAdapter delegates to shaper functions."""

    @pytest.mark.parametrize(
        "track_source_rows", [None, False, True], ids=["default", "preview", "finalization"]
    )
    def test_apply_shapers_delegates(
        self, sample_data: pd.DataFrame, track_source_rows: bool | None
    ) -> None:
        """Preserve the caller's provenance policy and return the facade's actual output."""
        from src.web.pages.plot_adapters import PipelineExecutorAdapter

        adapter = PipelineExecutorAdapter(DefaultShapersAPI())
        configs = cast(
            list[ShaperStepConfig],
            [{"type": "sort", "order_dict": {"benchmark_name": ["xalancbmk", "mcf"]}}],
        )
        transformed = sample_data.iloc[::-1].copy()

        with patch(
            "src.core.services.shapers.shapers_impl.DefaultShapersAPI.process_pipeline",
            return_value=transformed,
        ) as mock_apply:
            if track_source_rows is None:
                result = adapter.apply_shapers(sample_data, configs)
            else:
                result = adapter.apply_shapers(
                    sample_data, configs, track_source_rows=track_source_rows
                )
            mock_apply.assert_called_once_with(
                sample_data, configs, track_source_rows=bool(track_source_rows)
            )
            assert result is transformed
            assert result is not sample_data

    def test_configure_shaper_delegates(self, sample_data: pd.DataFrame) -> None:
        """configure_shaper passes all args including optional owner_id."""
        from src.web.pages.plot_adapters import PipelineExecutorAdapter

        adapter = PipelineExecutorAdapter(DefaultShapersAPI())
        existing = cast(ShaperStepConfig, {"type": "normalize"})

        with patch(
            "src.web.pages.plot_adapters.configure_shaper",
            return_value=cast(ShaperStepConfig, {"type": "normalize", "target": "x"}),
        ) as mock_cfg:
            result = adapter.configure_shaper("normalize", sample_data, 1, existing, owner_id=5)
            mock_cfg.assert_called_once_with(
                "normalize",
                sample_data,
                1,
                existing,
                owner_id=5,
                display_names=DefaultShapersAPI().get_shaper_display_names(),
            )
            assert result.get("type") == "normalize"

    def test_configure_shaper_preserves_zero_owner_id(self, sample_data: pd.DataFrame) -> None:
        """Plot zero owns its widgets like every other plot identifier."""
        from src.web.pages.plot_adapters import PipelineExecutorAdapter

        adapter = PipelineExecutorAdapter(DefaultShapersAPI())

        with patch(
            "src.web.pages.plot_adapters.configure_shaper",
            return_value=cast(ShaperStepConfig, {"type": "sort"}),
        ) as mock_cfg:
            adapter.configure_shaper("sort", sample_data, 2, None, owner_id=0)
            mock_cfg.assert_called_once_with(
                "sort",
                sample_data,
                2,
                None,
                owner_id=0,
                display_names=DefaultShapersAPI().get_shaper_display_names(),
            )


# Protocol conformance
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

    def test_pipeline_executor_has_required_methods(self) -> None:
        """PipelineExecutorAdapter has apply_shapers and configure_shaper."""
        from src.web.pages.plot_adapters import PipelineExecutorAdapter

        adapter = PipelineExecutorAdapter(DefaultShapersAPI())
        assert callable(getattr(adapter, "apply_shapers", None))
        assert callable(getattr(adapter, "configure_shaper", None))
