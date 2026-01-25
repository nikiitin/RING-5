"""
Stat Types Package

Auto-registering type system for gem5 statistics.

Usage:
    from src.parsing.types import StatTypeRegistry

    # Create by name
    scalar = StatTypeRegistry.create("scalar", repeat=1)
    vector = StatTypeRegistry.create("vector", repeat=1, entries=["0", "1"])

    # Get available types
    types = StatTypeRegistry.get_types()
"""

# Import type modules to trigger self-registration (intentionally unused)
from src.common.types import configuration as _configuration  # noqa: F401
from src.common.types import distribution as _distribution  # noqa: F401
from src.common.types import histogram as _histogram  # noqa: F401
from src.common.types import scalar as _scalar  # noqa: F401
from src.common.types import vector as _vector  # noqa: F401
from src.common.types.base import StatType, StatTypeRegistry, register_type

__all__ = ["StatType", "StatTypeRegistry", "register_type"]
