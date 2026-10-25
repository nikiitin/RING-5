"""Exact-generation ownership for a plot's opaque render binding."""

from _thread import LockType
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Self


@dataclass(frozen=True, eq=False, slots=True)
class PlotRenderBinding[T]:
    """Pair one native-agnostic payload with its exact retirement callback."""

    payload: T
    _retire: Callable[[], None] = field(repr=False)
    _lock: LockType = field(default_factory=Lock, init=False, repr=False)
    _retired: bool = field(default=False, init=False, repr=False)

    def dispose(self) -> None:
        """Run this generation's cleanup once, outside its ownership lock."""
        with self._lock:
            if self._retired:
                return
            object.__setattr__(self, "_retired", True)
        self._retire()


class PlotRenderState[T]:
    """Own one plot binding without invoking callbacks while its lock is held."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._binding: PlotRenderBinding[T] | None = None

    def snapshot(self) -> PlotRenderBinding[T] | None:
        """Return the current generation token without transferring ownership."""
        with self._lock:
            return self._binding

    def publish(self, payload: T, retire: Callable[[], None]) -> PlotRenderBinding[T] | None:
        """Publish a new generation and return the previous binding for disposal."""
        replacement = PlotRenderBinding(payload, retire)
        with self._lock:
            previous, self._binding = self._binding, replacement
        return previous

    def detach(self, expected: PlotRenderBinding[T] | None) -> PlotRenderBinding[T] | None:
        """Detach only the captured generation, preserving any newer publication."""
        with self._lock:
            if self._binding is not expected:
                return None
            self._binding = None
        return expected

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        """Copy only an empty detached owner; live native payloads cannot be cloned."""
        with self._lock:
            if self._binding is not None:
                raise TypeError("Detach plot render state before copying a plot.")
        result = type(self)()
        memo[id(self)] = result
        return result
