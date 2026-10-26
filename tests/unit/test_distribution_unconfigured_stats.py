"""Tests for distribution handling of unconfigured statistics."""

from src.parsing.gem5.types import StatTypeRegistry
from src.parsing.gem5.types.distribution import Distribution


class TestDistributionUnconfiguredStats:
    """Test suite for Distribution handling of unconfigured statistics."""

    def test_distribution_ignores_unconfigured_stats(self) -> None:
        """Ignore parsed statistics that were not requested."""
        dist = StatTypeRegistry.create(
            "distribution",
            minimum=0,
            maximum=10,
            bucket_size=1,
            zero_policy="missing",
            statistics=[],
        )

        assert isinstance(dist, Distribution)
        content = {
            "underflows": 0,
            "overflows": 0,
            **{str(i): 0 for i in range(11)},
            "samples": 100,
        }

        dist.add_observation(content)

        assert "0" in dist.content
        assert "10" in dist.content
        assert "samples" not in dist.content

    def test_distribution_with_configured_stats(self) -> None:
        """Process explicitly configured distribution statistics."""
        dist = StatTypeRegistry.create(
            "distribution",
            minimum=0,
            maximum=2,
            bucket_size=1,
            zero_policy="missing",
            statistics=["samples", "mean"],
        )

        assert isinstance(dist, Distribution)
        content = {
            "0": 10,
            "1": 20,
            "2": 30,
            "underflows": 0,
            "overflows": 0,
            "samples": 100,
            "mean": 1.5,
        }

        dist.add_observation(content)

        # Verify configured stats are present
        assert "samples" in dist.content
        assert "mean" in dist.content
        assert dist.content["samples"] == [100.0]
        assert dist.content["mean"] == [1.5]
