"""Transient UI ownership, scoped resets and current state accessors."""

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest

from src.web.state.ui_state_manager import UIStateManager, WidgetKeyBuilder


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
    ui_state.plot.reset_widgets(2)
    assert mock_state == expected
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
    ui_state.plot.reset_widgets(1, "appearance")
    assert mock_state == expected


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
    mock_state.update(
        {
            "plot.1.widgets.title": "old",
            "manager.mixer.col": "ipc",
            "nav.current_page": "Manage Plots",
        }
    )
    ui_state.cleanup_all()
    assert mock_state == retained
    assert mock_state["api"] is api
