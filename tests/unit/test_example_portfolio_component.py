"""The tutorial offer never replaces existing browser analysis."""

from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import pytest

from src.core.models.portfolio_models import RestoreReport
from src.core.models.parsing_models import default_parse_configs
from src.core.common.stat_config_codec import StatConfigCodec
from src.core.application_api import ApplicationAPI
from src.web.components.example_portfolio import render_example_portfolio


def empty_api() -> MagicMock:
    api = MagicMock()
    api.state_manager.has_data.return_value = False
    api.state_manager.get_plots.return_value = []
    api.list_datasets.return_value = ()
    api.state_manager.get_parse_variables.return_value = [
        StatConfigCodec.to_draft(config, f"preset-{index}")
        for index, config in enumerate(default_parse_configs())
    ]
    api.state_manager.get_scanned_variables.return_value = []
    api.state_manager.get_config.return_value = {}
    api.state_manager.get_stats_path.return_value = "/path/to/stats"
    api.state_manager.get_stats_pattern.return_value = "stats.txt"
    api.state_manager.get_parser_strategy.return_value = "simple"
    api.state_manager.get_simulator.return_value = "gem5"
    api.get_active_parse_job.return_value = None
    api.list_background_jobs.return_value = ()
    api.can_load_example_portfolio.side_effect = lambda: ApplicationAPI.can_load_example_portfolio(
        api
    )
    return api


@pytest.mark.parametrize("work", ["data", "plots", "datasets", "drafts", "scanned", "job"])
@patch("src.web.components.example_portfolio.st")
def test_existing_work_hides_the_example_action(st: MagicMock, work: str) -> None:
    # [test->req~ring5.portfolio.bundled-example~1]
    api = empty_api()
    if work == "data":
        api.state_manager.has_data.return_value = True
    elif work == "plots":
        api.state_manager.get_plots.return_value = [object()]
    elif work == "datasets":
        api.list_datasets.return_value = (object(),)
    elif work == "drafts":
        api.state_manager.get_parse_variables.return_value = [{"name": "authored draft"}]
    elif work == "scanned":
        api.state_manager.get_scanned_variables.return_value = [object()]
    else:
        api.get_active_parse_job.return_value = object()
    render_example_portfolio(api)
    st.button.assert_not_called()
    api.load_example_portfolio.assert_not_called()


@patch("src.web.components.example_portfolio.st")
def test_rendering_the_offer_does_not_load_or_write(st: MagicMock) -> None:
    api = empty_api()
    st.button.return_value = False
    render_example_portfolio(api)
    api.load_example_portfolio.assert_not_called()


@patch("src.web.components.example_portfolio.st")
def test_editor_projection_keeps_untouched_presets_eligible(st: MagicMock) -> None:
    api = empty_api()
    drafts = api.state_manager.get_parse_variables.return_value
    for draft in drafts:
        draft.pop("source_name", None)
        if draft["type"] == "configuration":
            draft["params"]["on_empty"] = "None"
    st.button.return_value = False
    render_example_portfolio(api)
    st.button.assert_called_once()


@pytest.mark.parametrize(
    ("getter", "value"),
    [
        ("get_config", {"description": "My analysis"}),
        ("get_stats_path", "/my/results"),
        ("get_stats_pattern", "run.stats"),
        ("get_parser_strategy", "config_aware"),
        ("get_simulator", "other"),
    ],
)
def test_authored_workspace_settings_block_the_tutorial(getter: str, value: object) -> None:
    api = empty_api()
    getattr(api.state_manager, getter).return_value = value
    assert not api.can_load_example_portfolio()


@patch("src.web.components.example_portfolio.UIStateManager")
@patch("src.web.components.example_portfolio.st")
def test_explicit_load_restores_cleans_widgets_and_navigates(
    st: MagicMock, state: MagicMock
) -> None:
    api = empty_api()
    st.button.return_value = True
    api.load_example_portfolio.return_value = RestoreReport(data_restored=True, plots_restored=17)
    render_example_portfolio(api)
    api.load_example_portfolio.assert_called_once_with()
    state.return_value.cleanup_all.assert_called_once_with()
    state.return_value.nav.set_current_page.assert_called_once_with("Manage Plots")
    st.rerun.assert_called_once_with(scope="app")


@pytest.mark.parametrize("failure", ["read", "partial"])
@patch("src.web.components.example_portfolio.st")
def test_failed_restore_is_visible_without_success_navigation(st: MagicMock, failure: str) -> None:
    api = empty_api()
    st.button.return_value = True
    if failure == "read":
        api.load_example_portfolio.side_effect = ValueError("invalid tutorial checksum")
    else:
        api.load_example_portfolio.return_value = RestoreReport(plots_skipped=["invalid plot"])
    render_example_portfolio(api)
    st.error.assert_called_once()
    st.toast.assert_not_called()
    st.rerun.assert_not_called()


@pytest.mark.parametrize("terminal", [False, True])
@patch("src.web.components.example_portfolio.st")
def test_background_work_blocks_offer_but_terminal_history_does_not(
    st: MagicMock, terminal: bool
) -> None:
    api = empty_api()
    api.list_background_jobs.return_value = (SimpleNamespace(terminal=terminal),)
    st.button.return_value = False
    render_example_portfolio(api)
    assert st.button.called is terminal
    api.load_example_portfolio.assert_not_called()


@patch("src.web.components.example_portfolio.UIStateManager")
@patch("src.web.components.example_portfolio.st")
def test_actual_partial_publication_has_bounded_details_and_widget_cleanup(
    st: MagicMock, state: MagicMock
) -> None:
    from src.core.application_api import ApplicationAPI
    from src.web.pages.ui.plotting.plot_factory import PlotFactory

    def deserialize(payload):
        if payload["id"] == 1:
            return None
        return PlotFactory.from_dict(payload)

    api = ApplicationAPI(plot_deserializer=deserialize)
    st.button.return_value = True
    try:
        assert api.can_load_example_portfolio()
        render_example_portfolio(api)
        assert api.state_manager.has_data()
        assert len(api.state_manager.get_plots()) == 16
        assert "Normalized IPC" in st.error.call_args.args[0]
        state.return_value.cleanup_all.assert_called_once_with()
        st.rerun.assert_not_called()
        st.toast.assert_not_called()
    finally:
        api.close(wait=True)
