"""Test modularization and imports of RING-5 components."""

import sys
from pathlib import Path

import pandas as pd


def test_main_app_import():
    """Test that main app can be imported."""

    # Add parent directory to path to import app
    root_dir = Path(__file__).parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    import app

    # app.py now just has main() as the entry point
    assert hasattr(app, "main")


def test_modularized_pages_import():
    """Test that modularized pages can be imported."""
    from src.web.pages import manage_plots, portfolio

    assert hasattr(portfolio, "show_portfolio_page")
    assert hasattr(manage_plots, "show_manage_plots_page")
    assert hasattr(manage_plots, "apply_shapers")
    assert hasattr(manage_plots, "configure_shaper")


def test_shaper_factory_import():
    """Test that ShaperFactory can be imported and used."""
    from src.processing.shapers.factory import ShaperFactory

    # Test column selector shaper
    sample_data = pd.DataFrame(
        {
            "benchmark": ["bench1", "bench2", "bench3"],
            "config": ["A", "B", "A"],
            "value": [100, 200, 150],
        }
    )

    col_config = {"type": "columnSelector", "columns": ["benchmark", "value"]}
    shaper = ShaperFactory.createShaper("columnSelector", col_config)
    result = shaper(sample_data)
    assert len(result.columns) == 2
    assert "benchmark" in result.columns
    assert "value" in result.columns


def test_shapers_functionality():
    """Test that various shapers work correctly."""
    from src.processing.shapers.factory import ShaperFactory

    sample_data = pd.DataFrame(
        {
            "benchmark": ["bench1", "bench2", "bench3"],
            "config": ["A", "B", "A"],
            "value": [100, 200, 150],
        }
    )

    # Test sort shaper
    sort_config = {"type": "sort", "order_dict": {"benchmark": ["bench3", "bench1", "bench2"]}}
    shaper = ShaperFactory.createShaper("sort", sort_config)
    result = shaper(sample_data)
    assert result.iloc[0]["benchmark"] == "bench3"

    # Test normalize shaper configuration
    norm_config = {
        "type": "normalize",
        "normalizerVars": ["value"],
        "normalizeVars": ["value"],
        "normalizerColumn": "config",
        "normalizerValue": "A",
        "groupBy": ["benchmark"],
        "normalizeSd": True,
    }
    shaper = ShaperFactory.createShaper("normalize", norm_config)
    assert shaper is not None


def test_delegation_pattern():
    """Test that manage_plots has the shaper functions."""

    from src.web.pages import manage_plots

    # The shaper functions now live in manage_plots module
    assert callable(manage_plots.apply_shapers)
    assert callable(manage_plots.configure_shaper)
