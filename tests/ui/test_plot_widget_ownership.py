"""Real widget lifecycle checks for plot ownership and exact scoped resets."""

from textwrap import dedent
from copy import deepcopy

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.web.pages.ui.plotting.plot_service import PlotService
from src.web.rendering.engine_manager import EngineManager
from tests.ui.helpers import create_app_with_data, get_api, navigate_to, plot_widget_key


def _app(body: str) -> AppTest:
    return AppTest.from_string("import streamlit as st\n" + dedent(body)).run()


def test_delete_then_reuse_plot_id_discards_rename_control() -> None:
    # [test->req~ring5.plots.independent-state~1]
    app = _app("""
        from src.core.application_api import ApplicationAPI
        from src.web.controllers.plot.creation_controller import PlotCreationController
        from src.web.pages.plot_adapters import PlotLifecycleAdapter, PlotTypeRegistryAdapter
        from src.web.pages.ui.plotting.plot_factory import PlotFactory
        from src.web.state.ui_state_manager import UIStateManager
        if "api" not in st.session_state:
            st.session_state["api"] = ApplicationAPI()
        api = st.session_state["api"]
        if not api.state_manager.get_plots():
            name = "New plot" if st.session_state.get("created") else "Old plot name"
            api.state_manager.add_plot(PlotFactory.create_plot("bar", 1, name))
            st.session_state["created"] = True
        plot = api.state_manager.get_plots()[0]
        PlotCreationController(api, UIStateManager(), PlotLifecycleAdapter(),
                               PlotTypeRegistryAdapter()).render_controls(plot)
        st.session_state["name"] = plot.name
    """)
    api = app.session_state["api"]
    try:
        assert not app.exception
        assert app.text_input[0].value == "Old plot name"
        next(button for button in app.button if button.label == "Delete").click().run()
        assert not app.exception
        assert app.text_input[0].value == "New plot"
        assert app.session_state["name"] == "New plot"
    finally:
        api.close()


def test_copy_target_preserves_another_plots_shaper_with_matching_numeric_id() -> None:
    # [test->req~ring5.plots.copy-settings-pipeline~1]
    app = _app("""
        import pandas as pd
        from src.core.application_api import ApplicationAPI
        from src.web.components.plotting.plot_transfer_panel import PlotTransferPanel
        from src.web.pages.ui.plotting.plot_factory import PlotFactory
        from src.web.pages.ui.shaper_config import configure_shaper
        data = pd.DataFrame({"kind": ["a", "b"], "metric": [3., 5.]})
        if "api" not in st.session_state:
            api = ApplicationAPI()
            source = PlotFactory.create_plot("bar", 1, "Source")
            target = PlotFactory.create_plot("bar", 2, "Target")
            for plot in [source, target]:
                plot.replace_processed_data(data)
                plot.replace_source_data(data)
                plot.config = {"x": "kind", "y": "metric", "title": plot.name}
            api.state_manager.set_plots([source, target])
            st.session_state["api"] = api
        api = st.session_state["api"]
        source, target = api.state_manager.get_plots()
        PlotTransferPanel.apply_pending_widget_reset(target.plot_id)
        emitted = configure_shaper("columnSelector", data, 2,
            {"type": "columnSelector", "columns": ["kind"]}, owner_id=1, display_names={})
        st.session_state["source_columns"] = emitted["columns"]
        PlotTransferPanel(api).render(target, [source, target])
        st.session_state["target_config"] = target.render_config_ui(data, target.config)
    """)
    api = app.session_state["api"]
    try:
        assert not app.exception
        app.multiselect[0].select("metric").run()
        assert app.session_state["source_columns"] == ["kind", "metric"]
        next(widget for widget in app.text_input if widget.label == "Title").set_value(
            "Unpublished target title"
        ).run()
        next(
            button for button in app.button if button.label == "Copy into current plot"
        ).click().run()
        assert not app.exception
        assert app.session_state["source_columns"] == ["kind", "metric"]
        assert app.session_state["target_config"]["title"] == "Source"
        assert app.session_state["api"].state_manager.get_plots()[0].config["title"] == "Source"
    finally:
        api.close()


