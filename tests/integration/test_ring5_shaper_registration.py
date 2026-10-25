"""Public plugin registration uses the same exact contract as built-in pipelines."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, Required, TypedDict

import pandas as pd
import pytest

import ring5
from ring5.errors import PipelineError
from ring5.shapers import Shaper, ShaperDefinition, available_shaper_types, register_shaper
from src.core.services.shapers.factory import ShaperFactory

pytestmark = pytest.mark.public_api


class PluginConfig(TypedDict, total=False):
    type: Required[Literal["publicOffset"]]
    column: Required[str]
    amount: Required[float]


class Offset(Shaper):
    def __call__(self, frame: pd.DataFrame) -> pd.DataFrame:
        return frame.assign(
            **{self.params["column"]: frame[self.params["column"]] + self.params["amount"]}
        )


def _validate_offset(config: Mapping[str, Any]) -> None:
    if not config["column"]:
        raise ValueError("Offset requires a non-empty column.")


def test_public_definition_registration_and_typed_rejection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    # [test->req~ring5.extension.shaper-registry~1]
    # [test->req~ring5.api.registry-discovery~1]
    monkeypatch.setattr(ShaperFactory, "_definitions", dict(ShaperFactory._definitions))
    definition = ShaperDefinition(
        "publicOffset", Offset, "Public offset", PluginConfig, _validate_offset
    )
    register_shaper(definition)
    assert available_shaper_types()[-1] == "publicOffset"
    pipeline: Sequence[Mapping[str, object]] = (
        PluginConfig(type="publicOffset", column="v", amount=2.5),
    )
    source = pd.DataFrame({"v": [1.0, 2.0]})
    from src.core.services.data_services.config_service import ConfigService

    monkeypatch.setattr(ConfigService, "_config_dir", tmp_path)
    with ring5.Session() as session:
        payload = session.export_pipeline_configuration("Custom pipeline", pipeline)
        restored = session.import_pipeline_configuration(payload)
        assert restored.shapers == tuple(pipeline)
        result = session.shape(ring5.Table(source), restored.shapers)
        assert result.frame["v"].tolist() == [3.5, 4.5]
        assert source["v"].tolist() == [1.0, 2.0]
        with pytest.raises(PipelineError, match="unsupported fields") as failure:
            session.shape(
                ring5.Table(source),
                [{"type": "publicOffset", "column": "v", "amount": 1.0, "stale": 1}],
            )
        assert failure.value.step_index == 0
        with pytest.raises(PipelineError, match="non-empty column"):
            session.shape(
                ring5.Table(source), [{"type": "publicOffset", "column": "", "amount": 1.0}]
            )
    with pytest.raises(PipelineError, match="already registered"):
        register_shaper(definition)
    with pytest.raises(PipelineError, match="ShaperDefinition"):
        register_shaper("publicOffset")  # type: ignore[arg-type]


def test_plugin_background_capture_and_submission_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from collections.abc import Callable
    from unittest.mock import MagicMock

    monkeypatch.setattr(ShaperFactory, "_definitions", dict(ShaperFactory._definitions))
    register_shaper(
        ShaperDefinition("publicOffset", Offset, "Public offset", PluginConfig, _validate_offset)
    )
    callbacks: list[Callable[[], Any]] = []

    def submit(kind: str, label: str, callback: Callable[[], Any]) -> Any:
        callbacks.append(callback)
        return MagicMock()

    with ring5.Session() as session:
        monkeypatch.setattr(session.api, "submit_background_operation", submit)
        frame = pd.DataFrame({"v": [1.0]})
        config = PluginConfig(type="publicOffset", column="v", amount=2.0)
        session.shape_submit(ring5.Table(frame), (config,))
        frame.loc[0, "v"] = 50.0
        config["amount"] = 99.0
        assert callbacks.pop()().frame["v"].tolist() == [3.0]

        def must_not_copy(frame: Any) -> Any:
            raise AssertionError("Invalid configuration reached data ownership copy")

        table = ring5.Table(frame)
        monkeypatch.setattr(ring5.Table, "frame", property(must_not_copy))
        with pytest.raises(ring5.JobError, match="unsupported fields"):
            session.shape_submit(
                table, [{"type": "publicOffset", "column": "v", "amount": 1.0, "stale": True}]
            )
        assert not callbacks
