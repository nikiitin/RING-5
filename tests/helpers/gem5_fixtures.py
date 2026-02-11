"""Shared gem5 test fixtures — synthetic data for always-runnable integration tests.

Provides paths to synthetic gem5 stats files and pre-built directory
structures that mirror real gem5 output, ensuring integration tests
never skip due to missing data.
"""

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SYNTHETIC_ROOT = Path(__file__).parent.parent / "data" / "synthetic"


# ---------------------------------------------------------------------------
# Directory-level fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_stats_root() -> Path:
    """Root of all synthetic gem5 test data."""
    assert _SYNTHETIC_ROOT.exists(), f"Synthetic data missing: {_SYNTHETIC_ROOT}"
    return _SYNTHETIC_ROOT


@pytest.fixture
def synthetic_single_stats(synthetic_stats_root: Path) -> Path:
    """Path to a single-benchmark stats directory (scalar + vector stats)."""
    return synthetic_stats_root / "single"


@pytest.fixture
def synthetic_multi_cpu_stats(synthetic_stats_root: Path) -> Path:
    """Path to stats with cpu0–cpu3 + controller patterns for aggregation."""
    return synthetic_stats_root / "multi_cpu"


@pytest.fixture
def synthetic_histogram_stats(synthetic_stats_root: Path) -> Path:
    """Path to stats containing histogram data with bins and statistics."""
    return synthetic_stats_root / "histogram"


@pytest.fixture
def synthetic_multi_dump_stats(synthetic_stats_root: Path) -> Path:
    """Path to stats with 3 Begin/End dump blocks (simpoint simulation)."""
    return synthetic_stats_root / "multi_dump"


@pytest.fixture
def synthetic_benchmarks_dir(synthetic_stats_root: Path) -> Path:
    """Multi-benchmark directory structure: {bench}/{config}/{seed}/stats.txt.

    Structure::

        benchmarks/
        ├── mcf/baseline/{0,1}/stats.txt
        ├── omnetpp/baseline/0/stats.txt
        └── xalancbmk/baseline/0/stats.txt
    """
    return synthetic_stats_root / "benchmarks"
