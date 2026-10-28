"""Schema publications refresh every active-dataset view in the same interaction."""

from typing import cast

import pandas as pd

from src.core.application_api import ApplicationAPI
from src.core.models.semantic_metadata_models import ColumnSemantics, DatasetSemantics
from tests.ui.helpers import create_app_with_data, get_api, navigate_to


def test_unit_conversion_refreshes_sibling_tables_and_retains_one_success_notice() -> None:
    data = pd.DataFrame(
        {
            "benchmark": ["alpha", "beta"],
            "time": [1000.0, 2500.0],
            "time.sd": [100.0, 250.0],
        }
    )
    app = create_app_with_data(data)
    api = cast(ApplicationAPI, get_api(app))
    annotated = api.managers.attach_semantics(
        data, DatasetSemantics((ColumnSemantics("time", "Latency", "ms"),))
    )
    api.state_manager.set_data(annotated)
    navigate_to(app, "Data Managers")

    app.button(key="manager.schema_contract.apply_semantics").click().run()
    assert not app.exception
    assert any(
        message.value == "Semantic labels and units are retained with the active dataset."
        for message in app.success
    )
    app.selectbox(key="manager.schema_contract.convert_target").set_value("s").run()
    app.button(key="manager.schema_contract.convert").click().run()

    assert not app.exception
    expected = pd.DataFrame(
        {"benchmark": ["alpha", "beta"], "time": [1.0, 2.5], "time.sd": [0.1, 0.25]}
    )
    current = api.state_manager.get_data()
    assert current is not None
    pd.testing.assert_frame_equal(current, expected)
    for label in ("Summary", "Data Visualization"):
        tab = next(item for item in app.tabs if item.label == label)
        pd.testing.assert_frame_equal(tab.dataframe[0].value, expected)
    assert any(
        message.value == "Converted time to s; the prior revision remains undoable."
        for message in app.success
    )
    assert api.managers.inspect_semantics(current).for_column("time") == ColumnSemantics(
        "time", "Latency", "s"
    )
    assert "manager.schema_contract.success_notice" not in app.session_state

    app.run()
    assert not app.exception
    assert not any("Converted time to s" in message.value for message in app.success)
