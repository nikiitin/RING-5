"""
Simulator Registry — Factory for parser/scanner instantiation.

Provides a central registry for all supported simulator backends.
Each simulator registers a ``SimulatorInfo`` descriptor and a factory
function that creates a ``SimulationParser`` instance.

Usage:
    >>> from src.parsing.registry import SimulatorRegistry
    >>> parser = SimulatorRegistry.get_parser("gem5")
    >>> SimulatorRegistry.available_simulators()
    ['gem5']
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from src.parsing.parser_protocol import SimulationParser

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsingStrategy:
    """
    Metadata for a parsing strategy supported by a simulator backend.

    Attributes:
        name: Unique strategy identifier (e.g., ``"simple"``).
        display_name: Human-readable label for UI display.
        description: Brief explanation shown as tooltip/help text.
    """

    name: str
    display_name: str
    description: str = ""


@dataclass(frozen=True)
class SimulatorInfo:
    """
    Metadata for a registered simulator backend.

    Attributes:
        name: Unique identifier (e.g., ``"gem5"``).
        display_name: Human-readable name for UI display (e.g., ``"gem5"``).
        description: Brief description of the simulator.
        file_pattern: Default filename pattern to search for stats files.
        variable_types: List of variable type strings this simulator supports.
        internal_stats: Set of internal/meta-stats to exclude from variable
            selection (e.g., gem5's ``total``, ``mean``, ``stdev``).
        parsing_strategies: Ordered list of parsing strategies this simulator
            supports. Every simulator MUST specify at least one strategy.
    """

    name: str
    display_name: str
    description: str = ""
    file_pattern: str = "stats.txt"
    variable_types: list[str] = field(default_factory=list)
    internal_stats: frozenset[str] = field(default_factory=frozenset)
    parsing_strategies: list[ParsingStrategy] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate that at least one parsing strategy is defined."""
        if not self.parsing_strategies:
            raise ValueError(f"Simulator '{self.name}' must define at least one parsing strategy.")


class SimulatorRegistry:
    """
    Central registry for simulator parser backends.

    Singleton-style class registry. Simulators register themselves
    with a ``SimulatorInfo`` descriptor and a factory callable.
    """

    # [impl->req~ring5.ingestion.simulator-registry~1]

    _registry: dict[str, tuple[SimulatorInfo, Callable[[], SimulationParser]]] = {}
    _instances: dict[str, SimulationParser] = {}
    _instances_lock: threading.Lock = threading.Lock()

    @classmethod
    def register(
        cls,
        info: SimulatorInfo,
        factory: Callable[[], SimulationParser],
    ) -> None:
        """
        Register a simulator backend.

        Args:
            info: Metadata about the simulator.
            factory: Callable that creates a ``SimulationParser`` instance.

        Raises:
            ValueError: If a simulator with the same name is already registered.
        """
        # [impl->req~ring5.extension.parser-protocol~1]
        if info.name in cls._registry:
            raise ValueError(
                f"Simulator '{info.name}' is already registered. "
                "Use a unique name for each simulator backend."
            )
        cls._registry[info.name] = (info, factory)
        logger.info(f"Registered simulator: {info.display_name} ({info.name})")

    @classmethod
    def get_parser(cls, name: str) -> SimulationParser:
        """
        Get or create a parser instance for the named simulator.

        Uses lazy instantiation — the parser is created on first access
        and cached for subsequent calls.

        Args:
            name: Registered simulator name.

        Returns:
            A ``SimulationParser`` instance.

        Raises:
            KeyError: If no simulator with that name is registered.
        """
        # [impl->req~ring5.extension.parser-protocol~1]
        if name not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys())) or "(none)"
            raise KeyError(f"Unknown simulator '{name}'. Available: {available}")

        # Locked lazy-init so concurrent first calls create exactly one instance.
        with cls._instances_lock:
            if name not in cls._instances:
                _, factory = cls._registry[name]
                cls._instances[name] = factory()
                logger.info(f"Created parser instance for simulator: {name}")
            return cls._instances[name]

    @classmethod
    def get_info(cls, name: str) -> SimulatorInfo:
        """
        Get metadata for a registered simulator.

        Args:
            name: Registered simulator name.

        Returns:
            The ``SimulatorInfo`` for the simulator.

        Raises:
            KeyError: If no simulator with that name is registered.
        """
        if name not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys())) or "(none)"
            raise KeyError(f"Unknown simulator '{name}'. Available: {available}")
        info, _ = cls._registry[name]
        return info

    @classmethod
    def available_simulators(cls) -> list[str]:
        """
        List all registered simulator names.

        Returns:
            Sorted list of registered simulator name strings.
        """
        return sorted(cls._registry.keys())

    @classmethod
    def available_simulator_info(cls) -> list[SimulatorInfo]:
        """
        List metadata for all registered simulators.

        Returns:
            List of ``SimulatorInfo`` objects, sorted by name.
        """
        return [info for info, _ in sorted(cls._registry.values(), key=lambda x: x[0].name)]

    @classmethod
    def _reset(cls) -> None:
        """Reset registry state. For testing only."""
        cls._registry.clear()
        cls._instances.clear()


# Auto-register gem5
GEM5_INFO = SimulatorInfo(
    name="gem5",
    display_name="gem5",
    description="gem5 computer architecture simulator",
    file_pattern="stats.txt",
    variable_types=["scalar", "vector", "distribution", "histogram", "configuration"],
    internal_stats=frozenset(
        {
            "total",
            "mean",
            "gmean",
            "stdev",
            "samples",
            "sample_period",
            "min_val",
            "max_val",
            "min_bucket",
            "max_bucket",
            "num_buckets",
            "underflows",
            "overflows",
        }
    ),
    parsing_strategies=[
        ParsingStrategy(
            name="simple",
            display_name="Simple (stats.txt only)",
            description="Parse stats.txt files without config metadata.",
        ),
        ParsingStrategy(
            name="config_aware",
            display_name="Config-Aware (Integrates config.ini)",
            description=(
                "Config-Aware strategy allows extracting metadata " "from simulation config files."
            ),
        ),
    ],
)


def _create_gem5_parser() -> SimulationParser:
    """Factory function for gem5 parser."""
    from src.parsing.gem5.impl.gem5_parser import Gem5Parser

    return Gem5Parser()


SimulatorRegistry.register(GEM5_INFO, _create_gem5_parser)
