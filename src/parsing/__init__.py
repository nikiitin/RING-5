"""
RING-5 Parsing Module — Interface Layer.

Provides the public API for the gem5 parsing subsystem.
The canonical implementations live in the ``gem5/impl/`` subpackage;
this ``__init__`` re-exports them under their legacy names so that
existing consumers continue to work.

Public API:
    - ParseService   (alias for ``Gem5Parser``)
    - ScannerService  (alias for ``Gem5Scanner``)

Implementation:
    - gem5/:  gem5-specific types, Perl scripts, and ``impl/``

Backward Compatibility:
    ``parse_service.py`` and ``scanner_service.py`` are thin re-export
    shims kept for test-patch compatibility.  New code should import
    from this package directly.
"""

# Backward-compatible re-exports for existing consumers.
# The canonical classes are now Gem5Parser and Gem5Scanner inside gem5/impl/.
from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService
from src.parsing.gem5.impl.gem5_scanner import Gem5Scanner as ScannerService

__all__ = ["ParseService", "ScannerService"]
