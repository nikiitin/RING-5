"""Transient UI ownership, scoped resets and current state accessors."""

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest

from src.web.state.ui_state_manager import ParseCompletionNotice, UIStateManager, WidgetKeyBuilder


@pytest.fixture
def mock_state() -> Generator[dict[Any, Any]]:
    """Provide isolated state to the actual ownership boundary."""
    with patch("src.web.state.ui_state_manager.st") as mock_st:
        state: dict[Any, Any] = {}
        mock_st.session_state = state
        yield state


@pytest.fixture
def ui_state(mock_state: dict[Any, Any]) -> UIStateManager:
    return UIStateManager()


class TestPlotUIState:
    """The actual toggle is the sole auto-refresh value."""

    def test_auto_refresh_default_true(self, ui_state: UIStateManager) -> None:
        assert ui_state.plot.get_auto_refresh(1) is True

    def test_auto_refresh_per_plot_isolation(
        self, ui_state: UIStateManager, mock_state: dict[Any, Any]
    ) -> None:
        # [test->req~ring5.plots.independent-state~1]
        mock_state[WidgetKeyBuilder.plot_key(1, "widgets.auto_refresh")] = False
        mock_state[WidgetKeyBuilder.plot_key(2, "widgets.auto_refresh")] = True
        assert ui_state.plot.get_auto_refresh(1) is False
        assert ui_state.plot.get_auto_refresh(2) is True


@pytest.mark.parametrize("plot_id", [0, 1, 10, 42])
def test_delete_cleans_exact_plot_namespace(
    ui_state: UIStateManager, mock_state: dict[Any, Any], plot_id: int
) -> None:
    prefix = f"plot.{plot_id}."
    mock_state.update(
        {
            prefix + "widgets.rename": "Old name",
            prefix + "widgets.pipeline.filter_2": "Old column",
            prefix + "drill_down.result": object(),
            "plot.101.widgets.rename": "Other plot",
            "manager.mixer.col": "source",
            "ring5_engine_mode": "matplotlib",
            "_recovery_last_capture_at": 1.0,
            f"plot.{plot_id}": "outside namespace",
            3: "non-text key",
        }
    )
    expected = {key: value for key, value in mock_state.items() if not str(key).startswith(prefix)}
    ui_state.plot.cleanup(plot_id)
    assert mock_state == expected
    assert ui_state.plot.get_auto_refresh(plot_id) is True
    ui_state.plot.cleanup(plot_id)
    assert mock_state == expected


def test_widget_reset_preserves_artifacts_markers_other_plots_and_preferences(
    ui_state: UIStateManager, mock_state: dict[Any, Any]
) -> None:
    native = object()
    spec = object()
    mock_state.update(
        {
            "plot.2.widgets.title": "old",
            "plot.2.widgets.appearance.theme_color_1_hash": "red",
            "plot.2.widgets.pipeline.filter_1": "old",
            "plot.2.mpl_fig": native,
            "plot.2.mpl_spec": spec,
            "plot.2.transfer_notice": "Copied settings",
            "plot.1.widgets.pipeline.filter_2": "source",
            "plot.1.widgets.appearance.theme_color_2_hash": "blue",
            "ring5_engine_mode": "matplotlib",
        }
    )
    expected = {
        key: value for key, value in mock_state.items() if not key.startswith("plot.2.widgets.")
    }
    previous_title_key = WidgetKeyBuilder.plot_key(2, "widgets.title")
    ui_state.plot.reset_widgets(2)
    expected["plot.2.widget_generations"] = mock_state["plot.2.widget_generations"]
    assert mock_state == expected
    assert WidgetKeyBuilder.plot_key(2, "widgets.title") != previous_title_key
    assert mock_state["plot.2.mpl_fig"] is native
    assert mock_state["plot.2.mpl_spec"] is spec


