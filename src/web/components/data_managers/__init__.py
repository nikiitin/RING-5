"""Data Manager Components.

Provides specific data transformation managers that implement the
DataManager ABC.
"""

from src.web.components.data_managers.data_manager import DataManager
from src.web.components.data_managers.mixer import MixerManager
from src.web.components.data_managers.comparison import ComparisonManager
from src.web.components.data_managers.outlier_remover import OutlierRemoverManager
from src.web.components.data_managers.preprocessor import PreprocessorManager
from src.web.components.data_managers.seeds_reducer import SeedsReducerManager

__all__ = [
    "ComparisonManager",
    "DataManager",
    "MixerManager",
    "OutlierRemoverManager",
    "PreprocessorManager",
    "SeedsReducerManager",
]
