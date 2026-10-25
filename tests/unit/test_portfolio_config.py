"""Current portfolio writers retain plot configuration and both scientific tables."""

import json

import pandas as pd

from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.common.typed_table_codec import TypedTableCodec
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.plot_factory import PlotFactory


def test_portfolio_serialization() -> None:
    """Round-trip the current writer, codec, and plot factory together."""
    source = pd.DataFrame(
        {
            "benchmark": ["bench1", "bench2", "bench3"],
            "config": ["baseline", "optimized", "experimental"],
            "speedup": [2.0, 3.0, 4.0],
        },
        index=pd.Index([10, 20, 30], name="run"),
    )
    processed = source.assign(speedup=[1.0, 1.5, 2.0])
    config = {
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
    }
    plot = PlotFactory.create_plot("grouped_bar", 1, "Test Plot")
    plot.config = config
    plot.replace_source_data(source)
    plot.replace_processed_data(processed)
    service = PortfolioService(RepositoryStateManager())

    document = json.loads(service.serialize_workspace(source, [plot], {}, 2))
    restored_plot = PlotFactory.from_dict(document["plots"][0])

    assert restored_plot.name == "Test Plot"
    assert restored_plot.config == config
    pd.testing.assert_frame_equal(TypedTableCodec.decode(document["data"]), source)
    pd.testing.assert_frame_equal(restored_plot.source_data, source)
    pd.testing.assert_frame_equal(restored_plot.processed_data, processed)
    restored_plot.processed_data.loc[10, "speedup"] = 99.0
    assert restored_plot.source_data.loc[10, "speedup"] == 2.0
