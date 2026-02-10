"""
Stat Types Registry and Base Class

This module provides a self-registering type system for gem5 statistics.
Types register themselves using the @register_type decorator.
"""

from typing import Any, Dict, List, Optional, Type


class StatTypeRegistry:
    """Registry for stat type classes. Types self-register via decorator."""

    _types: Dict[str, Type["StatType"]] = {}

    @classmethod
    def register(cls, type_name: str) -> Any:
        """Decorator to register a stat type class."""

        def decorator(klass: Type["StatType"]) -> Type["StatType"]:
            cls._types[type_name] = klass
            klass._type_name = type_name
            return klass

        return decorator

    @classmethod
    def create(cls, type_name: str, repeat: int = 1, **kwargs: Any) -> "StatType":
        """Create a stat type instance by name."""
        if type_name not in cls._types:
            available = ", ".join(cls._types.keys())
            raise ValueError(f"Unknown stat type: '{type_name}'. Available: {available}")
        return cls._types[type_name](repeat=repeat, **kwargs)

    @classmethod
    def get_types(cls) -> List[str]:
        """Get list of registered type names."""
        return list(cls._types.keys())


# Convenience alias
register_type = StatTypeRegistry.register


class StatType:
    """
    Base class for all gem5 stat types.

    Provides common functionality for content storage, balancing, and reduction.

    IMPORTANT: This base class enforces critical safety invariants:
    - reducedContent can ONLY be accessed after balance_content() AND reduce_duplicates()
    - Subclasses should override _set_content() to validate incoming data
    - All types protect against invalid attribute access
    """

    _type_name: str = "base"
    required_params: List[str] = []
    # Valid attributes that can be set on type instances
    _allowed_attributes = frozenset(
        {
            "_repeat",
            "_content",
            "_reduced_content",
            "_balanced",
            "_reduced",
        }
    )

    def __init__(self, repeat: int = 1, **kwargs: Any) -> None:
        # Use object.__setattr__ to bypass our protective __setattr__
        object.__setattr__(self, "_repeat", int(repeat))
        object.__setattr__(self, "_content", [])
        object.__setattr__(self, "_reduced_content", None)
        object.__setattr__(self, "_balanced", False)
        object.__setattr__(self, "_reduced", False)

    def __setattr__(self, name: str, value: Any) -> None:
        """Protect against setting invalid attributes."""
        # Allow 'content' to go through property setter on subclass
        if name == "content":
            # Find and call the property setter on the actual class
            # This properly invokes subclass custom setters
            prop = type(self).__dict__.get("content")
            if prop is not None and hasattr(prop, "fset") and prop.fset is not None:
                prop.fset(self, value)
            else:
                # Fallback for base class behavior
                self._validate_content(value)
                self._set_content(value)
        elif name in self._allowed_attributes or name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            raise AttributeError(
                f"{self._type_name.upper()}: Cannot set attribute '{name}'. "
                f"Only content assignment via .content property is allowed."
            )

    def __getattribute__(self, name: str) -> Any:
        """Guard access to reduced_content - only valid after reduction."""
        if name == "reduced_content":
            balanced = object.__getattribute__(self, "_balanced")
            reduced = object.__getattribute__(self, "_reduced")
            if not balanced or not reduced:
                raise AttributeError(
                    f"{object.__getattribute__(self, '_type_name').upper()}: "
                    f"Cannot access reduced_content before calling balance_content() "
                    f"AND reduce_duplicates()"
                )
        return object.__getattribute__(self, name)

    @property
    def repeat(self) -> int:
        return int(object.__getattribute__(self, "_repeat"))

    @property
    def content(self) -> Any:
        content = object.__getattribute__(self, "_content")
        if content is None:
            raise AttributeError(f"{self._type_name.upper()}: Content not initialized")
        return content

    @content.setter
    def content(self, value: Any) -> None:
        self._validate_content(value)
        self._set_content(value)

    @property
    def reduced_content(self) -> Any:
        # Guard is in __getattribute__
        return object.__getattribute__(self, "_reduced_content")

    def _validate_content(self, value: Any) -> None:
        """Override to validate content before setting. Raise TypeError on invalid."""
        pass

    def _set_content(self, value: Any) -> None:
        """Override to customize how content is stored."""
        content_list: List[Any] = self._content
        content_list.append(value)

    def balance_content(self) -> None:
        """Ensure content has exactly `repeat` entries, padding with zeros if needed."""
        object.__setattr__(self, "_balanced", True)
        content_list: List[Any] = self._content
        content_len: int = len(content_list)
        repeat: int = self._repeat

        if content_len < repeat:
            padding: int = repeat - content_len
            content_list.extend([0] * padding)
        elif content_len > repeat:
            raise RuntimeError(
                f"{self._type_name.upper()}: More values ({content_len}) than "
                f"expected ({repeat}). Values: {content_list}"
            )

    def reduce_duplicates(self) -> None:
        """Reduce content to single value via arithmetic mean."""
        object.__setattr__(self, "_reduced", True)

        if not self._content:
            object.__setattr__(self, "_reduced_content", "NA")
            return

        try:
            total = sum(self._content)
            object.__setattr__(self, "_reduced_content", total / self._repeat)
        except (TypeError, ValueError):
            # Non-numeric content - use first value
            object.__setattr__(
                self, "_reduced_content", self._content[0] if self._content else "NA"
            )

    @property
    def entries(self) -> Optional[List[str]]:
        """
        Return entry keys for complex types (Vector, Distribution).
        Returns None for Scalar and Configuration types.
        """
        return None

    def __str__(self) -> str:
        return f"{self._type_name}({self._content})"

    def __repr__(self) -> str:
        return self.__str__()
