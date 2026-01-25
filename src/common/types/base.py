"""
Stat Types Registry and Base Class

This module provides a self-registering type system for gem5 statistics.
Types register themselves using the @register_type decorator.
"""

from typing import Any, Dict, List, Type


class StatTypeRegistry:
    """Registry for stat type classes. Types self-register via decorator."""

    _types: Dict[str, Type["StatType"]] = {}

    @classmethod
    def register(cls, type_name: str):
        """Decorator to register a stat type class."""

        def decorator(klass: Type["StatType"]) -> Type["StatType"]:
            cls._types[type_name] = klass
            klass._type_name = type_name
            return klass

        return decorator

    @classmethod
    def create(cls, type_name: str, repeat: int = 1, **kwargs) -> "StatType":
        """Create a stat type instance by name."""
        if type_name not in cls._types:
            available = ", ".join(cls._types.keys())
            raise ValueError(f"Unknown stat type: '{type_name}'. Available: {available}")
        return cls._types[type_name](repeat=repeat, **kwargs)

    @classmethod
    def get_types(cls) -> List[str]:
        """Get list of registered type names."""
        return list(cls._types.keys())

    @classmethod
    def get_required_params(cls, type_name: str) -> List[str]:
        """Get required parameters for a type."""
        if type_name not in cls._types:
            return []
        return getattr(cls._types[type_name], "required_params", [])


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
            "balancedContent",
            "reducedDuplicates",
            "reducedContent",
        }
    )

    def __init__(self, repeat: int = 1, **kwargs):
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
        """Guard access to reducedContent - only valid after reduction."""
        if name == "reducedContent" or name == "reduced_content":
            balanced = object.__getattribute__(self, "_balanced")
            reduced = object.__getattribute__(self, "_reduced")
            if not balanced or not reduced:
                raise AttributeError(
                    f"{object.__getattribute__(self, '_type_name').upper()}: "
                    f"Cannot access reducedContent before calling balance_content() "
                    f"AND reduce_duplicates()"
                )
        return object.__getattribute__(self, name)

    @property
    def repeat(self) -> int:
        return object.__getattribute__(self, "_repeat")

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

    # Backward compatibility alias
    @property
    def reducedContent(self) -> Any:
        return self.reduced_content

    def _validate_content(self, value: Any) -> None:
        """Override to validate content before setting. Raise TypeError on invalid."""
        pass

    def _set_content(self, value: Any) -> None:
        """Override to customize how content is stored."""
        self._content.append(value)

    def balance_content(self) -> None:
        """Ensure content has exactly `repeat` entries, padding with zeros if needed."""
        object.__setattr__(self, "_balanced", True)
        content_len = len(self._content)
        repeat = self._repeat

        if content_len < repeat:
            padding = repeat - content_len
            self._content.extend([0] * padding)
        elif content_len > repeat:
            raise RuntimeError(
                f"{self._type_name.upper()}: More values ({content_len}) than "
                f"expected ({repeat}). Values: {self._content}"
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

    # Backward compatibility aliases
    def balanceContent(self) -> None:
        self.balance_content()

    def reduceDuplicates(self) -> None:
        self.reduce_duplicates()

    @property
    def entries(self) -> List[str]:
        """Override in Vector/Distribution to return entry keys."""
        raise NotImplementedError(f"{self._type_name} does not have entries")

    def __str__(self) -> str:
        return f"{self._type_name}({self._content})"

    def __repr__(self) -> str:
        return self.__str__()
