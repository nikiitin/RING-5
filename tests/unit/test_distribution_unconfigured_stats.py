"""Tests for Distribution type handling of unconfigured statistics.

This module verifies that the Distribution type gracefully handles
statistics that appear in the data but were not specifically requested
in the configuration.
"""

from src.common.types import StatTypeRegistry


class TestDistributionUnconfiguredStats:
    """Test suite for Distribution handling of unconfigured statistics."""

    def test_distribution_ignores_unconfigured_stats(self):
        """
        Verify Distribution does not crash when receiving unconfigured stats.
        
        Scientific Integrity: The parser may encounter statistics in the gem5
        output that were not requested by the user. These should be silently
        ignored rather than causing a crash.
        """
        # Create distribution WITHOUT 'samples' in statistics
        dist = StatTypeRegistry.create(
            "distribution", 
            minimum=0, 
            maximum=10, 
            statistics=[]  # No stats requested
        )

        # Input content contains 'samples' (simulating parser output)
        content = {
            "underflows": [],
            "overflows": [],
            **{str(i): [] for i in range(11)},  # Populate 0..10
            "samples": ["100"],  # This was causing crashes
        }

        # Should NOT raise TypeError - verify no exception
        dist.content = content
        
        # Verify the expected buckets are still accessible
        assert "0" in dist.content
        assert "10" in dist.content

    def test_distribution_with_configured_stats(self):
        """
        Verify Distribution correctly processes configured statistics.
        """
        dist = StatTypeRegistry.create(
            "distribution",
            minimum=0,
            maximum=2,
            statistics=["samples", "mean"]
        )

        content = {
            "0": ["10"],
            "1": ["20"],
            "2": ["30"],
            "underflows": ["0"],
            "overflows": ["0"],
            "samples": ["100"],
            "mean": ["1.5"],
        }

        dist.content = content

        # Verify configured stats are present
        assert "samples" in dist.content
        assert "mean" in dist.content
        assert dist.content["samples"] == [100.0]
        assert dist.content["mean"] == [1.5]
