from src.processing.shapers.impl.mean import Mean
from src.processing.shapers.impl.normalize import Normalize
from src.processing.shapers.impl.selector_algorithms.columnSelector import \
    ColumnSelector
from src.processing.shapers.impl.selector_algorithms.conditionSelector import \
    ConditionSelector
from src.processing.shapers.impl.selector_algorithms.itemSelector import \
    ItemSelector
from src.processing.shapers.impl.sort import Sort
from src.processing.shapers.base_shaper import Shaper


from src.processing.shapers.impl.transformer import Transformer

class ShaperFactory:
    """
    Factory class for creating shapers.
    """

    @classmethod
    def createShaper(cls, type: str, params: dict) -> Shaper:
        """
        Creates a shaper based on the type and parameters.
        """
        if type == "mean":
            return Mean(params)
        elif type == "columnSelector":
            return ColumnSelector(params)
        elif type == "conditionSelector":
            return ConditionSelector(params)
        elif type == "itemSelector":
            return ItemSelector(params)
        elif type == "normalize":
            return Normalize(params)
        elif type == "sort":
            return Sort(params)
        elif type == "transformer":
            return Transformer(params)
        else:
            raise ValueError("Invalid shaper type")
