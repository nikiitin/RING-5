"""Public operation boundaries for core-review regressions."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Callable
from copy import deepcopy
from typing import Literal, Required, TypedDict, cast
from types import SimpleNamespace

import pandas as pd
import pytest

import ring5
from ring5 import _portfolio
from ring5.shapers import Shaper, ShaperDefinition, register_shaper
from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.pipeline_service import PipelineStepError

pytestmark = pytest.mark.public_api


class _OwnedMutationConfig(TypedDict):
    type: Required[Literal["ownedMutation"]]


def _register_mutation(
    monkeypatch: pytest.MonkeyPatch, operation: Callable[[pd.DataFrame], object]
) -> None:
    class Mutation(Shaper):
        def __call__(self, frame: pd.DataFrame) -> pd.DataFrame:
            return cast(pd.DataFrame, operation(frame))

    monkeypatch.setattr(ShaperFactory, "_definitions", dict(ShaperFactory._definitions))
    register_shaper(
        ShaperDefinition(
            "ownedMutation", Mutation, "Owned mutation", _OwnedMutationConfig, lambda config: None
        )
    )


def test_malformed_pipeline_and_theme_raise_typed_public_errors() -> None:
    with ring5.Session() as session:
        with pytest.raises(ring5.PipelineError) as failure:
            session.shape(ring5.Table.from_rows([{"x": 1}]), cast(list[dict[str, object]], [None]))
        assert failure.value.step_index == 0
        with pytest.raises(ring5.DataValidationError):
            session.apply_accessible_theme({"marker_size": "bad"}, "line")


def test_close_releases_session_parse_orchestrator_workspace() -> None:
    session = ring5.Session()
    service = session.api._get_parse_job_service()
    workspace = service.session_dir
    assert workspace.exists()
    session.close()
    assert not workspace.exists()
    session.close()


def test_portfolio_export_allocates_every_collision_without_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class ReplaySession:
        plots = [
            SimpleNamespace(name=name, plot_id=identifier, config={})
            for identifier, name in enumerate(["a_2", "a", "a", "A"])
        ]

        def __enter__(self) -> "ReplaySession":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def load_portfolio(self, name: str) -> SimpleNamespace:
            return SimpleNamespace(plots_skipped=[])

        def render(self, plot: SimpleNamespace, *, engine: str) -> str:
            return str(plot.plot_id)

        def export(self, figure: str, path: str, **kwargs: object) -> str:
            Path(path).write_text(figure)
            return path

    monkeypatch.setattr(_portfolio, "Session", ReplaySession)
    written = _portfolio.render_portfolio("test", str(tmp_path))
    assert len({Path(path).name.casefold() for path in written}) == 4
    assert [Path(path).read_text() for path in written] == ["0", "1", "2", "3"]


def test_table_owns_nested_cells_across_constructor_access_and_transformation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = pd.DataFrame({"object": [{"values": [1]}]})
    table = ring5.Table(original)
    cast(dict[str, list[int]], original.iloc[0, 0])["values"].append(2)
    exposed = table.frame
    cast(dict[str, list[int]], exposed.iloc[0, 0])["values"].append(3)
    rows = table.rows()
    rows[0]["object"]["values"].append(4)
    assert table.rows() == [{"object": {"values": [1]}}]
    captured: list[pd.DataFrame] = []

    def mutate(frame: pd.DataFrame) -> pd.DataFrame:
        cast(dict[str, list[int]], frame.iloc[0, 0])["values"].append(5)
        captured.append(frame)
        return frame

    _register_mutation(monkeypatch, mutate)
    with ring5.Session() as session:
        transformed = session.shape(table, [{"type": "ownedMutation"}])
    cast(dict[str, list[int]], captured[0].iloc[0, 0])["values"].append(6)
    assert table.rows() == [{"object": {"values": [1]}}]
    assert transformed.rows() == [{"object": {"values": [1, 5]}}]

    def fail(frame: pd.DataFrame) -> pd.DataFrame:
        cast(dict[str, list[int]], frame.iloc[0, 0])["values"].append(7)
        raise ValueError("reject")

    monkeypatch.setattr(
        ShaperFactory,
        "_definitions",
        {key: value for key, value in ShaperFactory._definitions.items() if key != "ownedMutation"},
    )
    _register_mutation(monkeypatch, fail)
    with ring5.Session() as session:
        with pytest.raises(ring5.PipelineError, match="reject"):
            session.shape(table, [{"type": "ownedMutation"}])
    assert table.rows() == [{"object": {"values": [1]}}]


@pytest.mark.parametrize("returned", [None, 1, pd.Series([1])])
def test_pipeline_rejects_invalid_plugin_results_without_changing_owned_input(
    returned: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    table = ring5.Table.from_rows([{"x": 1, "nested": {"values": [1]}}])

    def invalid_transform(frame: pd.DataFrame) -> object:
        frame["x"] = 99
        cast(dict[str, list[int]], frame.at[0, "nested"])["values"].append(2)
        return returned

    _register_mutation(monkeypatch, invalid_transform)
    with ring5.Session() as session:
        with pytest.raises(
            ring5.PipelineError, match="Shaper output must be a pandas DataFrame"
        ) as failure:
            session.shape(table, [{"type": "ownedMutation"}])
        assert failure.value.step_index == 0
        assert failure.value.shaper_type == "ownedMutation"
        cause = failure.value.__cause__
        assert isinstance(cause, PipelineStepError)
        assert cause.step_index == 0 and cause.shaper_type == "ownedMutation"
        assert type(cause.__cause__) is TypeError
        assert str(cause.__cause__) == (
            f"Shaper output must be a pandas DataFrame; got {type(returned).__name__}."
        )
    assert table.rows() == [{"x": 1, "nested": {"values": [1]}}]
    with pytest.raises(TypeError, match="Table requires a pandas DataFrame"):
        ring5.Table(cast(pd.DataFrame, returned))


@pytest.mark.parametrize(
    ("declarations", "cause_type"), [(None, TypeError), ({"logical": {}}, ValueError)]
)
def test_table_rejects_malformed_reserved_declarations_without_changing_source(
    declarations: object, cause_type: type[Exception]
) -> None:
    frame = pd.DataFrame({"x": [1.5], "nested": [{"values": [1]}]})
    frame.attrs["ring5.distribution_layouts"] = declarations
    frame.attrs["unrelated"] = {"values": [2]}
    before = deepcopy(frame)
    original_attrs = deepcopy(frame.attrs)
    with pytest.raises(
        ring5.DataValidationError, match="Invalid table data or metadata"
    ) as failure:
        ring5.Table(frame)
    assert type(failure.value.__cause__) is cause_type
    pd.testing.assert_frame_equal(frame, before)
    assert frame.attrs == original_attrs
    assert frame.attrs["ring5.distribution_layouts"] is declarations
