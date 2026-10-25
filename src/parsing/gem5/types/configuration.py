"""Configuration stat type for metadata values."""

from typing import Any, override

from src.core.models.parsing_models import StatParamValue
from src.parsing.gem5.types.base import StatType, register_type


@register_type("configuration")
class Configuration(StatType):
    """
    Represents configuration/metadata values (e.g., benchmark name, seed).

    Stores string values; uses on_empty default if content is empty.

    Validation:
    - Values must be convertible to strings
    - on_empty provides fallback for empty content
    - No balancing needed (always balanced)
    - Reduction returns first value or on_empty
    """

    # [impl->req~ring5.ingestion.configuration-fallbacks~1]
    # [impl->req~ring5.ingestion.configuration~1]

    required_params = ["on_empty"]
    _allowed_attributes = frozenset(
        {
            "_repeat",
            "_content",
            "_reduced_content",
            "_balanced",
            "_reduced",
            "_on_empty",
        }
    )

    def __init__(
        self, repeat: int = 1, on_empty: str | None = None, **kwargs: StatParamValue
    ) -> None:
        if kwargs:
            raise TypeError(f"Unsupported configuration options: {sorted(kwargs)}")
        super().__init__(repeat)
        object.__setattr__(self, "_on_empty", on_empty or "None")

    @property
    def on_empty(self) -> str:
        """Return the value used when configuration content is empty."""
        return str(object.__getattribute__(self, "_on_empty"))

    @override
    def _validate_content(self, value: Any) -> None:
        """Ensure value can be converted to string."""
        try:
            str(value)
        except Exception as e:
            raise TypeError(
                f"CONFIGURATION: Variable non-convertible to string. "
                f"Value: {value}, Type: {type(value).__name__}"
            ) from e

    @override
    def _set_content(self, value: Any) -> None:
        """Store as string."""
        self._content.append(str(value))

    @override
    def balance_content(self) -> None:
        """Configuration is always balanced (no padding needed)."""
        object.__setattr__(self, "_balanced", True)

    @override
    def reduce_duplicates(self) -> None:
        """For configuration, return first value or on_empty default."""
        object.__setattr__(self, "_reduced", True)

        if not self._content:
            object.__setattr__(self, "_reduced_content", self._on_empty)
        else:
            object.__setattr__(self, "_reduced_content", self._content[0])

    def __str__(self) -> str:
        return f"Configuration({self._content}, on_empty={self._on_empty})"
