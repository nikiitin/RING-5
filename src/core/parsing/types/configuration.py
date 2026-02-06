"""Configuration stat type for metadata values."""

from typing import Any, Optional

from src.core.parsing.types.base import StatType, register_type


@register_type("configuration")
class Configuration(StatType):
    """
    Represents configuration/metadata values (e.g., benchmark name, seed).

    Stores string values; uses onEmpty default if content is empty.

    Validation:
    - Values must be convertible to strings
    - onEmpty provides fallback for empty content
    - No balancing needed (always balanced)
    - Reduction returns first value or onEmpty
    """

    required_params = ["onEmpty"]
    _allowed_attributes = frozenset(
        {
            "_repeat",
            "_content",
            "_reduced_content",
            "_balanced",
            "_reduced",
            "_on_empty",
            "balancedContent",
            "reducedDuplicates",
            "reducedContent",
        }
    )

    def __init__(self, repeat: int = 1, onEmpty: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(repeat, **kwargs)
        object.__setattr__(self, "_on_empty", onEmpty or "None")

    @property
    def onEmpty(self) -> str:
        return str(object.__getattribute__(self, "_on_empty"))

    def _validate_content(self, value: Any) -> None:
        """Ensure value can be converted to string."""
        try:
            str(value)
        except Exception as e:
            raise TypeError(
                f"CONFIGURATION: Variable non-convertible to string. "
                f"Value: {value}, Type: {type(value).__name__}"
            ) from e

    def _set_content(self, value: Any) -> None:
        """Store as string."""
        self._content.append(str(value))

    def balance_content(self) -> None:
        """Configuration is always balanced (no padding needed)."""
        object.__setattr__(self, "_balanced", True)
        # Always balanced - no action needed

    def reduce_duplicates(self) -> None:
        """For configuration, return first value or onEmpty default."""
        object.__setattr__(self, "_reduced", True)

        if not self._content:
            object.__setattr__(self, "_reduced_content", self._on_empty)
        else:
            object.__setattr__(self, "_reduced_content", self._content[0])

    def __str__(self) -> str:
        return f"Configuration({self._content}, onEmpty={self._on_empty})"
