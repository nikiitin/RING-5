"""
Backward-compatibility re-exports.

The canonical definitions of ScannedVariable and StatConfig now live in
``src.core.models.parsing_models``. This shim ensures that existing imports
of the form ``from src.core.parsing.models import ...`` continue to work.
"""

from src.core.models.parsing_models import ScannedVariable, StatConfig

__all__ = ["ScannedVariable", "StatConfig"]