def test_appearance_reset_preserves_data_controls_and_theme_exchange_widgets(
    ui_state: UIStateManager, mock_state: dict[Any, Any]
) -> None:
    mock_state.update(
        {
            "plot.1.widgets.appearance.theme_color_2_hash": "red",
            "plot.1.widgets.appearance.x_grid_color": "blue",
            "plot.1.widgets.theme.apply_figure_theme": True,
            "plot.1.widgets.theme.import_figure_theme": b"theme",
            "plot.1.widgets.x": "benchmark",
            "plot.1.widgets.auto_refresh": False,
            "plot.2.widgets.appearance.theme_color_1_hash": "green",
        }
    )
    expected = {
        key: value
        for key, value in mock_state.items()
        if not key.startswith("plot.1.widgets.appearance.")
    }
    previous_color_key = WidgetKeyBuilder.plot_key(1, "widgets.appearance.theme_color_2_hash")
    ui_state.plot.reset_widgets(1, "appearance")
    expected["plot.1.widget_generations"] = mock_state["plot.1.widget_generations"]
    assert mock_state == expected
    assert (
        WidgetKeyBuilder.plot_key(1, "widgets.appearance.theme_color_2_hash") != previous_color_key
    )


def test_manager_history_consumes_only_its_owned_entry(
    ui_state: UIStateManager, mock_state: dict[Any, Any]
) -> None:
    record = {"manager_name": "Outlier Remover", "source_columns": ["ipc"]}
    mock_state[WidgetKeyBuilder.manager_key("outlier_remover", "load_trigger")] = record
    mock_state[WidgetKeyBuilder.manager_key("mixer", "load_trigger")] = {"other": True}
    assert ui_state.manager.consume_load_trigger("outlier_remover") is record
    assert ui_state.manager.consume_load_trigger("outlier_remover") is None
    assert mock_state["manager.mixer.load_trigger"] == {"other": True}


def test_navigation_is_shared_across_accessors(ui_state: UIStateManager) -> None:
    assert ui_state.nav.get_current_page() is None
    ui_state.nav.set_current_page("Manage Plots")
    assert UIStateManager().nav.get_current_page() == "Manage Plots"


def test_workspace_reset_preserves_browser_owner_api_and_engine_preferences(
    ui_state: UIStateManager, mock_state: dict[Any, Any]
) -> None:
    api = object()
    retained = {
        "api": api,
        "ring5_engine_mode": "matplotlib",
        "_recovery_last_capture_at": 1.0,
        3: True,
    }
    mock_state.update(retained)
    ui_state.plot.reset_widgets(1)
    mock_state.update(
        {
            "plot.1.widgets.title": "old",
            "manager.mixer.col": "ipc",
            "nav.current_page": "Manage Plots",
            "parse.active_job_id": "running",
            "parse.completion": ParseCompletionNotice("old", "Loaded parsed CSV from Recent"),
        }
    )
    ui_state.cleanup_all()
    assert mock_state == {**retained, "data_source.widget_generation": 1}
    assert mock_state["api"] is api


def test_replacement_discards_data_source_projections_without_touching_global_owners(
    ui_state: UIStateManager, mock_state: dict[Any, Any]
) -> None:
    retained = {
        "api": object(),
        "ring5_engine_mode": "matplotlib",
        "_recovery_last_capture_at": 1.0,
    }
    owned = {
        "data_source_choice": "Upload data or portfolio",
        "stats_path_input": "/retired/results",
        "stats_pattern_input": "retired.stats",
        "parser_strategy_selector": "config_aware",
        "simulator_selector": "retired_backend",
        "parser_incremental_enabled": False,
        "data_source.import_types.old_hash": {"edited": True},
        "data_source.remote.bearer_token": "retired-secret",
        "data_source.browser_upload": object(),
        "var_name_old_id": "retired.stat",
        "var_alias_old_id": "retired alias",
        "var_source_type_old_id": "vector",
        "dist_bucket_size_old_id": 2.0,
        "vector_entries_select_old_id__search": "retired search",
        "use_pattern_filter_old_id": True,
        "pattern_entries_old_id": ["retired.source"],
        "config_onempty_old_id": "retired fallback",
        "dialog_manual_name": "retired dialog",
        "adv_repeat": 4,
    }
    mock_state.update(retained)
    mock_state.update(owned)

    ui_state.cleanup_all()

    assert mock_state == {**retained, "data_source.widget_generation": 1}


