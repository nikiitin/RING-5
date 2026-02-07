"""
Data models for the Parser layer.
Enforces strict typing and immutability.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, cast


@dataclass(frozen=True)
class ScannedVariable:
    """
    Metadata for a variable discovered in a gem5 stats file.
    Output of Layer A (Ingestion).
    """

    name: str
    type: str  # "scalar", "vector", "distribution", "histogram", "configuration"
    entries: List[str] = field(default_factory=list)
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    pattern_indices: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Legacy compatibility for dictionary-based components."""
        result: Dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "entries": self.entries,
        }
        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        if self.pattern_indices is not None:
            result["pattern_indices"] = self.pattern_indices
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScannedVariable":
        """Reconstruct model from dictionary."""
        return cls(
            name=data["name"],
            type=data["type"],
            entries=data.get("entries", []),
            minimum=data.get("minimum"),
            maximum=data.get("maximum"),
            pattern_indices=data.get("pattern_indices"),
        )

    def __getitem__(self, key: str) -> Any:
        """Allow subscript access for legacy compatibility."""
        if not isinstance(key, str):
            raise TypeError(f"attribute name must be string, not '{type(key).__name__}'")

        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"'{key}' not found in ScannedVariable")

    def get(self, key: str, default: Any = None) -> Any:
        """Mimic dict.get() for compatibility."""
        if hasattr(self, key):
            return getattr(self, key)
        return default

    def __contains__(self, key: str) -> bool:
        """Allow 'in' operator to check for attributes."""
        return hasattr(self, key)


@dataclass(frozen=True)
class StatConfig:
    """
    Configuration for a specific statistic extraction.
    Input to the FileParserStrategy implementations.
    """

    name: str
    type: str
    repeat: int = 1
    params: Dict[str, Any] = field(default_factory=dict)
    statistics_only: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for legacy component support."""
        return {
            "name": self.name,
            "type": self.type,
            "repeat": self.repeat,
            "statistics_only": self.statistics_only,
            **self.params,
        }

    # Typed views of params for specific types
    def get_entries(self) -> List[str]:
        return cast(List[str], self.params.get("entries", []))

    def get_bins(self) -> int:
        return cast(int, self.params.get("bins", 0))

    def get_max_range(self) -> float:
        return cast(float, self.params.get("max_range", 0.0))

    def __getitem__(self, key: str) -> Any:
        """Allow subscript access for legacy compatibility."""
        if not isinstance(key, str):
            raise TypeError(f"attribute name must be string, not '{type(key).__name__}'")

        if hasattr(self, key):
            return getattr(self, key)
        if key in self.params:
            return self.params[key]
        raise KeyError(f"'{key}' not found in StatConfig")

    def __contains__(self, key: str) -> bool:
        """Allow 'in' operator to check for attributes or params."""
        return hasattr(self, key) or key in self.params
