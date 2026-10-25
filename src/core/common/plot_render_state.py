"""Exact-generation ownership for a plot's opaque render binding."""

from _thread import LockType
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Self


@dataclass(frozen=True, eq=False, slots=True)
class PlotRenderBinding[T]:
    """Pair one native-agnostic payload with its exact retirement callback."""

    payload: T
    _retire: Callable[[], None] = field(repr=False)
    detached_payload: T | None = field(default=None, repr=False)
    _lock: LockType = field(default_factory=Lock, init=False, repr=False)
    _retired: bool = field(default=False, init=False, repr=False)

    def dispose(self) -> None:
        """Run this generation's cleanup once, outside its ownership lock."""
        with self._lock:
            if self._retired:
                return
            object.__setattr__(self, "_retired", True)
        self._retire()


@dataclass(frozen=True, slots=True)
class _DetachedPayload[T]:
    payload: T | None


class PlotRenderState[T]:
    """Own either one bound generation or its detached domain payload."""

    def __init__(self, payload: T | None = None) -> None:
        self._lock = Lock()
        self._state: PlotRenderBinding[T] | _DetachedPayload[T] = _DetachedPayload(payload)

    def snapshot(self) -> PlotRenderBinding[T] | None:
        """Return the current generation token without transferring ownership."""
        with self._lock:
            state = self._state
            return state if isinstance(state, PlotRenderBinding) else None

    def current_payload(self) -> T | None:
        """Return the opaque bound or detached value without copying under its lock."""
        with self._lock:
            return self._state.payload

    def set_detached_payload(self, payload: T) -> PlotRenderBinding[T] | None:
        """Replace domain state and return any prior binding for deferred disposal."""
        replacement = _DetachedPayload(payload)
        with self._lock:
            previous, self._state = self._state, replacement
        return previous if isinstance(previous, PlotRenderBinding) else None

    def publish(
        self,
        payload: T,
        retire: Callable[[], None],
        *,
        detached_payload: T | None = None,
    ) -> PlotRenderBinding[T] | None:
        """Publish a complete generation and return the previous binding for disposal."""
        replacement = PlotRenderBinding(payload, retire, detached_payload)
        with self._lock:
            previous, self._state = self._state, replacement
        return previous if isinstance(previous, PlotRenderBinding) else None

    def detach(self, expected: PlotRenderBinding[T] | None) -> PlotRenderBinding[T] | None:
        """Detach only the captured generation, preserving newer bound or domain state."""
        with self._lock:
            state = self._state
            if not isinstance(state, PlotRenderBinding) or state is not expected:
                return None
            self._state = _DetachedPayload(state.detached_payload)
        return state

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        """Copy detached domain state outside locks; live native payloads cannot be cloned."""
        with self._lock:
            state = self._state
            if isinstance(state, PlotRenderBinding):
                raise TypeError("Detach plot render state before copying a plot.")
            payload = state.payload
        result = type(self)()
        memo[id(self)] = result
        if payload is not None:
            result.set_detached_payload(deepcopy(payload, memo))
        return result