def test_theme_apply_preserves_another_plots_pending_series_color() -> None:
    # [test->req~ring5.figure.theme-presets~1]
    app = _app("""
        from src.web.components.plotting.settings.colors_settings import ColorsSettingsComponent
        from src.web.components.plotting.settings.theme_presets_settings import (
            ThemePresetsSettingsComponent,
        )
        saved = {"series_styles": {"A": {"color": "#ff0000", "use_color": True},
                                   "B": {"color": "#0000ff", "use_color": True}}}
        st.session_state["series"] = ColorsSettingsComponent(2, "bar")._render_series_colors(
            saved, None, ["A", "B"], "theme_", "wong")
        st.session_state["theme"] = ThemePresetsSettingsComponent(1, "bar").render({})
    """)
    assert not app.exception
    [picker for picker in app.color_picker if picker.label == "Custom"][1].set_value(
        "#654321"
    ).run()
    assert app.session_state["series"]["B"]["color"] == "#654321"
    next(button for button in app.button if button.label == "Apply theme").click().run()
    app.run()
    assert not app.exception
    assert app.session_state["series"]["B"]["color"] == "#654321"
    assert [picker for picker in app.color_picker if picker.label == "Custom"][1].value == "#654321"


def test_shape_rows_edit_and_delete_without_an_unreachable_edit_mode() -> None:
    # [test->req~ring5.figure.shapes-annotations~1]
    app = _app("""
        from copy import deepcopy
        from src.web.components.plotting.settings.shapes_settings import ShapesSettingsComponent
        if "config" not in st.session_state:
            st.session_state["config"] = {"shapes": [
                {"type": "line", "x0": 1., "y0": 2., "x1": 3., "y1": 4.,
                 "line": {"color": "#000000", "width": 2}},
                {"type": "line", "x0": 30., "y0": 40., "x1": 50., "y1": 60.,
                 "line": {"color": "#000000", "width": 2}}]}
        saved = st.session_state["config"]
        before = deepcopy(saved)
        result = ShapesSettingsComponent(1, "bar").render(saved)
        st.session_state["immutable"] = saved == before
        st.session_state["config"] = {"shapes": result}
    """)
    assert not app.exception
    assert len(app.text_input) == 12
    app.text_input(
        key=plot_widget_key(app, 1, "widgets.appearance.shape_rows.edit_x0_0")
    ).set_value("12.5").run()
    assert app.session_state["immutable"]
    assert app.session_state["config"]["shapes"][0]["x0"] == 12.5
    app.button(
        key=plot_widget_key(app, 1, "widgets.appearance.shape_rows.del_shape_0")
    ).click().run()
    app.run()
    assert not app.exception
    assert app.session_state["immutable"]
    assert len(app.session_state["config"]["shapes"]) == 1
    assert app.session_state["config"]["shapes"][0]["x0"] == 30.0
    assert (
        app.text_input(key=plot_widget_key(app, 1, "widgets.appearance.shape_rows.edit_x0_0")).value
        == "30.0"
    )


@pytest.mark.parametrize("action", ["delete", "add", "coordinate"])
def test_shape_draft_survives_manual_refresh_and_settings_navigation(action: str) -> None:
    # [test->req~ring5.figure.shapes-annotations~1]
    # [test->req~ring5.plots.refresh-cache~1]
    app = create_app_with_data(pd.DataFrame({"kind": ["a"], "metric": [3.0]}))
    api = get_api(app)
    plot = PlotService.create_plot("Measured", "bar", api.state_manager)
    plot.replace_processed_data(api.state_manager.get_data())
    plot.config = {
        "x": "kind",
        "y": "metric",
        "shapes": [
            {
                "type": "line",
                "x0": 1.0,
                "y0": 2.0,
                "x1": 3.0,
                "y1": 4.0,
                "line": {"color": "#000000", "width": 2},
            },
            {
                "type": "line",
                "x0": 30.0,
                "y0": 40.0,
                "x1": 50.0,
                "y1": 60.0,
                "line": {"color": "#000000", "width": 2},
            },
        ],
    }
    before = deepcopy(plot.config["shapes"])
    navigate_to(app, "Manage Plots")
    app.toggle(key=plot_widget_key(app, plot.plot_id, "widgets.show_advanced")).set_value(
        True
    ).run()
    app.pills(key="settings_nav").set_value("advanced").run()
    app.toggle(key=plot_widget_key(app, plot.plot_id, "widgets.auto_refresh")).set_value(
        False
    ).run()
    if action == "delete":
        app.button(
            key=plot_widget_key(app, plot.plot_id, "widgets.appearance.shape_rows.del_shape_0")
        ).click().run()
        expected_count, expected_x0 = 1, 30.0
    elif action == "add":
        for field, value in zip(("x0", "y0", "x1", "y1"), ("70", "80", "90", "100")):
            app.text_input(
                key=plot_widget_key(app, plot.plot_id, f"widgets.appearance.s_{field}")
            ).set_value(value).run()
        app.button(
            key=plot_widget_key(app, plot.plot_id, "widgets.appearance.add_shape")
        ).click().run()
        expected_count, expected_x0 = 3, 1.0
    else:
        app.text_input(
            key=plot_widget_key(app, plot.plot_id, "widgets.appearance.shape_rows.edit_x0_0")
        ).set_value("12.5").run()
        expected_count, expected_x0 = 2, 12.5
    assert not app.exception
    assert plot.config["shapes"] == before
    app.pills(key="settings_nav").set_value("layout").run()
    app.pills(key="settings_nav").set_value("advanced").run()
    assert not app.exception
    assert plot.config["shapes"] == before
    app.button(key=plot_widget_key(app, plot.plot_id, "widgets.refresh")).click().run()
    app.run()
    assert not app.exception
    assert len(plot.config["shapes"]) == expected_count
    assert plot.config["shapes"][0]["x0"] == expected_x0
    native = plot.render_artifact.figure
    import plotly.graph_objects as go

    assert isinstance(native, go.Figure)
    assert isinstance(native.data[0], go.Bar)
    assert list(native.data[0].y) == [3.0]
    assert len(native.layout.shapes) == expected_count
    assert native.layout.shapes[0].x0 == expected_x0
    if action == "add":
        assert native.layout.shapes[-1].x0 == 70.0


