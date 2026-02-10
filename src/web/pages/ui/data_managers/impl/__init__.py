"""
Concrete Data Manager Implementations.

Provides specific data transformation managers that implement the
DataManager ABC defined in the parent package.

Managers:
- MixerManager: Column merge/mix operations
- OutlierRemoverManager: Statistical outlier detection and removal
- PreprocessorManager: Data preprocessing and cleaning
- SeedsReducerManager: Seed-based data reduction
"""

from src.web.pages.ui.data_managers.impl.mixer import MixerManager
from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager
from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager
from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager

__all__ = [
    "MixerManager",
    "OutlierRemoverManager",
    "PreprocessorManager",
    "SeedsReducerManager",
]
