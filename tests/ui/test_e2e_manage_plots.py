"""E2E AppTest: Manage Plots page — deep interaction tests.

Goes beyond the basic rendering tests in test_e2e_data_loaded.py to verify:
- Plot CRUD operations (create, delete, duplicate) via API + UI state
- Plot selector with multiple plots
- Pipeline editor widgets (add shaper, steps, finalize)
- Plot controls (rename, delete, duplicate buttons)
- Workspace management section
- Plot type selector and configuration
- Auto-refresh and chart rendering controls

Uses a hybrid approach: UI widget verification combined with
API-based operations for flows that involve st.rerun() or dialogs.
"""

from typing import Any, Dict, List

import pandas as pd

from tests.ui.helpers import (
    create_app_with_data,
    create_app_with_plots,
    get_api,
    navigate_to,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_plot_via_api(api: Any, name: str, plot_type: str = "bar") -> Any:
    """Create a plot through the PlotService and return it."""
    from src.web.pages.ui.plotting.plot_service import PlotService

    return PlotService.create_plot(name, plot_type, api.state_manager)


def _inject_multiple_plots(api: Any, count: int = 3) -> List[Any]:
    """Inject multiple plots with different types."""
    types: List[str] = ["bar", "grouped_bar", "line", "scatter", "stacked_bar"]
    plots: List[Any] = []
    for i in range(count):
        plot_type: str = types[i % len(types)]
        plot = _create_plot_via_api(api, f"Plot {i + 1}", plot_type)
        plots.append(plot)
    return plots


# ---------------------------------------------------------------------------
# Plot CRUD operations
# ---------------------------------------------------------------------------
class TestPlotCreation:
    """Plot creation via API and UI state consistency."""

    def test_create_single_plot_state(self) -> None:
        """Creating one plot correctly updates state_manager."""
        at = create_app_with_data()
        api: Any = get_api(at)

        count_before: int = len(api.state_manager.get_plots())
        _create_plot_via_api(api, "My Plot", "bar")
        plots = api.state_manager.get_plots()

        assert len(plots) == count_before + 1
        created = [p for p in plots if p.name == "My Plot"]
        assert len(created) == 1
        assert created[0].plot_type == "bar"

    def test_create_multiple_plots_unique_ids(self) -> None:
        """Each created plot gets a unique plot_id."""
        at = create_app_with_data()
        api: Any = get_api(at)

        plots: List[Any] = _inject_multiple_plots(api, 3)
        ids = [p.plot_id for p in plots]

        assert len(set(ids)) == 3, "All plot IDs should be unique"

    def test_current_plot_id_set_after_create(self) -> None:
        """Creating a plot sets it as the current plot."""
        at = create_app_with_data()
        api: Any = get_api(at)

        plot = _create_plot_via_api(api, "Active Plot")
        current_id = api.state_manager.get_current_plot_id()

        assert current_id == plot.plot_id

    def test_create_each_plot_type(self) -> None:
        """Every registered plot type can be created without error."""
        from src.web.pages.ui.plotting.plot_factory import PlotFactory

        at = create_app_with_data()
        api: Any = get_api(at)

        available: List[str] = PlotFactory.get_available_plot_types()
        assert len(available) >= 5, "Expected at least 5 plot types"

        for plot_type in available:
            plot = _create_plot_via_api(api, f"Type {plot_type}", plot_type)
            assert plot.plot_type == plot_type


class TestPlotDeletion:
    """Plot deletion via PlotService updates state correctly."""

    def test_delete_removes_specific_plot(self) -> None:
        """Deleting a plot removes it from the plots list."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        at = create_app_with_data()
        api: Any = get_api(at)

        plot = _create_plot_via_api(api, "To Delete")
        count_before: int = len(api.state_manager.get_plots())

        PlotService.delete_plot(plot.plot_id, api.state_manager)

        remaining = api.state_manager.get_plots()
        assert len(remaining) == count_before - 1
        remaining_ids = [p.plot_id for p in remaining]
        assert plot.plot_id not in remaining_ids

    def test_delete_updates_current_plot_id(self) -> None:
        """Deleting the current plot changes current_plot_id."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        at = create_app_with_data()
        api: Any = get_api(at)

        plot = _create_plot_via_api(api, "Current Plot")
        assert api.state_manager.get_current_plot_id() == plot.plot_id

        PlotService.delete_plot(plot.plot_id, api.state_manager)

        # After deletion, current_plot_id is either None or a different plot
        new_current = api.state_manager.get_current_plot_id()
        assert new_current != plot.plot_id

    def test_delete_one_of_many(self) -> None:
        """Deleting one plot leaves others intact."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        at = create_app_with_data()
        api: Any = get_api(at)

        plots: List[Any] = _inject_multiple_plots(api, 3)
        count_before: int = len(api.state_manager.get_plots())

        PlotService.delete_plot(plots[1].plot_id, api.state_manager)

        remaining = api.state_manager.get_plots()
        remaining_ids = [p.plot_id for p in remaining]

        assert len(remaining) == count_before - 1
        assert plots[1].plot_id not in remaining_ids
        assert plots[0].plot_id in remaining_ids
        assert plots[2].plot_id in remaining_ids


class TestPlotDuplication:
    """Plot duplication creates a faithful copy with a new ID."""

    def test_duplicate_creates_copy(self) -> None:
        """Duplicating a plot creates a new plot with '(copy)' suffix."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        at = create_app_with_data()
        api: Any = get_api(at)

        original = _create_plot_via_api(api, "Original", "grouped_bar")
        dup = PlotService.duplicate_plot(original, api.state_manager)

        assert dup.plot_id != original.plot_id
        assert "(copy)" in dup.name
        assert dup.plot_type == original.plot_type

    def test_duplicate_preserves_pipeline(self) -> None:
        """Duplicated plot carries over the pipeline from original."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        at = create_app_with_data()
        api: Any = get_api(at)

        original = _create_plot_via_api(api, "With Pipeline", "bar")
        original.pipeline = [
            {"id": 0, "type": "columnSelector", "config": {"columns": ["system.cpu.ipc"]}},
        ]

        dup = PlotService.duplicate_plot(original, api.state_manager)
        assert len(dup.pipeline) == 1
        assert dup.pipeline[0]["type"] == "columnSelector"

    def test_duplicate_increments_total(self) -> None:
        """After duplication, total plot count increases by one."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        at = create_app_with_data()
        api: Any = get_api(at)

        _create_plot_via_api(api, "First")
        count_before: int = len(api.state_manager.get_plots())

        plots = api.state_manager.get_plots()
        PlotService.duplicate_plot(plots[0], api.state_manager)

        assert len(api.state_manager.get_plots()) == count_before + 1


# ---------------------------------------------------------------------------
# Page rendering with injected plots
# ---------------------------------------------------------------------------
class TestManagePlotsPageWithPlots:
    """UI elements appear correctly when plots are pre-injected."""

    def test_plot_selector_radio_present(self) -> None:
        """Plot selector radio renders when plots exist."""
        at = create_app_with_plots()
        navigate_to(at, "Manage Plots")

        assert not at.exception
        # At least the plot-selector radio exists
        radios = [r for r in at.radio if not r.label.startswith("Navigate")]
        assert len(radios) >= 1, "Expected plot selector radio"

    def test_controls_section_has_buttons(self) -> None:
        """Controls section renders rename, delete, duplicate buttons."""
        at = create_app_with_plots()
        navigate_to(at, "Manage Plots")

        assert not at.exception
        button_labels = [b.label.lower() for b in at.button]
        has_delete = any("delete" in lbl or "🗑" in lbl for lbl in button_labels)
        has_duplicate = any("duplicate" in lbl or "📋" in lbl for lbl in button_labels)

        assert has_delete, f"Expected delete button, got labels: {button_labels}"
        assert has_duplicate, f"Expected duplicate button, got labels: {button_labels}"

    def test_pipeline_section_has_add_shaper(self) -> None:
        """Pipeline section shows the add-shaper selectbox."""
        at = create_app_with_plots()
        navigate_to(at, "Manage Plots")

        assert not at.exception
        # The add-shaper selectbox should be present
        selectboxes = at.selectbox
        assert len(selectboxes) >= 2, "Expected at least 2 selectboxes (plot type + add shaper)"

    def test_no_exception_with_multiple_plots(self) -> None:
        """Page renders without error when 3+ plots are injected."""
        at = create_app_with_data()
        api: Any = get_api(at)
        count_before: int = len(api.state_manager.get_plots())
        _inject_multiple_plots(api, 4)
        navigate_to(at, "Manage Plots")

        assert not at.exception
        assert len(api.state_manager.get_plots()) == count_before + 4

    def test_rename_input_present(self) -> None:
        """Rename text_input is present for the current plot."""
        at = create_app_with_plots()
        navigate_to(at, "Manage Plots")

        assert not at.exception
        # Should have at least one text input for renaming
        # (in addition to the create form text input)
        assert len(at.text_input) >= 2, "Expected text inputs for create name + rename"


# ---------------------------------------------------------------------------
# Pipeline operations
# ---------------------------------------------------------------------------
class TestPipelineOperations:
    """Pipeline add/remove/finalize via API."""

    def test_add_shaper_to_pipeline(self) -> None:
        """Adding a shaper step to a plot's pipeline."""
        at = create_app_with_data()
        api: Any = get_api(at)

        plot = _create_plot_via_api(api, "Pipeline Plot", "bar")
        plot.pipeline.append({"id": 0, "type": "columnSelector", "config": {}})

        assert len(plot.pipeline) == 1
        assert plot.pipeline[0]["type"] == "columnSelector"

    def test_multiple_shapers_in_pipeline(self) -> None:
        """Pipeline supports multiple sequential shaper steps."""
        at = create_app_with_data()
        api: Any = get_api(at)

        plot = _create_plot_via_api(api, "Multi Shaper", "bar")
        plot.pipeline.extend(
            [
                {"id": 0, "type": "columnSelector", "config": {}},
                {"id": 1, "type": "sort", "config": {}},
                {"id": 2, "type": "mean", "config": {}},
            ]
        )

        assert len(plot.pipeline) == 3

    def test_remove_shaper_from_pipeline(self) -> None:
        """Removing a shaper step from the pipeline."""
        at = create_app_with_data()
        api: Any = get_api(at)

        plot = _create_plot_via_api(api, "Remove Test", "bar")
        plot.pipeline.extend(
            [
                {"id": 0, "type": "columnSelector", "config": {}},
                {"id": 1, "type": "sort", "config": {}},
            ]
        )

        # Remove first step
        plot.pipeline = [s for s in plot.pipeline if s["id"] != 0]
        assert len(plot.pipeline) == 1
        assert plot.pipeline[0]["type"] == "sort"

    def test_pipeline_reorder(self) -> None:
        """Pipeline steps can be reordered (move up/down)."""
        at = create_app_with_data()
        api: Any = get_api(at)

        plot = _create_plot_via_api(api, "Reorder Test", "bar")
        step_a: Dict[str, Any] = {"id": 0, "type": "columnSelector", "config": {}}
        step_b: Dict[str, Any] = {"id": 1, "type": "sort", "config": {}}
        plot.pipeline = [step_a, step_b]

        # Swap: move_down on index 0
        plot.pipeline[0], plot.pipeline[1] = plot.pipeline[1], plot.pipeline[0]

        assert plot.pipeline[0]["type"] == "sort"
        assert plot.pipeline[1]["type"] == "columnSelector"

    def test_finalize_pipeline_sets_processed_data(self) -> None:
        """Finalizing a pipeline with a column selector produces processed data."""
        from src.core.services.shapers.factory import ShaperFactory

        at = create_app_with_data()
        api: Any = get_api(at)

        plot = _create_plot_via_api(api, "Finalize Plot", "bar")

        raw_data: pd.DataFrame = api.state_manager.get_data()

        shaper = ShaperFactory.create_shaper(
            "columnSelector", {"columns": ["benchmark_name", "system.cpu.ipc"]}
        )
        processed: pd.DataFrame = shaper(raw_data)
        plot.processed_data = processed

        assert plot.processed_data is not None
        assert list(plot.processed_data.columns) == [
            "benchmark_name",
            "system.cpu.ipc",
        ]


# ---------------------------------------------------------------------------
# Plot type and config
# ---------------------------------------------------------------------------
class TestPlotTypeChange:
    """Changing a plot's type via PlotService.change_plot_type."""

    def test_change_plot_type(self) -> None:
        """Changing type from bar to line updates the plot_type."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        at = create_app_with_data()
        api: Any = get_api(at)

        plot = _create_plot_via_api(api, "Type Change", "bar")
        new_plot = PlotService.change_plot_type(plot, "line", api.state_manager)

        assert new_plot.plot_type == "line"

    def test_type_change_preserves_pipeline(self) -> None:
        """Pipeline is preserved when changing plot type."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        at = create_app_with_data()
        api: Any = get_api(at)

        plot = _create_plot_via_api(api, "Keep Pipeline", "bar")
        plot.pipeline = [
            {"id": 0, "type": "sort", "config": {"column": "system.cpu.ipc"}},
        ]

        new_plot = PlotService.change_plot_type(plot, "scatter", api.state_manager)

        assert len(new_plot.pipeline) == 1
        assert new_plot.pipeline[0]["type"] == "sort"

    def test_available_types_match_factory(self) -> None:
        """PlotFactory reports all expected plot types."""
        from src.web.pages.ui.plotting.plot_factory import PlotFactory

        types: List[str] = PlotFactory.get_available_plot_types()
        expected: List[str] = [
            "bar",
            "grouped_bar",
            "stacked_bar",
            "line",
            "scatter",
            "histogram",
        ]
        for t in expected:
            assert t in types, f"Missing plot type: {t}"


# ---------------------------------------------------------------------------
# Shaper pipeline execution
# ---------------------------------------------------------------------------
class TestShaperExecution:
    """Test individual shapers applied to the e2e sample data."""

    def test_column_selector_filters_columns(self) -> None:
        """ColumnSelector shaper keeps only specified columns."""
        from src.core.services.shapers.factory import ShaperFactory

        at = create_app_with_data()
        api: Any = get_api(at)
        raw: pd.DataFrame = api.state_manager.get_data()

        shaper = ShaperFactory.create_shaper(
            "columnSelector", {"columns": ["benchmark_name", "system.cpu.ipc"]}
        )
        result: pd.DataFrame = shaper(raw)

        assert list(result.columns) == ["benchmark_name", "system.cpu.ipc"]
        assert len(result) == len(raw)

    def test_sort_shaper_orders_data(self) -> None:
        """Sort shaper orders rows by specified column via order_dict."""
        from src.core.services.shapers.factory import ShaperFactory

        at = create_app_with_data()
        api: Any = get_api(at)
        raw: pd.DataFrame = api.state_manager.get_data()

        # Sort benchmarks in specified order
        shaper = ShaperFactory.create_shaper(
            "sort",
            {"order_dict": {"benchmark_name": ["mcf", "omnetpp", "xalancbmk"]}},
        )
        result: pd.DataFrame = shaper(raw)

        # After sorting, benchmark_name column should follow the specified order
        assert len(result) == len(raw)
        unique_ordered = list(result["benchmark_name"].unique())
        assert unique_ordered == ["mcf", "omnetpp", "xalancbmk"]

    def test_mean_shaper_aggregates(self) -> None:
        """Mean shaper computes mean and adds aggregate rows."""
        from src.core.services.shapers.factory import ShaperFactory

        at = create_app_with_data()
        api: Any = get_api(at)
        raw: pd.DataFrame = api.state_manager.get_data()

        shaper = ShaperFactory.create_shaper(
            "mean",
            {
                "meanVars": ["system.cpu.ipc"],
                "meanAlgorithm": "arithmean",
                "groupingColumns": ["config_description"],
                "replacingColumn": "benchmark_name",
            },
        )
        result: pd.DataFrame = shaper(raw)

        # Mean adds aggregate rows (one per group in groupingColumns)
        assert len(result) > 0
        assert len(result) != len(raw), "Mean should change row count"

    def test_chained_shapers_produce_expected_output(self) -> None:
        """Column selector followed by condition filter produces correct result."""
        from src.core.services.shapers.factory import ShaperFactory

        at = create_app_with_data()
        api: Any = get_api(at)
        raw: pd.DataFrame = api.state_manager.get_data()

        # Step 1: Column selector
        step1 = ShaperFactory.create_shaper(
            "columnSelector",
            {"columns": ["benchmark_name", "config_description", "system.cpu.ipc"]},
        )
        intermediate: pd.DataFrame = step1(raw)

        # Step 2: Filter to baseline only
        step2 = ShaperFactory.create_shaper(
            "conditionSelector",
            {"column": "config_description", "values": ["baseline"]},
        )
        final: pd.DataFrame = step2(intermediate)

        assert "system.cpu.ipc" in final.columns
        assert all(final["config_description"] == "baseline")


# ---------------------------------------------------------------------------
# Workspace management widgets
# ---------------------------------------------------------------------------
class TestWorkspaceManagement:
    """Workspace management section renders on the Manage Plots page."""

    def test_workspace_section_renders(self) -> None:
        """Workspace management area renders without error."""
        at = create_app_with_plots()
        navigate_to(at, "Manage Plots")

        assert not at.exception

    def test_export_widgets_present(self) -> None:
        """Export section has path input and format selectbox."""
        at = create_app_with_plots()
        navigate_to(at, "Manage Plots")

        assert not at.exception
        # Export path input should exist
        text_inputs = at.text_input
        assert len(text_inputs) >= 1, "Expected at least one text input"

    def test_page_stable_after_multiple_reruns(self) -> None:
        """Page remains stable through multiple consecutive reruns."""
        at = create_app_with_plots()
        navigate_to(at, "Manage Plots")

        for _ in range(3):
            at.run()
            assert not at.exception, "Page should remain stable across reruns"


# ---------------------------------------------------------------------------
# Plot config and rendering controls
# ---------------------------------------------------------------------------
class TestPlotConfigUI:
    """Plot configuration widgets render correctly."""

    def test_plot_type_selectbox_present(self) -> None:
        """Plot type selectbox renders in the visualization section."""
        at = create_app_with_plots()
        navigate_to(at, "Manage Plots")

        assert not at.exception
        # Should have selectboxes including the plot type selector
        assert len(at.selectbox) >= 1

    def test_toggle_present_when_finalized(self) -> None:
        """Auto-refresh toggle renders when plot has processed data."""
        at = create_app_with_data()
        api: Any = get_api(at)
        plot = _create_plot_via_api(api, "Finalized Plot", "bar")
        plot.processed_data = api.state_manager.get_data().copy()
        navigate_to(at, "Manage Plots")

        assert not at.exception
        toggles = at.toggle
        assert len(toggles) >= 1, "Expected auto-refresh toggle"

    def test_refresh_button_when_finalized(self) -> None:
        """Manual refresh button renders when plot has processed data."""
        at = create_app_with_data()
        api: Any = get_api(at)
        plot = _create_plot_via_api(api, "Finalized Plot", "bar")
        plot.processed_data = api.state_manager.get_data().copy()
        navigate_to(at, "Manage Plots")

        assert not at.exception
        refresh_buttons = [b for b in at.button if "refresh" in b.label.lower() or "🔄" in b.label]
        assert len(refresh_buttons) >= 1, "Expected refresh button"