def test_auto_refresh_reads_one_widget_and_manual_refresh_is_explicit() -> None:
    app = _app("""
        from src.web.components.common.chart_display import ChartDisplayComponent
        from src.web.state.ui_state_manager import UIStateManager
        ui = UIStateManager()
        for plot_id in [1, 2]:
            result = ChartDisplayComponent.render_refresh_controls(
                plot_id, ui.plot.get_auto_refresh(plot_id), True)
            st.session_state[f"result_{plot_id}"] = result
    """)
    assert not app.exception
    app.toggle(key=plot_widget_key(app, 1, "widgets.auto_refresh")).set_value(False).run()
    app.run()
    assert not app.exception
    assert app.session_state["result_1"]["auto_refresh"] is False
    assert app.session_state["result_1"]["should_generate"] is False
    assert app.session_state["result_2"]["auto_refresh"] is True
    app.button(key=plot_widget_key(app, 1, "widgets.refresh")).click().run()
    assert not app.exception
    assert app.session_state["result_1"]["manual_refresh"] is True
    assert app.session_state["result_1"]["should_generate"] is True


def test_type_change_resets_old_controls_and_preserves_measured_data() -> None:
    # [test->req~ring5.plots.change-type~1]
    frame = pd.DataFrame({"kind": ["a", "b"], "metric": [3.0, 5.0]})
    app = create_app_with_data(frame)
    api = get_api(app)
    old = PlotService.create_plot("Measured", "bar", api.state_manager)
    old.replace_processed_data(frame)
    navigate_to(app, "Manage Plots")
    app.toggle(key=plot_widget_key(app, old.plot_id, "widgets.auto_refresh")).set_value(False).run()
    app.text_input(key=plot_widget_key(app, old.plot_id, "widgets.title")).set_value(
        "Pending title"
    ).run()
    app.selectbox(key=plot_widget_key(app, old.plot_id, "widgets.plot_type_sel")).select(
        "line"
    ).run()
    assert not app.exception
    current = api.state_manager.get_plots()[0]
    assert current is not old
    assert current.plot_type == "line"
    assert current.plot_id == old.plot_id
    assert current.name == "Measured"
    pd.testing.assert_frame_equal(current.processed_data, frame)
    assert (
        app.text_input(key=plot_widget_key(app, old.plot_id, "widgets.title")).value
        != "Pending title"
    )
    assert app.toggle(key=plot_widget_key(app, old.plot_id, "widgets.auto_refresh")).value is True