def test_parse_completion_is_shared_but_not_consumed_by_another_accessor(
    ui_state: UIStateManager,
) -> None:
    # [test->req~ring5.ingestion.session-background-parse~1]
    notice = ParseCompletionNotice("job-1", "Loaded parsed CSV from Recent")
    ui_state.parse.remember_job("job-1")
    ui_state.parse.complete_job(notice)

    assert ui_state.parse.get_job_id() is None
    assert ui_state.parse.get_completion() is notice
    ui_state.nav.set_current_page("Data Managers")
    assert UIStateManager().parse.get_completion() is notice
    assert UIStateManager().parse.get_completion() is notice


def test_new_parse_attempt_clears_only_the_prior_completion_notice(
    ui_state: UIStateManager, mock_state: dict[Any, Any]
) -> None:
    notice = ParseCompletionNotice("job-1", "Loaded parsed CSV from Recent")
    ui_state.parse.complete_job(notice)
    mock_state["ring5_engine_mode"] = "matplotlib"
    ui_state.parse.remember_job("job-2")

    assert ui_state.parse.get_job_id() == "job-2"
    assert ui_state.parse.get_completion() is None
    assert mock_state["ring5_engine_mode"] == "matplotlib"
    ui_state.parse.forget_job("job-1")
    assert ui_state.parse.get_job_id() == "job-2"
    ui_state.parse.forget_job("job-2")
    assert ui_state.parse.get_job_id() is None


def test_workspace_restore_discards_a_previous_parse_notice(
    ui_state: UIStateManager, mock_state: dict[Any, Any]
) -> None:
    # [test->req~ring5.ingestion.session-background-parse~1]
    ui_state.parse.complete_job(ParseCompletionNotice("job-1", "Loaded parsed CSV from Recent"))
    mock_state["api"] = object()
    ui_state.cleanup_all()

    assert ui_state.parse.get_completion() is None
    assert ui_state.parse.get_job_id() is None
    assert set(mock_state) == {"api", "data_source.widget_generation"}


def test_widget_identities_are_stable_until_their_owned_scope_resets(
    ui_state: UIStateManager, mock_state: dict[Any, Any]
) -> None:
    suffixes = (
        "widgets.title",
        "widgets.engine_selector",
        "widgets.pipeline.filter_1",
        "widgets.appearance.theme_color",
    )
    initial = {suffix: WidgetKeyBuilder.plot_key(1, suffix) for suffix in suffixes}
    assert initial == {suffix: f"plot.1.{suffix}" for suffix in suffixes}
    assert {suffix: WidgetKeyBuilder.plot_key(1, suffix) for suffix in suffixes} == initial
    assert mock_state == {}

    ui_state.plot.reset_widgets(1)
    for suffix in suffixes:
        current = WidgetKeyBuilder.plot_key(1, suffix)
        assert current == initial[suffix] + ".__reset_1"
        assert WidgetKeyBuilder.plot_key(1, suffix) == current
        assert WidgetKeyBuilder.plot_key(2, suffix) == f"plot.2.{suffix}"
    assert WidgetKeyBuilder.plot_key(1, "transfer_notice") == "plot.1.transfer_notice"
    assert WidgetKeyBuilder.plot_key(1, "widgets") == "plot.1.widgets"
    assert WidgetKeyBuilder.manager_key("mixer", "mode") == "manager.mixer.mode"


