"""Injected recipe work stages editor fields until complete source and plot preflight."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

import ring5
from src.core.common.stat_config_codec import StatConfigCodec
from src.core.models.data_models import ScannedVariableDict
from src.core.state.state_manager import StateManager
from src.core.services.data_services.path_service import PathService
from tests.helpers.public_typed_parser import ExampleParser

pytestmark = pytest.mark.public_api


def _recipe(inputs: Path) -> ring5.AnalysisRecipe:
    variables = (
        ring5.StatConfig("value", "scalar", params={"source_type": "scalar"}),
        ring5.StatConfig(
            "label", "configuration", params={"source_type": "configuration", "on_empty": "NA"}
        ),
    )
    metadata: tuple[ScannedVariableDict, ...] = (
        {
            "name": "value",
            "type": "scalar",
            "source_type": "scalar",
            "entries": [],
            "instances": [{"source_name": "value", "indices": []}],
            "minimum": 1.25,
            "maximum": 1.25,
        },
    )
    return ring5.AnalysisRecipe(
        "injected",
        ring5.RecipeSource(
            "parser",
            str(inputs),
            pattern="*.txt",
            strategy="simple",
            variables=tuple(StatConfigCodec.to_payload(v) for v in variables),
            scanned_variables=metadata,
            simulator="declared-injected",
            scan_limit=None,
        ),
    )


def _editor(state: StateManager) -> tuple[object, ...]:
    return (
        state.get_stats_path(),
        state.get_stats_pattern(),
        state.get_parser_strategy(),
        state.get_simulator(),
        state.get_parse_variables(),
        state.get_scanned_variables(),
    )


@pytest.fixture
def workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[ring5.Session, ExampleParser, MagicMock, ring5.AnalysisRecipe], None, None]:
    PathService.reset_caches()
    monkeypatch.setenv("RING5_DATA_DIR", str(tmp_path / "ring5-data"))
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "a.txt").write_text("1.25", encoding="utf-8")
    old = tmp_path / "old.csv"
    old.write_text("label,original\nold,3.0\n", encoding="utf-8")
    backend = ExampleParser()
    submit = MagicMock(wraps=backend.submit_parse_async)
    monkeypatch.setattr(backend, "submit_parse_async", submit)
    try:
        with ring5.Session(parser=backend) as session:
            table = session.load(str(old))
            session.create_plot(
                "bar", data=table, config={"x": "label", "y": "original"}, name="old-plot"
            )
            state = session.api.state_manager
            state.set_stats_path("old-editor-inputs")
            state.set_stats_pattern("*.old")
            state.set_parser_strategy("old-editor-strategy")
            state.set_simulator("old-editor-backend")
            state.set_parse_variables(
                [
                    {
                        "name": "old",
                        "type": "scalar",
                        "params": {"source_type": "scalar"},
                    }
                ]
            )
            state.set_scanned_variables(
                [
                    {
                        "name": "old",
                        "type": "scalar",
                        "source_type": "scalar",
                        "entries": [],
                        "instances": [{"source_name": "old", "indices": []}],
                        "minimum": -1.0,
                        "maximum": 2.0,
                    }
                ]
            )
            yield session, backend, submit, _recipe(inputs)
    finally:
        backend.close()
        PathService.reset_caches()


@pytest.mark.parametrize("stage", ["pipeline", "plot"])
def test_injected_recipe_failed_preflight_preserves_frame_origin_editor_and_plots(
    workspace: tuple[ring5.Session, ExampleParser, MagicMock, ring5.AnalysisRecipe],
    stage: str,
) -> None:
    session, backend, submit, recipe = workspace
    state = session.api.state_manager
    data, origin, editor, plots = (
        state.get_data(),
        state.get_loaded_origin(),
        _editor(state),
        state.get_plots(),
    )
    error: type[ring5.Ring5Error]
    if stage == "pipeline":
        invalid = replace(
            recipe, transformations=({"type": "columnSelector", "columns": ["missing"]},)
        )
        error = ring5.PipelineError
    else:
        invalid = replace(
            recipe, plots=(ring5.RecipePlot("bad", "bar", {"x": "label", "y": "missing"}),)
        )
        error = ring5.ColumnNotFoundError
    with pytest.raises(error):
        session.run_analysis_recipe(invalid)
    current = state.get_data()
    assert data is not None and current is not None
    pd.testing.assert_frame_equal(current, data)
    assert state.get_loaded_origin() is origin
    assert _editor(state) == editor
    assert state.get_plots() == plots
    assert session.api._parser is backend
    assert submit.call_count == 1
    assert backend.scans == 0
    assert backend._executor.submit(lambda: 17).result(timeout=5) == 17


def test_successful_injected_recipe_publishes_nonempty_actual_editor_and_preserves_backend_lifetime(
    workspace: tuple[ring5.Session, ExampleParser, MagicMock, ring5.AnalysisRecipe],
) -> None:
    session, backend, submit, recipe = workspace
    session.run_analysis_recipe(recipe)
    state = session.api.state_manager
    current = state.get_data()
    assert current is not None
    assert current.to_dict("list") == {"value": [1.25], "label": ["NA"]}
    assert state.get_stats_path() == recipe.source.path
    assert state.get_stats_pattern() == "*.txt"
    assert state.get_parser_strategy() == "simple"
    assert state.get_simulator() == "declared-injected"
    assert [
        StatConfigCodec.to_payload(StatConfigCodec.from_draft(v))
        for v in state.get_parse_variables()
    ] == list(recipe.source.variables)
    assert state.get_scanned_variables() == list(recipe.source.scanned_variables)
    assert session.capture_analysis_recipe("recaptured").source == recipe.source
    state.set_stats_path("later-editor-only")
    state.set_scanned_variables([])
    assert session.capture_analysis_recipe("still-origin").source == recipe.source
    assert session.api._parser is backend
    assert submit.call_count == 1
    assert backend.scans == 0
    assert backend._executor.submit(lambda: 17).result(timeout=5) == 17