@pytest.mark.parametrize("bundle", [False, True])
def test_browser_portfolio_restore_discards_widgets_for_reused_plot_ids(bundle: bool) -> None:
    # [test->req~ring5.ingestion.browser-upload~1]
    # [test->req~ring5.portfolio.portable-bundles~1]
    app = _app("""
        import pandas as pd
        from src.core.application_api import ApplicationAPI
        from src.core.services.data_services.portfolio_service import PortfolioService
        from src.core.services.portfolio_bundle_service import PortfolioBundleService
        from src.web.components.data_source.data_source_components import DataSourceComponents
        from src.web.controllers.plot.creation_controller import PlotCreationController
        from src.web.pages.plot_adapters import PlotLifecycleAdapter, PlotTypeRegistryAdapter
        from src.web.pages.ui.plotting.plot_factory import PlotFactory
        from src.web.state.ui_state_manager import UIStateManager
        if "api" not in st.session_state:
            api = ApplicationAPI(plot_deserializer=PlotFactory.from_dict)
            frame = pd.DataFrame({"x": ["a"], "y": [3.0]})
            api.state_manager.set_data(frame)
            plots = [PlotFactory.create_plot("bar", 1, name)
                     for name in ["Old plot name", "Imported plot name"]]
            for plot in plots:
                plot.replace_processed_data(frame)
                plot.replace_source_data(frame)
                plot.config = {"x": "x", "y": "y"}
            api.state_manager.add_plot(plots[0])
            payload = PortfolioService(api.state_manager).serialize_workspace(
                frame, [plots[1]], {}, 2)
            if USE_BUNDLE:
                payload = PortfolioBundleService.create("Imported", payload)
                name, mime = "imported.ring5-bundle", "application/zip"
            else:
                name, mime = "imported.json", "application/json"
            st.session_state["inspection"] = api.inspect_browser_upload(name, mime, payload)
            st.session_state["api"] = api
        api = st.session_state["api"]
        DataSourceComponents._show_validated_upload(api, st.session_state["inspection"])
        plot = api.state_manager.get_plots()[0]
        PlotCreationController(api, UIStateManager(), PlotLifecycleAdapter(),
                               PlotTypeRegistryAdapter()).render_controls(plot)
    """.replace("USE_BUNDLE", repr(bundle)))
    api = app.session_state["api"]
    try:
        assert not app.exception
        assert (
            app.text_input(key=plot_widget_key(app, 1, "widgets.rename")).value == "Old plot name"
        )
        button = next(button for button in app.button if "Restore" in button.label)
        button.click().run()
        assert not app.exception
        restored = api.state_manager.get_plots()[0]
        assert restored.name == "Imported plot name"
        assert (
            app.text_input(key=plot_widget_key(app, 1, "widgets.rename")).value
            == "Imported plot name"
        )
        pd.testing.assert_frame_equal(
            restored.processed_data, pd.DataFrame({"x": ["a"], "y": [3.0]})
        )
    finally:
        api.close()


@pytest.mark.parametrize("action", ["Clear Data", "Reset All"])
def test_actual_workspace_reset_clears_plot_widgets_and_preserves_global_owners(
    action: str,
) -> None:
    # [test->req~ring5.workspace.reset~1]
    app = create_app_with_data(pd.DataFrame({"kind": ["a"], "metric": [3.0]}))
    api = get_api(app)
    owner = app.query_params["_ring5_recovery"]
    old = PlotService.create_plot("Old plot name", "bar", api.state_manager)
    old.replace_processed_data(api.state_manager.get_data())
    navigate_to(app, "Manage Plots")
    assert (
        app.text_input(key=plot_widget_key(app, old.plot_id, "widgets.rename")).value
        == "Old plot name"
    )
    app.session_state[EngineManager.STATE_KEY] = "matplotlib"
    next(button for button in app.sidebar.button if button.label == action).click().run()
    assert not app.exception
    assert not api.state_manager.get_plots()
    assert app.session_state["api"] is api
    assert app.query_params["_ring5_recovery"] == owner
    assert app.session_state[EngineManager.STATE_KEY] == "matplotlib"
    assert f"plot.{old.plot_id}.widgets.rename" not in app.session_state
    assert f"plot.{old.plot_id}.widgets.auto_refresh" not in app.session_state
    api.state_manager.set_data(pd.DataFrame({"kind": ["b"], "metric": [5.0]}))
    fresh = PlotService.create_plot("New plot", "bar", api.state_manager)
    assert fresh.plot_id == old.plot_id
    navigate_to(app, "Manage Plots")
    assert (
        app.text_input(key=plot_widget_key(app, fresh.plot_id, "widgets.rename")).value
        == "New plot"
    )
    assert fresh.name == "New plot"
