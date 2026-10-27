"""Real plot-selector widgets keep UI and domain identity synchronized."""

from textwrap import dedent
from typing import cast

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.core.application_api import ApplicationAPI
from src.web.pages.ui.plotting.plot_service import PlotService
from tests.ui.helpers import plot_widget_key

_APP = dedent("""
    import pandas as pd
    import streamlit as st
    from src.core.application_api import ApplicationAPI
    from src.core.models.workspace_metadata_models import WorkspaceArtifact
    from src.core.models.workspace_search_models import WorkspaceSearchResult
    from src.web.components.workspace_organizer import WorkspaceOrganizerComponent
    from src.web.components.workspace_search import WorkspaceSearchComponent
    from src.web.controllers.plot.creation_controller import PlotCreationController
    from src.web.pages.plot_adapters import PlotLifecycleAdapter, PlotTypeRegistryAdapter
    from src.web.pages.ui.plotting.plot_service import PlotService
    from src.web.state.ui_state_manager import UIStateManager

    frame = pd.DataFrame({"kind": ["a", "b"], "metric": [3.0, 5.0]})
    ui = UIStateManager()
    if "api" not in st.session_state:
        api = ApplicationAPI()
        api.state_manager.set_data(frame)
        for name in ("Alpha", "Beta"):
            PlotService.create_plot(name, "bar", api.state_manager)
        api.state_manager.set_current_plot_id(0)
        st.session_state["api"] = api
    api = st.session_state["api"]
    if st.button("Open first through search"):
        plot = api.state_manager.get_plots()[0]
        WorkspaceSearchComponent.activate(api, WorkspaceSearchResult(
            kind="plot", identifier=str(plot.plot_id), title=plot.name,
            description="Select the first plot", location="Manage Plots",
            score=100, matched_terms=(),
        ))
        st.rerun()
    if st.button("Open last through organizer"):
        plot = api.state_manager.get_plots()[-1]
        WorkspaceOrganizerComponent.activate(api, WorkspaceArtifact(
            "plot", str(plot.plot_id), plot.name,
        ))
        st.rerun()
    if st.button("Replace workspace"):
        api.reset_session()
        ui.cleanup_all()
        api.state_manager.set_data(frame)
        PlotService.create_plot("Restored", "bar", api.state_manager)
        st.rerun()
    for plot in api.state_manager.get_plots():
        if plot.source_data is None:
            plot.replace_source_data(frame)
            plot.replace_processed_data(frame)
    controller = PlotCreationController(
        api, ui, PlotLifecycleAdapter(), PlotTypeRegistryAdapter(),
    )
    controller.render_create_section()
    selected = controller.render_selector()
    if selected is not None:
        controller.render_controls(selected)
        st.session_state["rendered_plot_id"] = selected.plot_id
""")


def _app() -> AppTest:
    """Run the real lifecycle controller without figures or background work."""
    return AppTest.from_string(_APP).run()


def test_creation_rename_duplicate_and_delete_keep_exact_selection() -> None:
    """Lifecycle actions select their actual plot without another user click."""
    # [test->req~ring5.plots.create-multiple~1]
    # [test->req~ring5.plots.rename~1]
    # [test->req~ring5.plots.duplicate~1]
    # [test->req~ring5.plots.delete~1]
    app = _app()
    api = cast(ApplicationAPI, app.session_state["api"])
    try:
        assert not app.exception
        app.text_input(key="new_plot_name").set_value("Created")
        app.selectbox(key="new_plot_type").set_value("bar")
        next(button for button in app.button if button.label == "Create Plot").click().run()
        assert not app.exception
        created_id = api.state_manager.get_current_plot_id()
        assert created_id == 2
        selector = app.pills(key=plot_widget_key(app, created_id, "selector"))
        assert selector.value == created_id
        assert selector.formatted_values == ["Created"]
        assert selector.proto.required and selector.proto.set_value
        original_selector_id = selector.id
        app.text_input(key=plot_widget_key(app, created_id, "widgets.rename")).set_value(
            "Renamed"
        ).run()
        assert not app.exception
        selector = app.pills(key=plot_widget_key(app, created_id, "selector"))
        assert selector.id == original_selector_id
        assert selector.value == api.state_manager.get_current_plot_id() == created_id
        assert selector.formatted_values == ["Renamed"] and selector.proto.set_value
        original = api.state_manager.get_plots()[-1]
        expected = pd.DataFrame({"kind": ["a", "b"], "metric": [3.0, 5.0]})
        next(button for button in app.button if button.label == "Duplicate").click().run()
        assert not app.exception
        duplicate = api.state_manager.get_plots()[-1]
        assert duplicate.plot_id == 3 and duplicate.name == "Renamed (copy)"
        assert api.state_manager.get_current_plot_id() == duplicate.plot_id
        selector = app.pills(key=plot_widget_key(app, duplicate.plot_id, "selector"))
        assert selector.value == duplicate.plot_id
        assert selector.formatted_values == ["Renamed (copy)"] and selector.proto.set_value
        assert duplicate.processed_data is not None and original.processed_data is not None
        pd.testing.assert_frame_equal(duplicate.processed_data, expected)
        pd.testing.assert_frame_equal(original.processed_data, expected)
        assert duplicate.processed_data is not original.processed_data
        next(button for button in app.button if button.label == "Delete").click().run()
        assert not app.exception
        assert len(api.state_manager.get_plots()) == 3
        assert original in api.state_manager.get_plots()
        assert all(plot.plot_id != duplicate.plot_id for plot in api.state_manager.get_plots())
        assert api.state_manager.get_current_plot_id() == 0
        assert app.pills(key=plot_widget_key(app, 0, "selector")).value == 0
        assert app.session_state["rendered_plot_id"] == 0
        loaded = api.state_manager.get_data()
        assert loaded is not None
        pd.testing.assert_frame_equal(loaded, expected)
    finally:
        api.close()


