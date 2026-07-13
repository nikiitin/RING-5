"""
Shaper Factory - Dynamic Transformation Instantiation.

Implements the Factory pattern for creating shaper instances from configuration.
Dispatches to appropriate shaper class based on type identifier, supporting
all available transformation types (filter, sort, normalize, mean, etc.).

Enables runtime shaper selection and dynamic pipeline construction.
"""

from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.shapers.impl.derive_column import DeriveColumn
from src.core.services.shapers.impl.mean import Mean
from src.core.services.shapers.impl.normalize import Normalize
from src.core.services.shapers.impl.pivot import PivotLonger, PivotWider
from src.core.services.shapers.impl.selector_algorithms.column_selector import (
    ColumnSelector,
)
from src.core.services.shapers.impl.selector_algorithms.condition_selector import (
    ConditionSelector,
)
from src.core.services.shapers.impl.selector_algorithms.group_cardinality_selector import (
    GroupCardinalitySelector,
)
from src.core.services.shapers.impl.selector_algorithms.group_predicate_selector import (
    GroupPredicateSelector,
)
from src.core.services.shapers.impl.selector_algorithms.item_selector import (
    ItemSelector,
)
from src.core.services.shapers.impl.sort import Sort
from src.core.services.shapers.impl.split_apply import SplitApply
from src.core.services.shapers.impl.transformer import Transformer
from src.core.services.shapers.shaper import Shaper


class ShaperFactory:
    """
    Factory for instantiating data shapers (Factory Pattern).

    Provides a registry of available shaper implementations and a unified
    creation interface. Supports runtime registration for extensibility
    (Open/Closed Principle).
    """

    # Registry of shaper types mapping to their implementing classes
    _registry: dict[str, type[Shaper]] = {
        "mean": Mean,
        "columnSelector": ColumnSelector,
        "conditionSelector": ConditionSelector,
        "itemSelector": ItemSelector,
        "normalize": Normalize,
        "pivotLonger": PivotLonger,
        "pivotWider": PivotWider,
        "sort": Sort,
        "splitApply": SplitApply,
        "transformer": Transformer,
        "deriveColumn": DeriveColumn,
        "groupCardinalitySelector": GroupCardinalitySelector,
        "groupPredicateSelector": GroupPredicateSelector,
    }

    # Human-readable display names for the UI layer
    _display_names: dict[str, str] = {
        "columnSelector": "Column Selector",
        "sort": "Sort",
        "mean": "Mean Calculator",
        "normalize": "Normalize",
        "pivotLonger": "Pivot Longer (Melt)",
        "pivotWider": "Pivot Wider",
        "conditionSelector": "Filter",
        "itemSelector": "Item Selector",
        "splitApply": "Split-Apply (Per-Axis)",
        "transformer": "Transformer",
        "deriveColumn": "Derive Column",
        "groupCardinalitySelector": "Group Cardinality Filter",
        "groupPredicateSelector": "Group Predicate Filter",
    }

    @classmethod
    def register(cls, shaper_type: str, shaper_class: type[Shaper]) -> None:
        """
        Register a new shaper type for extensibility (Open/Closed Principle).

        Args:
            shaper_type: Unique identifier for the shaper type
            shaper_class: Class reference implementing the Shaper interface
        """
        cls._registry[shaper_type] = shaper_class

    @classmethod
    def get_available_types(cls) -> list[str]:
        """
        Return a list of all registered shaper type identifiers.

        Returns:
            List of shaper type strings (e.g., ['mean', 'normalize', 'sort'])
        """
        return list(cls._registry.keys())

    @classmethod
    def get_display_name_map(cls) -> dict[str, str]:
        """
        Return mapping of display names to shaper type identifiers.

        Used by UI layers to show human-readable names in dropdowns and
        resolve back to type identifiers for pipeline construction.

        Returns:
            Dict mapping display name -> shaper type id.
            E.g., {"Column Selector": "columnSelector", "Sort": "sort", ...}
        """
        return {
            display: shaper_type
            for shaper_type, display in cls._display_names.items()
            if shaper_type in cls._registry
        }

    @classmethod
    def get_display_name(cls, shaper_type: str) -> str:
        """
        Get human-readable display name for a shaper type.

        Args:
            shaper_type: Internal shaper type identifier.

        Returns:
            Display name, or the type identifier if no display name exists.
        """
        return cls._display_names.get(shaper_type, shaper_type)

    @classmethod
    def create_shaper(cls, shaper_type: str, params: ShaperStepConfig) -> Shaper:
        """
        Instantiate a shaper of the specified type.

        Args:
            shaper_type: Registered type name
            params: Configuration dictionary passed to the shaper constructor

        Returns:
            An initialized Shaper instance

        Raises:
            ValueError: If the shaper_type is not found in the registry
        """
        shaper_class: type[Shaper] | None = cls._registry.get(shaper_type)
        if shaper_class is None:
            available: str = ", ".join(cls._registry.keys())
            raise ValueError(
                f"FACTORY: Unknown shaper type '{shaper_type}'. " f"Available types: {available}"
            )
        return shaper_class(dict(params))
