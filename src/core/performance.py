"""
Performance utilities for RING-5.

Provides caching, profiling, and optimization helpers to improve
application performance.
"""

import functools
import hashlib
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, TypeVar, cast

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


# Global cache instance for plot figure generation
_plot_cache = SimpleCache(maxsize=32, ttl=300)  # 5 min TTL


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


def get_plot_cache() -> SimpleCache:
    """Get global plot cache instance."""
    return _plot_cache


def clear_all_caches() -> None:
    """Clear all global caches."""
    _plot_cache.clear()
    logger.info("All caches cleared")


def get_cache_stats() -> dict[str, Any]:
    """Get statistics from all caches."""
    return {
        "plot_cache": _plot_cache.stats(),
    }


def compute_data_fingerprint(
    data: pd.DataFrame,
    params: dict[str, Any],
    relevant_cols: list[str],
) -> str:
    """Compute an MD5 fingerprint for DataFrame+params cache keying.

    Used by cached shapers (mean, normalize) to detect whether the
    input data and configuration have changed since the last run,
    avoiding expensive recalculation when the fingerprint matches.

    Args:
        data: Input DataFrame.
        params: Shaper configuration parameters.
        relevant_cols: Column names relevant to the computation.

    Returns:
        16-char hex digest suitable as a cache key.
    """

    fingerprint_parts = [
        f"shape:{data.shape}",
        f"cols:{sorted(relevant_cols)}",
        f"params:{sorted(params.items())}",
    ]

    if len(data) > 0 and relevant_cols:
        existing = list(dict.fromkeys(c for c in relevant_cols if c in data.columns))
        if existing:
            # Hash the full content of the relevant columns (every row), so a
            # change in any row — not just the first few — busts the cache.
            row_hashes = pd.util.hash_pandas_object(data[existing], index=False)
            content_digest = hashlib.md5(
                row_hashes.to_numpy().tobytes(), usedforsecurity=False
            ).hexdigest()
            fingerprint_parts.append(f"content:{content_digest}")

    fingerprint = "|".join(fingerprint_parts)
    return hashlib.md5(fingerprint.encode(), usedforsecurity=False).hexdigest()[:16]
