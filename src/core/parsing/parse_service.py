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
from src.core.parsing.gem5.impl.gem5_parser import (  # noqa: F401
    Gem5Parser as ParseService,
)

# Re-exports required by test @patch targets
from src.core.parsing.gem5.impl.pool.pool import ParseWorkPool  # noqa: F401
from src.core.parsing.gem5.impl.strategies.factory import (  # noqa: F401
    StrategyFactory,
)
from src.core.services.data_services.pattern_index_service import (  # noqa: F401
    PatternIndexService,
)

__all__ = ["ParseService"]
