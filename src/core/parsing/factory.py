"""
Parser API Factory - Creates simulator-specific ParserAPI instances.

Provides a single entry point for obtaining a complete parser API
for any supported simulator backend.
"""

from typing import Dict, Type

from src.core.parsing.parser_api import ParserAPI


class ParserAPIFactory:
    """
    Factory for creating ParserAPI instances by simulator name.

    Usage:
        >>> api = ParserAPIFactory.create("gem5")
        >>> futures = api.submit_scan_async("/path/to/stats")
    """

    _registry: Dict[str, Type[ParserAPI]] = {}

    @classmethod
    def register(cls, name: str, api_cls: Type[ParserAPI]) -> None:
        """Register a ParserAPI implementation for a simulator."""
        cls._registry[name] = api_cls

    @classmethod
    def create(cls, simulator: str = "gem5") -> ParserAPI:
        """
        Create a ParserAPI instance for the specified simulator.

        Args:
            simulator: Simulator backend identifier (default: "gem5")

        Returns:
            A ParserAPI implementation for the specified simulator

        Raises:
            ValueError: If no implementation registered for the simulator
        """
        if simulator == "gem5":
            # Lazy import to avoid circular dependencies
            from src.core.parsing.gem5.impl.gem5_parser_api import Gem5ParserAPI

            return Gem5ParserAPI()

        if simulator in cls._registry:
            return cls._registry[simulator]()

        available = ", ".join(["gem5"] + list(cls._registry.keys()))
        raise ValueError(f"Unknown simulator: '{simulator}'. Available: {available}")
