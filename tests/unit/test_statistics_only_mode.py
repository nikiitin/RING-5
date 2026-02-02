"""Test statistics-only parsing mode for distributions, histograms, and vectors."""

import pytest

from src.parsers.type_mapper import TypeMapper


class TestStatisticsOnlyMode:
    """Test that statisticsOnly flag correctly configures stat types."""

    def test_distribution_statistics_only(self):
        """Distribution with statisticsOnly=True should skip bucket validation."""
        config = {
            "type": "distribution",
            "minimum": 0,
            "maximum": 100,
            "statistics": ["mean", "stdev"],
            "statisticsOnly": True,
        }

        dist = TypeMapper.create_stat(config)

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

    def test_distribution_full_mode(self):
        """Distribution with statisticsOnly=False should require buckets."""
        config = {
            "type": "distribution",
            "minimum": 0,
            "maximum": 10,
            "statistics": ["mean", "stdev"],
            "statisticsOnly": False,
        }

        dist = TypeMapper.create_stat(config)

        # Verify that statistics_only flag is False
        assert dist._statistics_only is False

        # Verify that minimum/maximum are properly set
        assert dist._minimum == 0
        assert dist._maximum == 10

        # Test that setting content requires buckets
        with pytest.raises(TypeError, match="Missing mandatory keys"):
            dist.content = {"mean": [10.5], "stdev": [2.3]}

    def test_vector_statistics_only(self):
        """Vector with statisticsOnly=True should use only statistics entries."""
        config = {
            "type": "vector",
            "entries": ["entry0", "entry1", "entry2"],
            "statistics": ["mean", "sum"],
            "statisticsOnly": True,
        }

        vec = TypeMapper.create_stat(config)

        # When statistics_only, entries should be just the statistics
        assert vec._entries == ["mean", "sum"]

    def test_histogram_statistics_only(self):
        """Histogram with statisticsOnly=True should skip bins."""
        config = {
            "type": "histogram",
            "bins": 10,
            "max_range": 100.0,
            "entries": ["0-10", "10-20"],
            "statistics": ["mean", "samples"],
            "statisticsOnly": True,
        }

        hist = TypeMapper.create_stat(config)

        # Verify bins are disabled
        assert hist._bins == 0
        assert hist._max_range == 0.0
        assert hist._entries is None

        # Statistics should be preserved
        assert hist._statistics == ["mean", "samples"]

    def test_distribution_default_statistics_only(self):
        """Test that statisticsOnly defaults to False if not specified."""
        config = {
            "type": "distribution",
            "minimum": 0,
            "maximum": 10,
            "statistics": ["mean"],
        }

        dist = TypeMapper.create_stat(config)

        # Should default to False (full bucket mode)
        assert dist._statistics_only is False
        assert dist._minimum == 0
        assert dist._maximum == 10
