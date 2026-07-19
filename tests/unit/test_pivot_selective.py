import pandas as pd
import pytest

from src.core.services.shapers.impl.pivot import PivotLonger, PivotWider


def test_pivot_longer_selective_discard():
    # Setup data
    # [test->req~ring5.shaping.pivot-longer~1]
    data = pd.DataFrame(
        {
            "config": ["base", "base"],
            "tick": [100, 200],
            "system.cpu0.ipc": [1.0, 1.1],
            "system.cpu1.ipc": [0.8, 0.9],
            "system.cpu2.ipc": [1.2, 1.3],
        }
    )

    # Config: keep only cpu0 and cpu1, discard cpu2
    params = {
        "type": "pivotLonger",
        "id_vars": ["config", "tick"],
        "value_vars": ["system.cpu0.ipc", "system.cpu1.ipc", "system.cpu2.ipc"],
        "var_name": "cpu",
        "value_name": "ipc",
        "extract_pattern": r"system\.cpu(\d+)\.ipc",
        "extract_group_indices": [1],
        "selection_filters": {1: ["0", "1"]},
        "selection_strategy": "discard",
    }

    shaper = PivotLonger(params)
    result = shaper(data)

    # Verify rows: should have 4 rows (2 ticks * 2 CPUs)
    assert len(result) == 4
    assert set(result["cpu"].unique()) == {"0", "1"}
    assert "2" not in result["cpu"].values


def test_pivot_longer_selective_merge():
    # Setup data
    # [test->req~ring5.shaping.pivot-longer~1]
    data = pd.DataFrame(
        {"config": ["base"], "tick": [100], "cpu0": [10], "cpu1": [20], "cpu2": [30], "cpu3": [40]}
    )

    # Config: keep cpu0, merge cpu1-3 into "others"
    params = {
        "type": "pivotLonger",
        "id_vars": ["config", "tick"],
        "value_vars": ["cpu0", "cpu1", "cpu2", "cpu3"],
        "var_name": "cpuid",
        "value_name": "val",
        "extract_pattern": r"cpu(\d+)",
        "extract_group_indices": [1],
        "selection_filters": {1: ["0"]},
        "selection_strategy": "merge",
        "merge_label": "others",
    }

    shaper = PivotLonger(params)
    result = shaper(data)

    # Verify rows: should have 2 rows (cpu0 and merged others)
    assert len(result) == 2
    assert "0" in result["cpuid"].values
    assert "others" in result["cpuid"].values

    # Verify aggregated value: cpu1(20) + cpu2(30) + cpu3(40) = 90
    merged_val = result[result["cpuid"] == "others"]["val"].iloc[0]
    assert merged_val == 90


def test_pivot_longer_multi_group_extraction():
    # Setup data
    # [test->req~ring5.shaping.pivot-longer~1]
    data = pd.DataFrame(
        {"config": ["base"], "l0_cntrl0": [5], "l0_cntrl1": [10], "l1_cntrl0": [15]}
    )

    # Extract both level and controller
    params = {
        "type": "pivotLonger",
        "id_vars": ["config"],
        "value_vars": ["l0_cntrl0", "l0_cntrl1", "l1_cntrl0"],
        "var_name": "component",
        "value_name": "val",
        "extract_pattern": r"l(\d+)_cntrl(\d+)",
        "extract_group_indices": [1, 2],
        "extract_separator": "-",
        "selection_filters": {1: ["0", "1"], 2: ["0", "1"]},
        "selection_strategy": "discard",
    }

    shaper = PivotLonger(params)
    result = shaper(data)

    assert len(result) == 3
    assert set(result["component"].unique()) == {"0-0", "0-1", "1-0"}


def test_pivot_longer_rejects_expression_that_exceeds_timeout():
    data = pd.DataFrame({"config": ["base"], "a" * 4095 + "!": [1]})
    value_column = str(data.columns[1])
    params = {
        "type": "pivotLonger",
        "id_vars": ["config"],
        "value_vars": [value_column],
        "var_name": "component",
        "value_name": "value",
        "extract_pattern": r"(a+)+$",
        "extract_group_indices": [1],
    }

    with pytest.raises(ValueError, match="matching exceeded"):
        PivotLonger(params)(data)


def test_pivot_wider_reshapes_long_table():
    # [test->req~ring5.shaping.pivot-wider~1]
    data = pd.DataFrame(
        {
            "benchmark": ["mcf", "mcf", "xalanc", "xalanc"],
            "statistic": ["ipc", "cycles", "ipc", "cycles"],
            "value": [1.2, 100, 0.8, 140],
        }
    )

    result = PivotWider({"index": ["benchmark"], "columns": "statistic", "values": "value"})(data)

    assert list(result.columns) == ["benchmark", "cycles", "ipc"]
    assert result.to_dict("records") == [
        {"benchmark": "mcf", "cycles": 100.0, "ipc": 1.2},
        {"benchmark": "xalanc", "cycles": 140.0, "ipc": 0.8},
    ]
