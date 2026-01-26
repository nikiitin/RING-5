"""
Workers Package for Parallel Stats Parsing

Provides:
- ParseWork: Base class for parsing work units
- ParseWorkPool: Singleton pool for managing parallel parsing jobs
- Gem5ParseWork: Worker for parsing gem5 stats files
"""

from src.parsers.workers.gem5_parse_work import Gem5ParseWork
from src.parsers.workers.parse_work import ParseWork
from src.parsers.workers.pool import ParseWorkPool

__all__ = ["ParseWork", "Gem5ParseWork", "ParseWorkPool"]
