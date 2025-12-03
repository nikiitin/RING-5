from src.data_plotter.src.shaper.shaper import Shaper
from src.data_plotter.src.shaper.impl.mean import Mean
from data_plotter.src.shaper.impl.selector_algorithms.columnSelector import ColumnSelector
from data_plotter.src.shaper.impl.selector_algorithms.conditionSelector import ConditionSelector
from data_plotter.src.shaper.impl.selector_algorithms.itemSelector import ItemSelector
from src.data_plotter.src.shaper.impl.normalize import Normalize
from src.data_plotter.src.shaper.impl.sort import Sort


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
        else:
            raise ValueError("Invalid shaper type")
        