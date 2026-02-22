"""
Backward-compatibility shim for ParseService.

The canonical implementation is ``Gem5Parser`` in
``src.core.parsing.gem5.impl.gem5_parser``.  This module re-exports
the class (aliased as *ParseService*) together with the symbols that
existing test-suites patch through this module path.

New code should import from the canonical location or from
``src.core.parsing`` (which re-exports ``ParseService`` via
``__init__.py``).
"""

# Canonical implementation
from src.core.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

# Re-exports required by test @patch targets
from src.core.parsing.gem5.impl.pool.pool import ParseWorkPool
from src.core.parsing.gem5.impl.strategies.factory import StrategyFactory
from src.core.services.data_services.pattern_index_service import PatternIndexService

__all__ = ["ParseService", "ParseWorkPool", "StrategyFactory", "PatternIndexService"]
