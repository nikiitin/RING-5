"""
Backward-compatibility shim for ScannerService.

The canonical implementation is ``Gem5Scanner`` in
``src.parsing.gem5.impl.gem5_scanner``.  This module re-exports
the class (aliased as *ScannerService*) so that existing test-suites
that import from this module path continue to work.

New code should import from the canonical location or from
``src.parsing`` (which re-exports ``ScannerService`` via
``__init__.py``).
"""

from src.parsing.gem5.impl.gem5_scanner import Gem5Scanner as ScannerService

__all__ = ["ScannerService"]
