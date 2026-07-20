"""Public API coverage for reversible plot source-row drill-down."""

from __future__ import annotations

import pandas as pd
import pytest

import ring5

pytestmark = pytest.mark.public_api


def test_public_drill_down_recovers_aggregate_source_rows_without_mutation() -> None:
    # [test->req~ring5.plots.drill-down~1]
    source = pd.DataFrame(
        {
            "workload": ["A", "A", "B"],
            "seed": [0, 1, 0],
            "ipc": [1.0, 1.2, 0.8],
        }
    )
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=source,
            config={"x": "workload", "y": "ipc"},
        )
        plot.replace_processed_data(source.groupby("workload", as_index=False)["ipc"].mean())
        config_snapshot = dict(plot.config)

        result = session.drill_down(plot, {"workload": "A"})

        assert isinstance(result, ring5.DrillDownResult)
        assert result.row_count == 2
        assert result.rows["seed"].tolist() == [0, 1]
        assert plot.config == config_snapshot
        assert source["ipc"].tolist() == [1.0, 1.2, 0.8]

        by_id = session.drill_down(plot.plot_id, {"workload": "B"})
        assert by_id.rows["seed"].tolist() == [0]


def test_public_drill_down_uses_typed_validation_errors() -> None:
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=pd.DataFrame({"x": ["A"], "y": [1.0]}),
            config={"x": "x", "y": "y"},
        )
        with pytest.raises(ring5.DataValidationError, match="unknown plot ID"):
            session.drill_down(999, {"x": "A"})
        with pytest.raises(ring5.DataValidationError, match="plot ID"):
            session.drill_down(True, {"x": "A"})
        with pytest.raises(ring5.DataValidationError, match="no column"):
            session.drill_down(plot, {"missing": "A"})
        with pytest.raises(ring5.DataValidationError, match="scalar"):
            session.drill_down(plot, {"x": ["A"]})

        plot.replace_source_data(None)
        plot.replace_processed_data(None)
        with pytest.raises(ring5.DataValidationError, match="no source data"):
            session.drill_down(plot, {})
