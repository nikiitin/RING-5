"""
Strategy Factory - Creates FileParserStrategy Instances.

Centralises strategy instantiation so that ParseService (and any future
consumer) never needs inline imports or if/elif chains.

Usage:
    >>> strategy = StrategyFactory.create("simple")
    >>> strategy = StrategyFactory.create("config_aware")
"""

from src.core.parsing.strategies.interface import FileParserStrategy


class StrategyFactory:
    """Factory for creating FileParserStrategy instances by name."""

    @staticmethod
    def create(strategy_type: str) -> FileParserStrategy:
        """Return a strategy instance for the given type key.

        Args:
            strategy_type: One of ``"simple"`` or ``"config_aware"``.

        Returns:
            A concrete strategy implementing :class:`FileParserStrategy`.

        Raises:
            ValueError: If *strategy_type* is not recognised.
        """
        # Lazy imports to avoid circular dependency at module level
        if strategy_type == "simple":
            from src.core.parsing.strategies.simple import SimpleStatsStrategy

            return SimpleStatsStrategy()

        if strategy_type == "config_aware":
            from src.core.parsing.strategies.config_aware import (
                ConfigAwareStrategy,
            )

            return ConfigAwareStrategy()

        raise ValueError(
            f"Unknown strategy type: '{strategy_type}'. "
            f"Supported types: 'simple', 'config_aware'"
        )