def test_nested_and_sibling_widget_resets_use_the_latest_applicable_generation(
    ui_state: UIStateManager, mock_state: dict[Any, Any]
) -> None:
    suffixes = {
        "title": "widgets.title",
        "theme": "widgets.theme.import_figure_theme",
        "draft": "widgets.appearance.shape_editor",
        "row": "widgets.appearance.shape_rows.edit_x0_0",
        "series": "widgets.appearance.series",
        "unrelated": "widgets.appearance_extra.control",
    }
    row_key = WidgetKeyBuilder.plot_key(1, suffixes["row"])
    draft = object()
    mock_state[row_key] = "old coordinate"
    mock_state[WidgetKeyBuilder.plot_key(1, suffixes["draft"])] = draft

    steps: tuple[tuple[tuple[str, ...], dict[str, int]], ...] = (
        (("appearance", "shape_rows"), {"row": 1}),
        (("appearance", "series"), {"row": 1, "series": 2}),
        (("appearance", "shape_rows"), {"row": 3, "series": 2}),
        (("appearance",), {"draft": 4, "row": 4, "series": 4}),
        (("appearance", "shape_rows"), {"draft": 4, "row": 5, "series": 4}),
        ((), dict.fromkeys(suffixes, 6)),
        (("appearance", "series"), {**dict.fromkeys(suffixes, 6), "series": 7}),
    )
    for index, (sections, expected) in enumerate(steps):
        ui_state.plot.reset_widgets(1, *sections)
        for name, suffix in suffixes.items():
            generation = expected.get(name, 0)
            physical = f"plot.1.{suffix}"
            if generation:
                physical += f".__reset_{generation}"
            assert WidgetKeyBuilder.plot_key(1, suffix) == physical
            assert WidgetKeyBuilder.plot_key(2, suffix) == f"plot.2.{suffix}"
        if index == 0:
            assert row_key not in mock_state
            assert mock_state[WidgetKeyBuilder.plot_key(1, suffixes["draft"])] is draft


def test_widget_reset_cleans_all_generated_descendants_and_cleanup_discards_epochs(
    ui_state: UIStateManager, mock_state: dict[Any, Any]
) -> None:
    ui_state.plot.reset_widgets(1, "appearance")
    generated_prefix = WidgetKeyBuilder.plot_key(1, "widgets.appearance.series") + "."
    mock_state[generated_prefix + "color_A"] = "red"
    mock_state[WidgetKeyBuilder.plot_key(1, "widgets.title")] = "Retained title"
    mock_state["plot.2.widgets.title"] = "Other plot"
    ui_state.plot.reset_widgets(1, "appearance")
    assert generated_prefix + "color_A" not in mock_state
    assert mock_state[WidgetKeyBuilder.plot_key(1, "widgets.title")] == "Retained title"
    assert mock_state["plot.2.widgets.title"] == "Other plot"

    ui_state.plot.cleanup(1)
    assert mock_state == {"plot.2.widgets.title": "Other plot"}
    assert WidgetKeyBuilder.plot_key(1, "widgets.appearance.series") == (
        "plot.1.widgets.appearance.series"
    )


def test_data_source_keys_change_only_when_the_workspace_projection_is_retired(
    ui_state: UIStateManager, mock_state: dict[Any, Any]
) -> None:
    logical_keys = (
        "data_source_choice",
        "stats_path_input",
        "data_source.browser_upload",
        "data_source.remote.bearer_token",
        "var_name_saved_id",
        "dialog_manual_name",
        "pattern_entries_saved_id",
    )
    initial = {key: WidgetKeyBuilder.data_source_key(key) for key in logical_keys}
    assert initial == dict(zip(logical_keys, logical_keys, strict=True))
    mock_state["api"] = owner = object()
    mock_state["ring5_engine_mode"] = "matplotlib"
    for generation in (1, 2, 3):
        retired = {key: WidgetKeyBuilder.data_source_key(key) for key in logical_keys}
        mock_state.update({physical: "retired" for physical in retired.values()})
        ui_state.cleanup_all()
        for logical, previous in retired.items():
            physical = WidgetKeyBuilder.data_source_key(logical)
            assert physical == f"{logical}.__reset_{generation}"
            assert physical != previous
            assert WidgetKeyBuilder.data_source_key(logical) == physical
            assert previous not in mock_state
        assert mock_state["api"] is owner
        assert mock_state["ring5_engine_mode"] == "matplotlib"
        assert mock_state["data_source.widget_generation"] == generation


def test_manager_success_notice_is_consumed_once_within_its_owner(
    ui_state: UIStateManager, mock_state: dict[Any, Any]
) -> None:
    ui_state.manager.set_success_notice("schema_contract", "Converted latency to s")
    ui_state.manager.set_success_notice("mixer", "Mixed columns")

    assert UIStateManager().manager.consume_success_notice("schema_contract") == (
        "Converted latency to s"
    )
    assert ui_state.manager.consume_success_notice("schema_contract") is None
    assert mock_state == {"manager.mixer.success_notice": "Mixed columns"}

    ui_state.cleanup_all()
    assert ui_state.manager.consume_success_notice("mixer") is None
