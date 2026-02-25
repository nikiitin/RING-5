"""Backward-compatibility shim — re-exports from canonical location.

.. deprecated::
    Import from ``src.core.services.visualization.config_resolver`` instead.
    This shim will be removed in Phase 10 (Dead Code Removal).
"""

from src.core.services.visualization.config_resolver import (  # noqa: F401
    SENTINEL_FLOAT,
    SENTINEL_INT,
    resolve_config,
)
