"""Public access to RING-5's data shapers.

The shaper *implementations* live under ``src.core.services.shapers.impl`` (a private
layer). This module is the **supported public import path** so user scripts never reach
into ``src.*``::

    from ring5.shapers import Mean
    long = Mean({"meanVars": cols, "meanAlgorithm": "arithmean",
                 "groupingColumns": ["policy"], "replacingColumn": "benchmark"})(df)

Each shaper is a stateless callable: ``Shaper(params)(table) -> table``. Prefer running a
sequence of them through :meth:`ring5.Session.shape` when you have a pipeline; import the
classes directly (here) when you need one transform inline. Direct constructors
and calls raise ordinary ``TypeError`` or ``ValueError`` for invalid inputs;
``Session.shape`` translates pipeline failures to ``ring5.errors.PipelineError``.
"""

from __future__ import annotations

from ring5.errors import PipelineError
from src.core.services.shapers.definition import ShaperDefinition
from src.core.services.shapers.shaper import Shaper
from src.core.services.shapers.impl.derive_column import DeriveColumn
from src.core.services.shapers.impl.mean import Mean
from src.core.services.shapers.impl.normalize import Normalize
from src.core.services.shapers.impl.pivot import PivotLonger, PivotWider
from src.core.services.shapers.impl.selector import Selector
from src.core.services.shapers.impl.selector_algorithms.column_selector import ColumnSelector
from src.core.services.shapers.impl.selector_algorithms.condition_selector import ConditionSelector
from src.core.services.shapers.impl.selector_algorithms.group_cardinality_selector import (
    GroupCardinalitySelector,
)
from src.core.services.shapers.impl.selector_algorithms.group_predicate_selector import (
    GroupPredicateSelector,
)
from src.core.services.shapers.impl.selector_algorithms.item_selector import ItemSelector
from src.core.services.shapers.impl.sort import Sort
from src.core.services.shapers.impl.split_apply import SplitApply
from src.core.services.shapers.impl.transformer import Transformer


def available_shaper_types() -> tuple[str, ...]:
    # [impl->req~ring5.api.registry-discovery~1]
    """Return every registered pipeline shaper identifier."""
    from src.core.services.shapers.factory import ShaperFactory

    return tuple(ShaperFactory.get_available_types())


def register_shaper(definition: ShaperDefinition) -> None:
    """Register one current plugin definition for pipeline construction.

    Args:
        definition: Strategy, exact TypedDict configuration, label and validator.

    Raises:
        PipelineError: Definition is malformed or duplicates an existing registration.
    """
    from src.core.services.shapers.factory import ShaperFactory

    try:
        ShaperFactory.register(definition)
    except (TypeError, ValueError) as exc:
        raise PipelineError(str(exc)) from exc


__all__ = [
    "Shaper",
    "ShaperDefinition",
    "register_shaper",
    "Mean",
    "Normalize",
    "Selector",
    "ColumnSelector",
    "ConditionSelector",
    "ItemSelector",
    "Sort",
    "SplitApply",
    "Transformer",
    "PivotLonger",
    "PivotWider",
    "DeriveColumn",
    "GroupCardinalitySelector",
    "GroupPredicateSelector",
    "available_shaper_types",
]
