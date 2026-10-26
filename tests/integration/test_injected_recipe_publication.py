"""Injected recipe work stages editor fields until complete source and plot preflight."""

from __future__ import annotations

from collections.abc import Generator
from concurrent.futures import Future
from threading import Event
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
    csv_path = state.get_csv_path()
    assert csv_path is not None
    published = Path(csv_path)
    assert published.is_file()
    assert str(published.parent) in session._owned_tmpdirs
    session.close()
    assert not published.parent.exists()
    assert (Path(recipe.source.path) / "a.txt").is_file()
    assert backend._executor.submit(lambda: 17).result(timeout=5) == 17


class _GatedParser(ExampleParser):
    """Keep real executor work running after the foreground timeout is reported."""

    def __init__(self) -> None:
        super().__init__()
        self.started = Event()
        self.release = Event()
        self.batch: ring5.ParseBatchResult | None = None

    def _work(
        self, path: str, variables: list[ring5.StatConfig], output_dir: str
    ) -> ring5.ParsedFileResult:
        self.started.set()
        if not self.release.wait(5):
            raise TimeoutError("Test did not release the parser worker")
        (Path(output_dir) / "worker-marker").write_text("completed", encoding="utf-8")
        return ExampleParser._parse(path, variables)

    def submit_parse_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: list[ring5.StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ring5.ScannedVariable] | None = None,
        *,
        file_paths: list[str] | None = None,
    ) -> ring5.ParseBatchResult:
        paths = tuple(
            file_paths
            if file_paths is not None
            else (str(path) for path in sorted(Path(stats_path).glob(stats_pattern)))
        )
        futures: tuple[Future[ring5.ParsedFileResult], ...] = tuple(
            self._executor.submit(self._work, path, variables, output_dir) for path in paths
        )
        self.batch = ring5.ParseBatchResult(
            futures, tuple(v.name for v in variables), paths, output_dir, strategy_type
        )
        assert self.started.wait(5)
        return self.batch


@pytest.mark.parametrize("injected", [False, True])
def test_recipe_timeout_retains_running_workspace_until_task_settles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    injected: bool,
) -> None:
    from src.parsing.registry import ParsingStrategy, SimulatorInfo, SimulatorRegistry

    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "a.txt").write_text("1.25", encoding="utf-8")
    old = tmp_path / "old.csv"
    old.write_text("label,original\nold,7.5\n", encoding="utf-8")
    backend = _GatedParser()
    name = "gated-recipe"
    if not injected:
        info = SimulatorInfo(
            name, "Gated recipe", parsing_strategies=[ParsingStrategy("simple", "Simple")]
        )
        monkeypatch.setitem(SimulatorRegistry._registry, name, (info, lambda: backend))
        monkeypatch.setitem(SimulatorRegistry._instances, name, backend)
    session = ring5.Session(parser=backend) if injected else ring5.Session()
    try:
        session.load(str(old))
        state = session.api.state_manager
        state.set_stats_path("previous-editor")
        before_data, before_origin, before_editor = (
            state.get_data(),
            state.get_loaded_origin(),
            _editor(state),
        )
        recipe = _recipe(inputs)
        if not injected:
            recipe = replace(recipe, source=replace(recipe.source, simulator=name))
        monkeypatch.setattr("ring5._parse.PARSE_BATCH_TIMEOUT_SECONDS", 0)
        with pytest.raises(ring5.ParseError, match="remained unfinished"):
            session.run_analysis_recipe(recipe)
        assert backend.batch is not None
        future = backend.batch.futures[0]
        directory = Path(backend.batch.output_dir)
        assert future.running()
        assert directory.is_dir()
        assert str(directory) not in session._owned_tmpdirs
        current = state.get_data()
        assert current is not None and before_data is not None
        pd.testing.assert_frame_equal(current, before_data)
        assert state.get_loaded_origin() is before_origin
        assert _editor(state) == before_editor
        session.close()
        assert directory.is_dir()
        callbacks_done = Event()
        future.add_done_callback(lambda _future: callbacks_done.set())
        backend.release.set()
        result = future.result(timeout=5)
        assert result.variables[0].cells[0].value == 1.25
        assert callbacks_done.wait(5)
        assert not directory.exists()
        assert backend._executor.submit(lambda: 17).result(timeout=5) == 17
    finally:
        backend.release.set()
        session.close()
        backend.close()


@pytest.mark.parametrize("mode", ["recipe", "incremental", "playground"])
def test_internally_owned_scratch_uses_one_identity_under_symlinked_tmpdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    import tempfile

    actual = tmp_path / "actual-temp"
    actual.mkdir()
    alias = tmp_path / "temp-alias"
    alias.symlink_to(actual, target_is_directory=True)
    monkeypatch.setenv("TMPDIR", str(alias))
    monkeypatch.setattr(tempfile, "tempdir", None)
    assert tempfile.gettempdir() == str(alias)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "stats.txt").write_text("simTicks 1.25\n", encoding="utf-8")
    variable = ring5.StatConfig(
        "value", "scalar", source_name="simTicks", params={"source_type": "scalar"}
    )
    session = ring5.Session()
    try:
        if mode == "recipe":
            recipe = ring5.AnalysisRecipe(
                "symlink",
                ring5.RecipeSource(
                    "parser",
                    str(inputs),
                    variables=(StatConfigCodec.to_payload(variable),),
                    simulator="gem5",
                    scan_limit=None,
                ),
            )
            session.run_analysis_recipe(recipe)
            csv_path = session.api.state_manager.get_csv_path()
            assert csv_path is not None and Path(csv_path).is_file()
            directory = Path(csv_path).parent
        elif mode == "incremental":
            parsed = session.parse(str(inputs), [variable], incremental=True)
            assert session.load(parsed).rows() == [{"value": 1.25}]
            directory = Path(parsed.csv_path).parent
        else:
            job = session.parser_playground_submit(str(inputs), [variable])
            assert job.finalize().rows == ((1.25,),)
            directory = Path(job.output_dir)
        assert directory.parent == actual
        assert str(directory) in session._owned_tmpdirs
        assert all(path == str(Path(path).resolve()) for path in session._owned_tmpdirs)
        assert directory.is_dir()
    finally:
        session.close()
    assert not directory.exists()
    assert (inputs / "stats.txt").is_file()
