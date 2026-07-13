"""Public access to RING-5's data shapers.

The shaper *implementations* live under ``src.core.services.shapers.impl`` (a private
layer). This module is the **supported public import path** so user scripts never reach
into ``src.*``::

    from ring5.shapers import Mean
    long = Mean({"meanVars": cols, "meanAlgorithm": "arithmean",
                 "groupingColumns": ["policy"], "replacingColumn": "benchmark"})(df)

Each shaper is a stateless callable: ``Shaper(params)(table) -> table``. Prefer running a
sequence of them through :meth:`ring5.Session.shape` when you have a pipeline; import the
classes directly (here) when you need one transform inline.
"""

from __future__ import annotations

from src.core.services.shapers.impl.derive_column import DeriveColumn
from src.core.services.shapers.impl.mean import Mean
from src.core.services.shapers.impl.normalize import Normalize
from src.core.services.shapers.impl.pivot import PivotLonger, PivotWider
from src.core.services.shapers.impl.selector import Selector
from src.core.services.shapers.impl.selector_algorithms.group_cardinality_selector import (
    GroupCardinalitySelector,
)
from src.core.services.shapers.impl.selector_algorithms.group_predicate_selector import (
    GroupPredicateSelector,
)
from src.core.services.shapers.impl.sort import Sort
from src.core.services.shapers.impl.split_apply import SplitApply
from src.core.services.shapers.impl.transformer import Transformer

__all__ = [
    "Mean",
    "Normalize",
    "Selector",
    "Sort",
    "SplitApply",
    "Transformer",
    "PivotLonger",
    "PivotWider",
    "DeriveColumn",
    "GroupCardinalitySelector",
    "GroupPredicateSelector",
]
