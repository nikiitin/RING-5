"""
Backward-compatibility shim for ParseService.

The canonical implementation is ``Gem5Parser`` in
``src.parsing.gem5.impl.gem5_parser``.  This module re-exports
the class (aliased as *ParseService*) together with the symbols that
existing test-suites patch through this module path.

New code should import from the canonical location or from
``src.parsing`` (which re-exports ``ParseService`` via
``__init__.py``).
"""

from src.core.services.data_services.pattern_index_service import PatternIndexService

# Canonical implementation
from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

# Re-exports required by test @patch targets
from src.parsing.gem5.impl.pool.pool import ParseWorkPool
from src.parsing.gem5.impl.strategies.factory import StrategyFactory

__all__ = ["ParseService", "ParseWorkPool", "StrategyFactory", "PatternIndexService"]
