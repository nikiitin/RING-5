"""Test portfolio saving and loading with full plot configurations."""

import json
import tempfile
from pathlib import Path

import pandas as pd


def test_portfolio_serialization():
    """Test that plot configurations are properly saved and loaded."""

    # Create sample plot data
    sample_plot = {
        "id": 1,
        "name": "Test Plot",
        "pipeline": [{"type": "columnSelector", "config": {"columns": ["col1", "col2"]}, "id": 0}],
        "pipeline_counter": 1,
        "plot_type": "grouped_bar",
        "plot_config": {
            "type": "grouped_bar",
            "x": "benchmark",
            "y": "speedup",
            "group": "config",
            "color": "config",
            "title": "Performance Comparison",
            "xlabel": "Benchmark",
            "ylabel": "Speedup",
            "width": 1000,
            "height": 700,
            "legend_title": "Configuration",
            "show_error_bars": True,
            "download_format": "pdf",
            "legend_labels": {
                "baseline": "Baseline Config",
                "optimized": "Optimized Config",
                "experimental": "Experimental Config",
            },
        },
        "legend_mappings": {
            "baseline": "Baseline Config",
            "optimized": "Optimized Config",
            "experimental": "Experimental Config",
        },
        "processed_data": pd.DataFrame(
            {
                "benchmark": ["bench1", "bench2", "bench3"],
                "config": ["baseline", "optimized", "experimental"],
                "speedup": [1.0, 1.5, 2.0],
            }
        ),
    }

    # Serialize the plot (convert DataFrame to CSV)
    serialized_plot = sample_plot.copy()
    if isinstance(serialized_plot["processed_data"], pd.DataFrame):
        serialized_plot["processed_data"] = serialized_plot["processed_data"].to_csv(index=False)

    # Create portfolio data
    portfolio_data = {
        "version": "1.0",
        "timestamp": pd.Timestamp.now().isoformat(),
        "data_csv": sample_plot["processed_data"].to_csv(index=False),
        "csv_path": "/path/to/data.csv",
        "plots": [serialized_plot],
        "plot_counter": 2,
        "config": {},
    }

    # Test JSON serialization
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)
        json.dump(portfolio_data, f, indent=2)

    # Load it back
    with open(temp_path, "r") as f:
        loaded_portfolio = json.load(f)

    # Deserialize plot
    loaded_plot = loaded_portfolio["plots"][0]
    if isinstance(loaded_plot["processed_data"], str):
        loaded_plot["processed_data"] = pd.read_csv(
            pd.io.common.StringIO(loaded_plot["processed_data"])
        )

    # Verify all configurations are preserved
    assert loaded_plot["plot_config"]["type"] == "grouped_bar"
    assert loaded_plot["plot_config"]["x"] == "benchmark"
    assert loaded_plot["plot_config"]["y"] == "speedup"
    assert loaded_plot["plot_config"]["group"] == "config"
    assert loaded_plot["plot_config"]["title"] == "Performance Comparison"
    assert loaded_plot["plot_config"]["width"] == 1000
    assert loaded_plot["plot_config"]["height"] == 700
    assert loaded_plot["plot_config"]["legend_title"] == "Configuration"
    assert loaded_plot["plot_config"]["show_error_bars"] is True
    assert loaded_plot["plot_config"]["download_format"] == "pdf"

    # Verify legend labels
    assert "legend_labels" in loaded_plot["plot_config"]
    assert loaded_plot["plot_config"]["legend_labels"]["baseline"] == "Baseline Config"
    assert loaded_plot["plot_config"]["legend_labels"]["optimized"] == "Optimized Config"
    assert loaded_plot["plot_config"]["legend_labels"]["experimental"] == "Experimental Config"

    # Verify legend_mappings
    assert "legend_mappings" in loaded_plot
    assert loaded_plot["legend_mappings"]["baseline"] == "Baseline Config"

    # Verify processed data
    assert isinstance(loaded_plot["processed_data"], pd.DataFrame)
    assert len(loaded_plot["processed_data"]) == 3
    assert "benchmark" in loaded_plot["processed_data"].columns
    assert "speedup" in loaded_plot["processed_data"].columns

    # Cleanup
    temp_path.unlink()
