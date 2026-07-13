"""
Stat Types Package

Auto-registering type system for gem5 statistics.

Usage:
    from src.parsing.gem5.types import StatTypeRegistry

    # Create by name
    scalar = StatTypeRegistry.create("scalar", repeat=1)
    vector = StatTypeRegistry.create("vector", repeat=1, entries=["0", "1"])

    # Get available types
    types = StatTypeRegistry.get_types()
"""

# Import type modules to trigger self-registration (intentionally unused)
from src.parsing.gem5.types import configuration as _configuration
from src.parsing.gem5.types import distribution as _distribution
from src.parsing.gem5.types import histogram as _histogram
from src.parsing.gem5.types import scalar as _scalar
from src.parsing.gem5.types import vector as _vector
from src.parsing.gem5.types.base import StatType, StatTypeRegistry, register_type

__all__ = [
    "StatType",
    "StatTypeRegistry",
    "register_type",
    "_configuration",
    "_distribution",
    "_histogram",
    "_scalar",
    "_vector",
]
