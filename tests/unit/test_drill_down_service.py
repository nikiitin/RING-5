"""Tests for non-mutating source-row drill-down resolution."""

import pandas as pd
import pytest

from src.core.services.visualization.drill_down_service import drill_down_rows


def test_drill_down_matches_grouped_source_rows_and_returns_defensive_copies() -> None:
    # [test->req~ring5.plots.drill-down~1]
    source = pd.DataFrame(
        {
            "workload": [1, 1, 2, 1],
            "variant": ["base", "base", "base", "new"],
            "seed": [0, 1, 0, 0],
            "ipc": [1.0, 1.2, 0.8, 1.4],
        }
    )
    snapshot = source.copy(deep=True)

    result = drill_down_rows(4, source, {"workload": "1", "variant": "base"})

    assert result.plot_id == 4
    assert result.filters == (("workload", "1"), ("variant", "base"))
    assert result.row_count == 2
    assert result.columns == ("workload", "variant", "seed", "ipc")
    assert result.rows["seed"].tolist() == [0, 1]
    assert source.equals(snapshot)

    detached = result.rows
    detached.loc[:, "ipc"] = 99.0
    assert result.rows["ipc"].tolist() == [1.0, 1.2]


def test_drill_down_without_dimensions_returns_complete_source_snapshot() -> None:
    source = pd.DataFrame({"value": [1, 2]})

    result = drill_down_rows(0, source, {})

    assert result.row_count == 2
    source.loc[0, "value"] = 99
    assert result.rows["value"].tolist() == [1, 2]


def test_drill_down_matches_browser_iso_dates() -> None:
    source = pd.DataFrame({"when": pd.to_datetime(["2026-01-01", "2026-01-02"]), "value": [1, 2]})

    result = drill_down_rows(2, source, {"when": "2026-01-02T00:00:00"})

    assert result.rows["value"].tolist() == [2]


def test_drill_down_rejects_invalid_identifiers_filters_and_columns() -> None:
    source = pd.DataFrame({"category": ["A"]})

    with pytest.raises(ValueError, match="plot ID"):
        drill_down_rows(True, source, {})
    with pytest.raises(ValueError, match="pandas DataFrame"):
        drill_down_rows(1, object(), {})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="mapping"):
        drill_down_rows(1, source, [])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-empty strings"):
        drill_down_rows(1, source, {"": "A"})
    with pytest.raises(ValueError, match="no column"):
        drill_down_rows(1, source, {"missing": "A"})
    with pytest.raises(ValueError, match="scalar"):
        drill_down_rows(1, source, {"category": ["A"]})
