"""Test statistics-only parsing mode for distributions, histograms, and vectors."""

import pytest

from src.core.models.parsing_models import StatConfig

from src.parsing.gem5.types.type_mapper import TypeMapper
from src.parsing.gem5.impl.source_bindings import resolve_sources


class TestStatisticsOnlyMode:
    """Test that statistics_only flag correctly configures stat types."""

    # [test->req~ring5.ingestion.statistics-only~1]

    def test_distribution_statistics_only(self) -> None:
        """Distribution with statistics_only=True should skip bucket validation."""
        config = StatConfig(
            statistics_only=True,
            type="distribution",
            name="test_stat",
            params={
                "minimum": 0,
                "maximum": 100,
                "statistics": ["mean", "stdev"],
                "source_type": "distribution",
            },
        )

        dist = TypeMapper.create_stat(resolve_sources([config], None).accumulators[0])

        # Verify that statistics_only flag is set
        assert hasattr(dist, "_statistics_only")
        assert dist._statistics_only is True

        # Verify that minimum/maximum are set to 0 (no buckets)
        assert dist._minimum == 0
        assert dist._maximum == 0

        # Verify statistics are set
        assert dist._statistics == ["mean", "stdev"]

        # Test that content can be set with only statistics (no buckets)
        dist.content = {"mean": [10.5], "stdev": [2.3]}
        assert "mean" in dist.content
        assert "stdev" in dist.content

    def test_distribution_full_mode(self) -> None:
        """Distribution with statistics_only=False should require buckets."""
        config = StatConfig(
            statistics_only=False,
            type="distribution",
            name="test_stat",
            params={
                "minimum": 0,
                "maximum": 10,
                "statistics": ["mean", "stdev"],
                "source_type": "distribution",
            },
        )

        dist = TypeMapper.create_stat(resolve_sources([config], None).accumulators[0])

        # Verify that statistics_only flag is False
        assert dist._statistics_only is False

        # Verify that minimum/maximum are properly set
        assert dist._minimum == 0
        assert dist._maximum == 10

        # Test that setting content requires buckets
        with pytest.raises(TypeError, match="Missing mandatory keys"):
            dist.content = {"mean": [10.5], "stdev": [2.3]}

    def test_vector_statistics_only(self) -> None:
        """Vector with statistics_only=True should use only statistics entries."""
        config = StatConfig(
            statistics_only=True,
            type="vector",
            name="test_stat",
            params={
                "entries": ["entry0", "entry1", "entry2"],
                "statistics": ["mean", "sum"],
                "source_type": "vector",
            },
        )

        vec = TypeMapper.create_stat(resolve_sources([config], None).accumulators[0])

        # When statistics_only, entries should be just the statistics
        assert vec.entries == ["mean", "sum"]

    def test_histogram_statistics_only(self) -> None:
        """Histogram with statistics_only=True should skip bins."""
        config = StatConfig(
            statistics_only=True,
            type="histogram",
            name="test_stat",
            params={
                "bins": 10,
                "max_range": 100.0,
                "entries": ["0-10", "10-20"],
                "statistics": ["mean", "samples"],
                "source_type": "histogram",
            },
        )

        hist = TypeMapper.create_stat(resolve_sources([config], None).accumulators[0])

        # Verify bins are disabled
        assert hist._bins == 0
        assert hist._max_range == 0.0
        assert object.__getattribute__(hist, "_entries") is None

        # Statistics should be preserved
        assert hist._statistics == ["mean", "samples"]

    def test_distribution_default_statistics_only(self) -> None:
        """Test that statistics_only defaults to False if not specified."""
        config = StatConfig(
            type="distribution",
            name="test_stat",
            params={
                "minimum": 0,
                "maximum": 10,
                "statistics": ["mean"],
                "source_type": "distribution",
            },
        )

        dist = TypeMapper.create_stat(resolve_sources([config], None).accumulators[0])

        # Should default to False (full bucket mode)
        assert dist._statistics_only is False
        assert dist._minimum == 0
        assert dist._maximum == 10
