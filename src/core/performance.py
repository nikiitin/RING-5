"""
Performance utilities for RING-5.

Provides caching, profiling, and optimization helpers to improve
application performance.
"""

import functools
import hashlib
import json
import logging
import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, TypeVar, cast

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar("T")


class SimpleCache:
    """
    Simple in-memory cache for expensive operations.

    Thread-safe cache with TTL support and LRU eviction.
    Optimized for Streamlit's execution model.
    """

    # [impl->req~ring5.quality.bounded-caching~1]

    def __init__(self, maxsize: int = 128, ttl: float | None = None):
        """
        Initialize cache.

        Args:
            maxsize: Maximum number of cached entries
            ttl: Time-to-live in seconds (None = no expiration)
        """
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._maxsize = maxsize
        self._ttl = ttl
        self._hits = 0
        self._misses = 0
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        """Get value from cache if not expired (marks the entry as recently used)."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, timestamp = self._cache[key]

            # Check TTL expiration
            if self._ttl and (time.time() - timestamp) > self._ttl:
                del self._cache[key]
                self._misses += 1
                return None

            self._cache.move_to_end(key)  # mark most-recently-used (true LRU)
            self._hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        """Set value in cache, evicting the least-recently-used entry at capacity."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self._maxsize:
                self._cache.popitem(last=False)  # evict least-recently-used

            self._cache[key] = (value, time.time())

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict[str, int | float]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            stats: dict[str, int | float] = {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._cache),
                "hit_rate": round(hit_rate, 2),
            }
            return stats


def cached(
    ttl: float | None = None,
    maxsize: int = 128,
    cache_instance: SimpleCache | None = None,
    key_func: Callable[..., str] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to cache function results with optional custom key generation.

    Args:
        ttl: Time-to-live in seconds
        maxsize: Maximum cache size
        cache_instance: Existing cache to use
        key_func: Optional function to generate cache key from args/kwargs.
                  If None, uses default stringification.
                  Signature: key_func(*args, **kwargs) -> str

    Example:
        # Simple caching (default key generation)
        @cached(ttl=60)
        def simple_operation(x: int) -> int:
            return x * 2

        # Custom key for DataFrame caching (avoid stringifying large data)
        @cached(ttl=300, key_func=lambda df, fingerprint: fingerprint)
        def dataframe_operation(data: pd.DataFrame, fingerprint: str) -> pd.DataFrame:
            # fingerprint is used as cache key, NOT the DataFrame
            return expensive_transform(data)
    """
    cache = cache_instance or SimpleCache(maxsize=maxsize, ttl=ttl)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key using custom function or default
            if key_func is not None:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: stringify all arguments (works for primitives)
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try cache first
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {func.__name__} (key={cache_key[:32]}...)")
                # Cache returns Any, but we trust it matches T
                return cast(T, cached_value)

            # Compute and cache
            logger.debug(f"Cache MISS: {func.__name__} (key={cache_key[:32]}...)")
            result: T = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result

        # Attach cache management methods (dynamic attributes)
        cast(Any, wrapper).cache = cache
        cast(Any, wrapper).cache_clear = cache.clear
        cast(Any, wrapper).cache_stats = cache.stats

        return wrapper

    return decorator


def timed(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to measure function execution time.

    Logs execution time at INFO level for performance monitoring.

    Example:
        @timed
        def slow_operation():
            # ... slow code
    """

    # [impl->req~ring5.quality.performance-regression-gates~1]

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000  # ms

        if elapsed > 100:  # Log slow operations (>100ms)
            logger.warning(f"SLOW: {func.__name__} took {elapsed:.2f}ms")
        else:
            logger.debug(f"PERF: {func.__name__} took {elapsed:.2f}ms")

        return result

    return wrapper


def _cache_identity(value: Any) -> Any:
    """Encode supported metadata without conflating Python or pandas types."""
    if value is None or type(value) in (str, bool, int):
        return [type(value).__name__, value]
    if type(value) is float:
        return ["float", value.hex()]
    if value is pd.NA:
        return ["pandas.NA"]
    if value is pd.NaT:
        return ["pandas.NaT"]
    if isinstance(value, np.generic):
        return ["numpy", str(value.dtype), _cache_identity(value.item())]
    if type(value) in (list, tuple):
        return [type(value).__name__, [_cache_identity(item) for item in value]]
    if type(value) is dict:
        items = [[_cache_identity(key), _cache_identity(item)] for key, item in value.items()]
        return ["dict", sorted(items, key=lambda item: json.dumps(item[0], sort_keys=True))]
    if isinstance(value, pd.CategoricalDtype):
        return ["categorical", _cache_identity(value.categories), value.ordered]
    if isinstance(value, pd.Index):
        dtype = (
            _cache_identity(value.dtype)
            if isinstance(value.dtype, pd.CategoricalDtype)
            else repr(value.dtype)
        )
        levels = (
            [_cache_identity(level) for level in value.levels]
            if isinstance(value, pd.MultiIndex)
            else None
        )
        return [
            type(value).__qualname__,
            dtype,
            _cache_identity(list(value.names)),
            _cache_identity(value.tolist()),
            levels,
        ]
    if isinstance(value, np.ndarray):
        return ["ndarray", str(value.dtype), value.shape, _cache_identity(value.tolist())]
    raise TypeError(f"Unsupported cache identity type: {type(value).__qualname__}")


def compute_data_fingerprint(
    data: pd.DataFrame,
    params: dict[str, Any],
    relevant_cols: list[str],
) -> str:
    """Identify all retained values, types, axes and metadata of a cached frame.

    Args:
        data: Complete input retained by the cached transformation.
        params: Shaper configuration.
        relevant_cols: Columns selected by the operation.

    Returns:
        A 16-character key; unsupported metadata deliberately bypasses reuse.
    """
    # [impl->req~ring5.quality.bounded-caching~1]
    try:
        metadata = _cache_identity(
            {
                "columns": data.columns,
                "index": data.index,
                "dtypes": [
                    dtype if isinstance(dtype, pd.CategoricalDtype) else repr(dtype)
                    for dtype in data.dtypes
                ],
                "attrs": data.attrs,
                "params": params,
                "selected": relevant_cols,
                "object_values": [
                    data.iloc[:, position].tolist()
                    for position, dtype in enumerate(data.dtypes)
                    if pd.api.types.is_object_dtype(dtype)
                ],
            }
        )
        content = pd.util.hash_pandas_object(data, index=True).to_numpy().tobytes()
        digest = hashlib.sha256(json.dumps(metadata, separators=(",", ":")).encode("utf-8"))
        digest.update(content)
        return digest.hexdigest()[:16]
    except (TypeError, ValueError):
        # An unsupported mutable object has no reliable canonical identity. Never
        # collapse it through stringification or reuse another frame's output.
        return uuid.uuid4().hex[:16]
