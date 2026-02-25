"""Backward-compatibility shim — re-exports from canonical location.

.. deprecated::
    Import from ``src.core.services.visualization.plot_interaction`` instead.
    This shim will be removed in Phase 10 (Dead Code Removal).
"""

from src.core.services.visualization.plot_interaction import (  # noqa: F401
    resolve_item_order,
    try_float,
    try_float_edit,
    update_config_from_relayout,
)
