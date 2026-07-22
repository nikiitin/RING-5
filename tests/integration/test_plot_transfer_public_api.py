"""Public API coverage for destination-only plot content transfers."""

from __future__ import annotations

import pandas as pd
import pytest

import ring5

pytestmark = pytest.mark.public_api


def _plots(session: ring5.Session) -> tuple[object, object]:
    data = pd.DataFrame({"benchmark": ["A", "B"], "ipc": [1.0, 2.0]})
    source = session.create_plot(
        "bar",
        data=data,
        config={
            "x": "benchmark",
            "y": "ipc",
            "title": "Source",
            "font_family": "serif",
            "color_palette": "wong",
        },
        name="Source",
    )
    target = session.create_plot(
        "bar",
        data=data.copy(),
        config={"x": "benchmark", "y": "ipc", "title": "Target"},
        name="Target",
    )
    return source, target


def test_public_copy_supports_sections_configuration_and_pipeline() -> None:
    # [test->req~ring5.plots.copy-settings-pipeline~1]
    with ring5.Session() as session:
        source, target = _plots(session)

        selected = session.copy_plot_content(
            source, target, "settings", sections=["labels", "colors"]
        )
        assert isinstance(selected, ring5.PlotTransferResult)
        assert target.config["title"] == "Source"
        assert target.config["x"] == "benchmark"

        source.config["series_styles"] = {"ipc": {"color": "red"}}
        complete = session.copy_plot_content(source.plot_id, target.plot_id, "configuration")
        assert "series_styles" in complete.copied_keys
        source.config["series_styles"]["ipc"]["color"] = "blue"
        assert target.config["series_styles"]["ipc"]["color"] == "red"

        source.pipeline = [{"id": 1, "type": "sort", "config": {"order_dict": {"benchmark": True}}}]
        source.pipeline_counter = 1
        pipeline = session.copy_plot_content(source, target, "pipeline")
        assert pipeline.requires_finalize
        assert target.processed_data is None
        assert target.pipeline == source.pipeline


def test_public_copy_reports_typed_compatibility_errors() -> None:
    with ring5.Session() as session:
        source, target = _plots(session)
        line = session.create_plot(
            "line",
            data=pd.DataFrame({"benchmark": ["A"], "ipc": [1.0]}),
            config={"x": "benchmark", "y": "ipc"},
        )
        with pytest.raises(ring5.DataValidationError, match="same plot type"):
            session.copy_plot_content(source, line, "configuration")
        with pytest.raises(ring5.DataValidationError, match="unknown plot IDs"):
            session.copy_plot_content(999, target, "settings", sections=["labels"])
