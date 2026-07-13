"""
Work Pool Submodule.

Manages parallel work distribution for parsing and scanning operations.
This is a black-box submodule — external code should only interact through
the pool facades (ParseWorkPool, ScanWorkPool).
"""

from src.parsing.gem5.impl.pool.parse_work import ParseWork
from src.parsing.gem5.impl.pool.pool import ParseWorkPool, ScanWorkPool

__all__ = ["ParseWork", "ParseWorkPool", "ScanWorkPool"]
