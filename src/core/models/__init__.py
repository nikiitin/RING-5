"""
RING-5 Core Models — Shared data models for cross-layer communication.

These frozen dataclasses form the "common language" between the parsing,
application-API, and presentation layers. They are intentionally kept
outside any single layer so that every module can depend on them
without introducing circular or upward imports.

Public API:
    - ScannedVariable: Metadata for a variable discovered in a stats file
    - StatConfig:      Configuration for a specific statistic extraction
"""

from src.core.models.parsing_models import ScannedVariable, StatConfig

__all__ = ["ScannedVariable", "StatConfig"]
