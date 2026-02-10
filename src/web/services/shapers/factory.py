from typing import Any, Dict, List, Optional, Type

from src.web.services.shapers.base_shaper import Shaper
from src.web.services.shapers.impl.mean import Mean
from src.web.services.shapers.impl.normalize import Normalize
from src.web.services.shapers.impl.selector_algorithms.columnSelector import (
    ColumnSelector,
)
from src.web.services.shapers.impl.selector_algorithms.conditionSelector import (
    ConditionSelector,
)
from src.web.services.shapers.impl.selector_algorithms.itemSelector import ItemSelector
from src.web.services.shapers.impl.sort import Sort
from src.web.services.shapers.impl.transformer import Transformer


class ShaperFactory:
    """
    Factory for instantiating data shapers (Factory Pattern).

    Provides a registry of available shaper implementations and a unified
    creation interface. Supports runtime registration for extensibility
    (Open/Closed Principle).
    """

    # Registry of shaper types mapping to their implementing classes
    _registry: Dict[str, Type[Shaper]] = {
        "mean": Mean,
        "columnSelector": ColumnSelector,
        "conditionSelector": ConditionSelector,
        "itemSelector": ItemSelector,
        "normalize": Normalize,
        "sort": Sort,
        "transformer": Transformer,
    }

    @classmethod
    def register(cls, shaper_type: str, shaper_class: Type[Shaper]) -> None:
        """
        Register a new shaper type for extensibility (Open/Closed Principle).

        Args:
            shaper_type: Unique identifier for the shaper type
            shaper_class: Class reference implementing the Shaper interface
        """
        cls._registry[shaper_type] = shaper_class

    @classmethod
    def get_available_types(cls) -> List[str]:
        """
        Return a list of all registered shaper type identifiers.

        Returns:
            List of shaper type strings (e.g., ['mean', 'normalize', 'sort'])
        """
        return list(cls._registry.keys())

    @classmethod
    def create_shaper(cls, shaper_type: str, params: Dict[str, Any]) -> Shaper:
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
        shaper_class: Optional[Type[Shaper]] = cls._registry.get(shaper_type)
        if shaper_class is None:
            available: str = ", ".join(cls._registry.keys())
            raise ValueError(
                f"FACTORY: Unknown shaper type '{shaper_type}'. " f"Available types: {available}"
            )
        return shaper_class(params)

    @classmethod
    def createShaper(cls, shaper_type: str, params: Dict[str, Any]) -> Shaper:
        """Backward compatibility alias for create_shaper."""
        return cls.create_shaper(shaper_type, params)
