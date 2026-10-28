"""Exercise the default tutorial entry point in an actual Streamlit session."""

from tests.ui.helpers import create_app, create_app_with_data, get_api


def test_default_offer_loads_complete_editable_tutorial() -> None:
    # [test->req~ring5.portfolio.bundled-example~1]
    app = create_app()
    assert not app.exception
    assert get_api(app).state_manager.get_data() is None
    button = next(button for button in app.button if button.label == "Load example portfolio")
    button.click().run(timeout=30)
    assert not app.exception
    api = get_api(app)
    assert api.state_manager.has_data()
    assert len(api.state_manager.get_plots()) == 17
    assert app.session_state["nav.current_page"] == "Manage Plots"
    assert any("Manage Plots" in heading.value for heading in app.markdown)
    assert not any(button.label == "Load example portfolio" for button in app.button)


def test_loaded_user_data_has_no_replace_with_example_action() -> None:
    app = create_app_with_data()
    app.run()
    assert not app.exception
    assert not any(button.label == "Load example portfolio" for button in app.button)
