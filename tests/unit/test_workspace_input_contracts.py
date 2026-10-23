"""Source-bound preview confirmation and complete stable artifact identities."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace

import pandas as pd
import pytest

from src.core.application_api import ApplicationAPI
from src.core.common.content_identity import frame_signature
from src.core.models.visualization.figure_config import FigureConfig
from src.core.services.data_services.dataset_snapshot_service import DatasetSnapshotService
from src.core.services.data_services.path_service import PathService
from src.core.services.data_services.portfolio_service import PortfolioService


@pytest.fixture
def api():
    instance = ApplicationAPI()
    instance.state_manager.set_data(pd.DataFrame({"x": [1.0], "group": ["A"]}))
    try:
        yield instance
    finally:
        instance.close()


def _store(api, config=None):
    options = config or {"column": "x", "factor": 2}
    token = api.preview_input_signature()
    data = api.state_manager.get_data()
    data["x"] *= 2
    api.set_preview("scale", data, operation_config=options, source_signature=token)
    return options


def test_preview_reads_preserve_identity_and_confirmation_consumes_it(api) -> None:
    before = api.preview_input_signature()
    defensive = api.state_manager.get_data()
    defensive["x"] = 900
    assert api.preview_input_signature() == before
    options = _store(api)
    assert api.preview_matches("scale", operation_config=options)
    defensive_preview = api.get_preview("scale")
    defensive_preview["x"] = 999
    confirmed = api.confirm_preview("scale", operation_config=options, operation="Scale x")
    assert confirmed["x"].tolist() == [2.0]
    assert api.state_manager.get_data()["x"].tolist() == [2.0]
    assert not api.has_preview("scale")
    assert not api.preview_matches("scale", operation_config=options)


def test_preview_options_are_owned_and_edited_options_cannot_confirm(api) -> None:
    options = {"columns": ["x"], "factor": 2}
    _store(api, options)
    api.get_preview_config("scale")["columns"].append("other")
    assert api.get_preview_config("scale") == options
    options["columns"].append("changed")
    assert not api.preview_matches("scale", operation_config=options)
    with pytest.raises(ValueError, match="options changed"):
        api.confirm_preview("scale", operation_config=options, operation="Scale")
    assert api.state_manager.get_data()["x"].tolist() == [1.0]


def test_identical_named_data_sources_have_distinct_identity(api) -> None:
    state = api.state_manager
    state.add_dataset("A", state.get_data())
    state.add_dataset("B", state.get_data(), select=False)
    options = _store(api)
    state.select_dataset("B")
    assert not api.preview_matches("scale", operation_config=options)
    with pytest.raises(ValueError, match="source or options changed"):
        api.confirm_preview("scale", operation_config=options, operation="Scale")
    assert state.selected_dataset_name() == "B"
    assert state.get_data()["x"].tolist() == [1.0]


def test_inflight_computation_does_not_lock_state_and_cannot_publish_stale_result(api) -> None:
    ready, resume = threading.Event(), threading.Event()

    def compute():
        token = api.preview_input_signature()
        result = api.state_manager.get_data()
        ready.set()
        assert resume.wait(2)
        result["x"] *= 2
        api.set_preview("scale", result, operation_config={"factor": 2}, source_signature=token)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(compute)
        assert ready.wait(2)
        api.state_manager.set_data(pd.DataFrame({"x": [20.0]}))
        resume.set()
        with pytest.raises(ValueError, match="source changed during computation"):
            future.result(timeout=2)
    assert api.state_manager.get_data()["x"].tolist() == [20.0]
    assert not api.has_preview("scale")


def test_confirm_compare_and_publication_are_one_transaction(api, monkeypatch) -> None:
    options = _store(api)
    checking, update_attempted, update_done = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    original_get = api.state_manager.get_preview

    def paused_get(name):
        checking.set()
        assert update_attempted.wait(2)
        assert not update_done.is_set()
        return original_get(name)

    monkeypatch.setattr(api.state_manager, "get_preview", paused_get)

    def update():
        assert checking.wait(2)
        update_attempted.set()
        api.state_manager.set_data(pd.DataFrame({"x": [50.0]}))
        update_done.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(update)
        result = api.confirm_preview("scale", operation_config=options, operation="Scale")
        future.result(timeout=2)
    assert result["x"].tolist() == [2.0]
    assert api.state_manager.get_data()["x"].tolist() == [50.0]


def test_legacy_preview_has_no_confirmation_authorization(api) -> None:
    api.set_preview("scale", pd.DataFrame({"x": [2]}))
    assert api.get_preview_config("scale") is None
    with pytest.raises(ValueError, match="preview it again"):
        api.confirm_preview("scale", operation_config={}, operation="Scale")


def _plot():
    frame = pd.DataFrame({"category": ["A"], "value": [1.0]})
    return SimpleNamespace(
        plot_id=1,
        name="Figure",
        plot_type="bar",
        config={"x": "category", "y": "value"},
        pipeline=[],
        pipeline_counter=0,
        legend_mappings={},
        legend_mappings_by_column={},
        source_data=frame.copy(),
        processed_data=frame.copy(),
    )


@pytest.mark.parametrize(
    "changed",
    [
        "data",
        "processed",
        "plot_config",
        "pipeline",
        "plot_source",
        "plot_processed",
        "figure_style",
        "global",
        "provenance",
        "semantics",
    ],
)
def test_report_signature_covers_every_render_and_provenance_input(api, changed) -> None:
    state = api.state_manager
    plot = _plot()
    state.add_plot(plot)
    state.set_visualization_config(1, FigureConfig())
    before = api.report_input_signature([1])
    assert api.report_input_signature([1]) == before
    defensive = state.get_data()
    defensive["x"] = 999
    assert api.report_input_signature([1]) == before
    if changed == "data":
        state.set_data(pd.DataFrame({"x": [3.0]}))
    elif changed == "processed":
        state.set_processed_data(pd.DataFrame({"x": [5.0]}))
    elif changed == "plot_config":
        plot.config["title"] = "Changed"
    elif changed == "pipeline":
        plot.pipeline.append({"type": "sort", "order_dict": {"category": ["A"]}})
    elif changed == "plot_source":
        plot.source_data["value"] = 5
    elif changed == "plot_processed":
        plot.processed_data["value"] = 7
    elif changed == "figure_style":
        state.set_visualization_config(
            1, replace(state.get_visualization_config(1), barmode="stack")
        )
    elif changed == "global":
        state.update_config("font_family", "Different")
    elif changed == "semantics":
        plot.source_data.attrs = {"units": {"value": "cycles"}}
    else:
        state.set_csv_path("different.csv")
    assert api.report_input_signature([1]) != before
    assert api.report_input_signature([1], include_data=False) != api.report_input_signature([1])


def test_stable_frame_identity_retains_typed_objects_datetime_axes_and_semantics() -> None:
    frame = pd.DataFrame({"x": pd.Series([1], dtype=object)})
    before = frame_signature(frame)
    assert frame_signature(frame.copy()) == before
    frame["x"] = pd.Series(["1"], dtype=object)
    assert frame_signature(frame) != before
    frame.index = pd.DatetimeIndex(["2026-10-23T12:00:00Z"], name="when")
    assert frame_signature(frame) == frame_signature(frame.copy())


def test_bundle_signature_tracks_saved_portfolio_and_snapshot_content(
    api, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("RING5_DATA_DIR", str(tmp_path))
    PathService.reset_caches()
    service = PortfolioService(api.state_manager)
    service.save_portfolio("paper", pd.DataFrame({"x": [1]}), [], {}, 0)
    DatasetSnapshotService.save_snapshot("source", pd.DataFrame({"x": [1]}), source_dataset="run")
    before = api.portfolio_bundle_signature("paper", "source")
    assert api.portfolio_bundle_signature("paper", "source") == before
    service.save_portfolio("paper", pd.DataFrame({"x": [2]}), [], {}, 0)
    assert api.portfolio_bundle_signature("paper", "source") != before
    saved = api.portfolio_bundle_signature("paper", "source")
    DatasetSnapshotService.save_snapshot(
        "source", pd.DataFrame({"x": [3]}), source_dataset="run", overwrite=True
    )
    assert api.portfolio_bundle_signature("paper", "source") != saved
    PathService.reset_caches()


def test_unrelated_named_data_and_redundant_source_controls_keep_preview_valid(api) -> None:
    state = api.state_manager
    state.add_dataset("active", state.get_data())
    options = _store(api)
    before = api.preview_input_signature()
    state.add_dataset("unselected", pd.DataFrame({"x": [70]}), select=False)
    state.select_dataset("active")
    state.set_csv_path(state.get_csv_path())
    state.set_use_parser(state.is_using_parser())
    assert api.preview_input_signature() == before
    assert api.preview_matches("scale", operation_config=options)


def test_failed_change_callback_cannot_leave_old_preview_authorized(api) -> None:
    options = _store(api)

    def rejected_callback():
        raise RuntimeError("callback failed")

    with pytest.raises(RuntimeError, match="callback failed"):
        api.state_manager.set_data(pd.DataFrame({"x": [100]}), on_change=rejected_callback)
    assert not api.preview_matches("scale", operation_config=options)
    with pytest.raises(ValueError, match="preview it again"):
        api.confirm_preview("scale", operation_config=options, operation="Scale")
    assert api.state_manager.get_data()["x"].tolist() == [100]


def test_change_callback_can_wait_for_other_state_publication(api) -> None:
    with ThreadPoolExecutor(max_workers=1) as pool:

        def callback():
            pool.submit(api.state_manager.set_processed_data, pd.DataFrame({"x": [7]})).result(
                timeout=2
            )

        api.state_manager.set_data(pd.DataFrame({"x": [5]}), on_change=callback)
    assert api.state_manager.get_processed_data()["x"].tolist() == [7]


def test_global_config_writes_obey_the_same_state_transaction(api) -> None:
    attempted, completed = threading.Event(), threading.Event()

    def update():
        attempted.set()
        api.state_manager.update_config("font", "changed")
        completed.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with api.state_manager.transaction():
            future = pool.submit(update)
            assert attempted.wait(2)
            assert not completed.is_set()
            assert "font" not in api.state_manager.get_config()
        future.result(timeout=2)
    assert completed.is_set()
    assert api.state_manager.get_config()["font"] == "changed"


def test_preview_and_confirmed_source_own_nested_object_cells(api) -> None:
    options = {"kind": "nested"}
    source = api.preview_input_signature()
    result = pd.DataFrame({"object": [{"value": [2]}]})
    api.set_preview("nested", result, operation_config=options, source_signature=source)
    result.iloc[0, 0]["value"].append(3)
    exposed = api.get_preview("nested")
    exposed.iloc[0, 0]["value"].append(999)
    confirmed = api.confirm_preview("nested", operation_config=options, operation="Nested result")
    assert confirmed.iloc[0, 0] == {"value": [2]}
    confirmed.iloc[0, 0]["value"].append(1000)
    assert api.state_manager.get_data().iloc[0, 0] == {"value": [2]}


def test_initialize_invalidates_preview_when_clearing_an_empty_source(api) -> None:
    api.state_manager.set_data(pd.DataFrame({"x": pd.Series(dtype=float)}))
    options = _store(api)
    assert api.preview_matches("scale", operation_config=options)
    api.state_manager.initialize()
    assert api.state_manager.get_data() is None
    assert not api.preview_matches("scale", operation_config=options)


def test_transaction_rejects_foreign_callback_before_source_publication(api) -> None:
    options = _store(api)
    called = []
    with api.state_manager.transaction():
        with pytest.raises(ValueError, match="surrounding transaction exits"):
            api.state_manager.set_data(
                pd.DataFrame({"x": [900]}), on_change=lambda: called.append(True)
            )
        assert api.state_manager.get_data()["x"].tolist() == [1.0]
        assert api.preview_matches("scale", operation_config=options)
    assert called == []


@pytest.mark.parametrize("values", [["text"], [1], [True], [None], [{"value": [1]}]])
def test_owned_frame_copy_preserves_explicit_object_dtype(values) -> None:
    from src.core.common.dataframe_copy import copy_dataframe

    frame = pd.DataFrame({"value": pd.Series(values, dtype=object)})
    copied = copy_dataframe(frame)
    pd.testing.assert_frame_equal(copied, frame)
    assert copied["value"].dtype == object
