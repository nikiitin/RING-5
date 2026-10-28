"""Reset and restore rebuild parser controls from the current domain configuration."""

from typing import cast

from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import ButtonGroup, Checkbox, TextInput

from src.core.application_api import ApplicationAPI
from src.core.common.stat_config_codec import StatConfigCodec
from src.core.models.parsing_models import default_parse_configs
from tests.ui.helpers import create_app, get_api, navigate_to


def _text_input(app: AppTest, label: str) -> TextInput:
    """Find the visible input independently of its reset generation."""
    return next(widget for widget in app.text_input if widget.label == label)


def _button_group(app: AppTest, label: str) -> ButtonGroup[str]:
    """Find the current segmented control by its accessible label."""
    return next(widget for widget in app.button_group if widget.label == label)


def _checkbox(app: AppTest, label: str) -> Checkbox:
    """Find the current checkbox by its accessible label."""
    return next(widget for widget in app.checkbox if widget.label == label)


def _configure(app: AppTest, name: str, path: str, pattern: str, strategy: str) -> None:
    """Author parser inputs through the real Data Source controls."""
    navigate_to(app, "Data Source")
    _text_input(app, "Stats directory path").set_value(path).run()
    _text_input(app, "File pattern").set_value(pattern).run()
    _button_group(app, "Select ingestion strategy:").set_value(strategy).run()
    _text_input(app, "Variable 1 Name").set_value(name).run()
    assert not app.exception


def test_reset_all_rebuilds_default_parser_inputs_and_retires_authored_widgets() -> None:
    # [test->req~ring5.workspace.reset~1]
    app = create_app()
    api = cast(ApplicationAPI, get_api(app))
    _configure(app, "authored.stat", "/authored/results", "custom.stats", "config_aware")
    old_ids = {variable["_id"] for variable in api.state_manager.get_parse_variables()}
    old_path_key = _text_input(app, "Stats directory path").key
    old_choice_key = _button_group(app, "Select your data source:").key
    _checkbox(app, "Reuse unchanged simulator files").set_value(False).run()
    next(widget for widget in app.checkbox if widget.label.startswith("Deep Scan (")).set_value(
        True
    ).run()
    _button_group(app, "Select your data source:").set_value("Load from Recent").run()

    next(button for button in app.sidebar.button if button.label == "Reset All").click().run()

    assert not app.exception
    assert get_api(app) is api
    assert _text_input(app, "Stats directory path").key != old_path_key
    assert _button_group(app, "Select your data source:").key != old_choice_key
    assert old_path_key not in app.session_state
    assert old_choice_key not in app.session_state
    assert api.state_manager.get_stats_path() == "/path/to/stats"
    assert api.state_manager.get_stats_pattern() == "stats.txt"
    assert api.state_manager.get_parser_strategy() == "simple"
    assert api.state_manager.get_simulator() == "gem5"
    assert _text_input(app, "Stats directory path").value == "/path/to/stats"
    assert _text_input(app, "File pattern").value == "stats.txt"
    assert _button_group(app, "Select ingestion strategy:").value == "simple"
    assert _button_group(app, "Select your data source:").value == "Parse gem5 Stats Files"
    assert _checkbox(app, "Reuse unchanged simulator files").value is True
    assert (
        next(widget for widget in app.checkbox if widget.label.startswith("Deep Scan (")).value
        is False
    )
    variables = api.state_manager.get_parse_variables()
    assert [StatConfigCodec.to_payload(StatConfigCodec.from_draft(item)) for item in variables] == [
        StatConfigCodec.to_payload(item) for item in default_parse_configs()
    ]
    assert not old_ids.intersection(variable["_id"] for variable in variables)
    for variable_id in old_ids:
        assert f"var_name_{variable_id}" not in app.session_state
        assert f"var_source_type_{variable_id}" not in app.session_state


def test_loading_a_configured_portfolio_rebuilds_saved_parser_controls() -> None:
    # [test->req~ring5.portfolio.restore~1]
    app = create_app()
    api = cast(ApplicationAPI, get_api(app))
    _configure(app, "saved.measurement", "/saved/results", "saved.stats", "config_aware")
    saved_variables = api.state_manager.get_parse_variables()
    navigate_to(app, "Save/Load Portfolio")
    app.text_input(key="portfolio_save_name").set_value("Configured parser")
    next(button for button in app.button if button.label == "Save Portfolio").click().run()
    assert not app.exception

    _configure(app, "unsaved.measurement", "/unsaved/results", "unsaved.stats", "simple")
    navigate_to(app, "Save/Load Portfolio")
    next(button for button in app.button if button.label == "Load Portfolio").click().run()
    assert not app.exception
    navigate_to(app, "Data Source")

    restored_variables = api.state_manager.get_parse_variables()
    assert [
        StatConfigCodec.to_payload(StatConfigCodec.from_draft(item)) for item in restored_variables
    ] == [StatConfigCodec.to_payload(StatConfigCodec.from_draft(item)) for item in saved_variables]
    assert api.state_manager.get_stats_path() == "/saved/results"
    assert api.state_manager.get_stats_pattern() == "saved.stats"
    assert api.state_manager.get_parser_strategy() == "config_aware"
    assert _text_input(app, "Stats directory path").value == "/saved/results"
    assert _text_input(app, "File pattern").value == "saved.stats"
    assert _button_group(app, "Select ingestion strategy:").value == "config_aware"
    assert _text_input(app, "Variable 1 Name").value == "saved.measurement"
    app.run()
    assert not app.exception
    assert api.state_manager.get_parse_variables() == restored_variables
    assert api.state_manager.get_stats_path() == "/saved/results"
