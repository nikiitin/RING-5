from typing import Dict, Type

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
    Factory class for creating shapers using registry pattern.
    """

    # Registry of shaper types to their implementing classes
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
        Register a new shaper type.

        Args:
            shaper_type: The type identifier for the shaper.
            shaper_class: The class implementing the shaper.
        """
        cls._registry[shaper_type] = shaper_class

    @classmethod
    def get_available_types(cls) -> list:
        """Get list of registered shaper types."""
        return list(cls._registry.keys())

    @classmethod
    def createShaper(cls, shaper_type: str, params: dict) -> Shaper:
        """
        Creates a shaper based on the type and parameters.

        Args:
            shaper_type: The type of shaper to create.
            params: Configuration parameters for the shaper.

        Returns:
            An instance of the requested shaper.

        Raises:
            ValueError: If the shaper type is not registered.
        """
        if shaper_type not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise ValueError(f"Unknown shaper type: '{shaper_type}'. Available: {available}")
        return cls._registry[shaper_type](params)
