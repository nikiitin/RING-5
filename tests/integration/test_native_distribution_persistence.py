"""Actual native parsing survives public typed persistence and one canonical recipe replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, cast
from unittest.mock import Mock

import pytest

import ring5
from src.core.models.visualization.trace_config import BarTraceConfig
from src.core.services.data_services.path_service import PathService
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.rendering.figure_preparation import PreparedFigure

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("perl_pool")]
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/gem5_native_text/nonunit.txt"


def assert_native_render(
    session: ring5.Session, plot: BasePlot, engine: Literal["plotly", "matplotlib"], payload: object
) -> None:
    assert plot.processed_data is not None
    assert plot.processed_data.attrs["ring5.distribution_layouts"]["cells"] == payload
    session.render(plot, engine=engine)
    preparation = plot.render_artifact.preparation
    assert isinstance(preparation, PreparedFigure)
    assert preparation.spec.axes.x.label == "Native bucket"
    assert preparation.trace_result.custom_x_ticks == {
        "vals": [0, 1, 2, 3, 4],
        "text": ["underflows", "0.25-1.75", "2.75-4.25", "5.25-5.75", "overflows"],
    }
    trace = cast(BarTraceConfig, preparation.trace_result.traces[0])
    assert trace.y == [0, 1, 1, 1, 0]
    assert trace.bar_width == [1.0] * 5


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_real_parser_table_portfolio_snapshot_recovery_and_recipe_preserve_native_cells(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, engine: Literal["plotly", "matplotlib"]
) -> None:
    # [test->req~ring5.plot.histogram~2]
    monkeypatch.setenv("RING5_DATA_DIR", str(tmp_path / "private-store"))
    PathService.reset_caches()
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "stats.txt").write_text(FIXTURE.read_text())
    config = ring5.StatConfig(
        "cells",
        "distribution",
        source_name="system.cpu00.dist",
        params={
            "source_type": "distribution",
            "minimum": 0.25,
            "maximum": 5.75,
            "bucket_size": 2.5,
            "zero_policy": "missing",
            "statistics": ["mean"],
        },
    )
    try:
        with ring5.Session() as original:
            result = original.parse(str(inputs), [config], scan_limit=0)
            table = original.load(result)
            payload = table.frame.attrs["ring5.distribution_layouts"]["cells"]
            assert payload["geometry"] == {"minimum": 0.25, "maximum": 5.75, "bucket_size": 2.5}
            assert table.rows()[0]["cells..mean"] == 4.25
            plot = original.create_plot(
                "histogram", data=table, config={"histogram_variable": "cells"}, name="Native cells"
            )
            assert_native_render(original, plot, engine, payload)
            original.save_dataset_snapshot("native-cells")
            original.save_portfolio("native-cells")
            capture = original.create_recovery_draft("native-owner")
            assert capture is not None
            recipe = original.capture_analysis_recipe("Native replay")
            wire = json.loads(original.export_analysis_recipe(recipe))
            assert wire["schema_version"] == 7
            assert wire["source"]["variables"][0]["params"] == config.params
            portfolio = json.loads(
                (PathService.get_portfolios_dir() / "native-cells.json").read_text()
            )
            assert portfolio["schema_version"] == 12 and portfolio["version"] == "12.0"

        with monkeypatch.context() as restore:
            no_parse = Mock(side_effect=AssertionError("Typed restoration must not reparse."))
            restore.setattr(Gem5Parser, "submit_parse_async", no_parse)
            with ring5.Session() as restored:
                assert restored.load_portfolio("native-cells").complete
                assert_native_render(restored, restored.plots[0], engine, payload)
                restored.load_dataset_snapshot("native-cells", "snapshot")
                snapshot = restored.get_dataset()
                assert snapshot.frame.attrs["ring5.distribution_layouts"]["cells"] == payload
                plot = restored.create_plot(
                    "histogram", data=snapshot, config={"histogram_variable": "cells"}
                )
                assert_native_render(restored, plot, engine, payload)
            with ring5.Session() as recovered:
                assert recovered.restore_recovery_draft(
                    "native-owner", capture.draft.draft_id
                ).complete
                assert_native_render(recovered, recovered.plots[0], engine, payload)
            no_parse.assert_not_called()

        with monkeypatch.context() as replay:
            no_scan = Mock(side_effect=AssertionError("Captured parser replay must not rescan."))
            parse_once = Mock(wraps=Gem5Parser.submit_parse_async)
            replay.setattr(Gem5Parser, "submit_scan_async", no_scan)
            replay.setattr(Gem5Parser, "submit_parse_async", parse_once)
            with ring5.Session() as repeated:
                repeated.run_analysis_recipe(recipe)
                assert_native_render(repeated, repeated.plots[0], engine, payload)
                assert repeated.capture_analysis_recipe("Again").source == recipe.source
            no_scan.assert_not_called()
            assert parse_once.call_count == 1
    finally:
        PathService.reset_caches()
