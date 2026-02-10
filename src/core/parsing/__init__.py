"""
RING-5 Parsing Module — Interface Layer.

Provides simulator-agnostic protocols and a factory for creating
parser API instances. The gem5 implementation lives in the gem5/ submodule.

Public API:
    - parser_protocol.py:   ParserProtocol (parsing contract)
    - scanner_protocol.py:  ScannerProtocol (scanning contract)
    - parser_api.py:        ParserAPI (unified facade contract)
    - factory.py:           ParserAPIFactory.create("gem5")

Data Models:
    ScannedVariable and StatConfig now live in ``src.core.models`` so they
    can be shared across all layers (parsing, application API, UI) without
    circular imports. A backward-compat shim remains in ``models.py``.

Implementation:
    - gem5/:                gem5-specific types, perl scripts, and impl/

Backward Compatibility:
    ParseService and ScannerService are re-exported from their new locations
    (Gem5Parser and Gem5Scanner) to support existing consumers.
"""

# Backward-compatible re-exports for existing consumers.
# The canonical classes are now Gem5Parser and Gem5Scanner inside gem5/impl/.
from src.core.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService
from src.core.parsing.gem5.impl.gem5_scanner import Gem5Scanner as ScannerService

__all__ = ["ParseService", "ScannerService"]
