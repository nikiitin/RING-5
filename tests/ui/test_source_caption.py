"""Render source identity from the facade instead of legacy configuration fields."""

from collections.abc import Generator
from pathlib import Path
from typing import cast

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.core.application_api import ApplicationAPI
from src.core.services.data_services.csv_pool_service import CsvPoolService
from src.core.services.data_services.path_service import PathService
from tests.ui.helpers import create_app, get_api


@pytest.fixture(autouse=True)
def isolated_application_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    """Keep the app's catalogs and automatic drafts inside this test's storage."""
    monkeypatch.setenv("RING5_DATA_DIR", str(tmp_path / "application-data"))
    PathService.reset_caches()
    CsvPoolService.clear_caches()
    try:
        yield
    finally:
        PathService.reset_caches()
        CsvPoolService.clear_caches()


def _source(app: AppTest) -> str:
    assert not app.exception
    return str(next(metric.value for metric in app.metric if metric.label == "Source"))


def test_unnamed_source_uses_loaded_basename_and_tracks_replacement(tmp_path: Path) -> None:
    app = create_app()
    api = cast(ApplicationAPI, get_api(app))
    first = tmp_path / "first results.csv"
    second = tmp_path / "second results.csv"
    first.write_text("ipc\n1.0\n", encoding="utf-8")
    second.write_text("ipc\n2.0\n", encoding="utf-8")
    config = {"csv_path": "/stale/config.csv", "title": "Preserved options"}
    api.state_manager.set_config(config.copy())

    api.load_data(str(first))
    app.run()
    assert _source(app) == first.name
    assert api.get_current_view()["csv_path"] == str(first)

    api.load_data(str(second))
    app.run()
    assert _source(app) == second.name
    assert api.state_manager.get_config() == config

    api.state_manager.clear_data()
    app.run()
    assert not app.exception
    assert not any(metric.label == "Source" for metric in app.metric)
    api.state_manager.set_data(pd.DataFrame({"ipc": [3.0]}))
    app.run()
    assert _source(app) == "Uploaded"


@pytest.mark.parametrize("csv_path", [None, ""])
def test_source_without_file_ignores_stale_config_path(csv_path: str | None) -> None:
    app = create_app()
    api = cast(ApplicationAPI, get_api(app))
    api.state_manager.set_data(pd.DataFrame({"ipc": [1.0]}))
    api.state_manager.update_config("csv_path", "/stale/config.csv")
    if csv_path is not None:
        api.state_manager.set_csv_path(csv_path)

    app.run()

    assert _source(app) == "Uploaded"
    view = api.get_current_view()
    assert view["csv_path"] == csv_path
    assert view["selected_dataset_name"] is None
    assert view["config"] == {"csv_path": "/stale/config.csv"}


def test_selected_dataset_name_wins_over_unrelated_file_association(tmp_path: Path) -> None:
    app = create_app()
    api = cast(ApplicationAPI, get_api(app))
    source = tmp_path / "A.csv"
    source.write_text("ipc\n1.0\n", encoding="utf-8")
    api.load_data(str(source))
    api.state_manager.update_config("csv_path", "/stale/config.csv")
    api.add_dataset("B", pd.DataFrame({"different": [2.0, 3.0]}), select=True)
    api.add_dataset("C", pd.DataFrame({"another": [4.0]}), select=False)

    app.run()
    assert _source(app) == "B"
    view = api.get_current_view()
    assert view["selected_dataset_name"] == "B"
    assert view["csv_path"] == str(source)
    assert view["config"] == {"csv_path": "/stale/config.csv"}

    api.select_dataset("C")
    app.run()
    assert _source(app) == "C"
