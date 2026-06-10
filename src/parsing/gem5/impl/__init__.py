"""
gem5 Implementation Details.

Contains ``Gem5Parser`` — the gem5 backend (parse + scan + CSV) implementing the
``SimulationParser`` protocol — and internal submodules for pools, strategies,
and scanning.
"""

from src.parsing.gem5.impl.gem5_parser import Gem5Parser

__all__ = ["Gem5Parser"]