def test_user_selection_retires_only_old_key_before_workspace_activation() -> None:
    """A changed user choice cannot override the next programmatic activation."""
    # [test->req~ring5.plots.create-multiple~1]
    app = _app()
    api = cast(ApplicationAPI, app.session_state["api"])
    try:
        assert not app.exception
        old_key = plot_widget_key(app, 0, "selector")
        app.session_state["plot.0.figure"] = "owned native artifact"
        app.session_state["plot.0.widgets.appearance.title"] = "Unchanged"
        app.session_state["plot.1.transfer_notice"] = "Another plot"
        app.pills(key=old_key).set_value(1).run()
        assert not app.exception
        assert api.state_manager.get_current_plot_id() == 1
        assert app.pills(key=plot_widget_key(app, 1, "selector")).value == 1
        assert app.session_state["rendered_plot_id"] == 1
        assert old_key not in app.session_state
        assert app.session_state["plot.0.figure"] == "owned native artifact"
        assert app.session_state["plot.0.widgets.appearance.title"] == "Unchanged"
        assert app.session_state["plot.1.transfer_notice"] == "Another plot"
        next(
            button for button in app.button if button.label == "Open first through search"
        ).click().run()
        assert not app.exception
        assert api.state_manager.get_current_plot_id() == 0
        assert app.pills(key=plot_widget_key(app, 0, "selector")).formatted_values == ["Alpha"]
        next(
            button for button in app.button if button.label == "Open last through organizer"
        ).click().run()
        assert not app.exception
        assert api.state_manager.get_current_plot_id() == 1
        app.pills(key=plot_widget_key(app, 1, "selector")).set_value(0).run()
        assert not app.exception
        assert api.state_manager.get_current_plot_id() == 0
        assert app.pills(key=plot_widget_key(app, 0, "selector")).value == 0
        assert app.session_state["rendered_plot_id"] == 0
    finally:
        api.close()


def test_duplicate_labels_and_renaming_preserve_integer_identity() -> None:
    """Names and generated suffixes never determine which plot is selected."""
    # [test->req~ring5.plots.create-multiple~1]
    # [test->req~ring5.plots.rename~1]
    app = _app()
    api = cast(ApplicationAPI, app.session_state["api"])
    try:
        plots = api.state_manager.get_plots()
        plots[0].name = plots[1].name = "X"
        third = PlotService.create_plot("X (2)", "bar", api.state_manager)
        app.run()
        assert not app.exception
        selector = app.pills(key=plot_widget_key(app, third.plot_id, "selector"))
        assert selector.options == ["X", "X (3)", "X (2)"]
        assert selector.value == third.plot_id
        selector.set_value(1).run()
        assert not app.exception
        selector = app.pills(key=plot_widget_key(app, 1, "selector"))
        assert selector.value == api.state_manager.get_current_plot_id() == 1
        assert selector.formatted_values == ["X (3)"]
        original_id = selector.id
        app.text_input(key=plot_widget_key(app, 1, "widgets.rename")).set_value("Other").run()
        assert not app.exception
        selector = app.pills(key=plot_widget_key(app, 1, "selector"))
        assert selector.id == original_id and selector.value == 1
        assert selector.formatted_values == ["Other"]
        plots[0].name = "Other"
        app.run()
        assert not app.exception
        selector = app.pills(key=plot_widget_key(app, 1, "selector"))
        assert selector.options == ["Other", "Other (2)", "X (2)"]
        assert selector.id == original_id and selector.value == 1
        assert selector.formatted_values == ["Other (2)"] and selector.proto.set_value
    finally:
        api.close()


def test_workspace_replacement_reuses_id_and_pushes_its_new_label() -> None:
    """Same-view replacement sends the current label despite reused widget identity."""
    # [test->req~ring5.workspace.reset~1]
    app = _app()
    api = cast(ApplicationAPI, app.session_state["api"])
    try:
        assert not app.exception
        selector = app.pills(key=plot_widget_key(app, 0, "selector"))
        original_id = selector.id
        assert selector.value == 0 and selector.formatted_values == ["Alpha"]
        next(button for button in app.button if button.label == "Replace workspace").click().run()
        assert not app.exception
        selector = app.pills(key=plot_widget_key(app, 0, "selector"))
        assert selector.id == original_id
        assert selector.value == api.state_manager.get_current_plot_id() == 0
        assert selector.formatted_values == ["Restored"]
        assert selector.proto.required and selector.proto.set_value
        assert list(selector.proto.raw_values) == ["Restored"]
        assert app.session_state["rendered_plot_id"] == 0
        loaded = api.state_manager.get_data()
        assert loaded is not None
        pd.testing.assert_frame_equal(
            loaded,
            pd.DataFrame({"kind": ["a", "b"], "metric": [3.0, 5.0]}),
        )
    finally:
        api.close()
