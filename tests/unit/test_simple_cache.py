"""Tests for SimpleCache thread safety and correctness."""

import threading
import time

import pandas as pd

from src.core.performance import SimpleCache, compute_data_fingerprint


class TestComputeDataFingerprint:
    # [test->req~ring5.quality.bounded-caching~1]

    """The fingerprint must reflect a change in *any* row, not just the first few."""

    def test_late_row_change_changes_fingerprint(self):
        # Identical shape and identical first rows; differ only in the last row.
        df1 = pd.DataFrame({"v": [1.0, 1.0, 1.0, 1.0]})
        df2 = pd.DataFrame({"v": [1.0, 1.0, 1.0, 9.0]})
        fp1 = compute_data_fingerprint(df1, {}, ["v"])
        fp2 = compute_data_fingerprint(df2, {}, ["v"])
        assert fp1 != fp2  # a head(2) sample would have collided here

    def test_identical_data_same_fingerprint(self):
        df = pd.DataFrame({"v": [1.0, 2.0, 3.0]})
        assert compute_data_fingerprint(df, {}, ["v"]) == compute_data_fingerprint(
            df.copy(), {}, ["v"]
        )


class TestBasicOperations:
    """Tests for basic cache operations without concurrency."""

    # [test->req~ring5.quality.bounded-caching~1]

    def test_basic_get_set(self):
        """Cache should store and retrieve values correctly."""
        cache = SimpleCache(maxsize=10)

        cache.set("key1", "value1")
        cache.set("key2", 42)
        cache.set("key3", [1, 2, 3])

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == 42
        assert cache.get("key3") == [1, 2, 3]

    def test_get_nonexistent_key(self):
        """Cache should return None for keys that were never set."""
        cache = SimpleCache(maxsize=10)

        assert cache.get("missing") is None
        assert cache.get("") is None
        assert cache.get("also_missing") is None

    def test_set_overwrites_existing(self):
        """Setting a key that already exists should overwrite the old value."""
        cache = SimpleCache(maxsize=10)

        cache.set("key", "original")
        assert cache.get("key") == "original"

        cache.set("key", "updated")
        assert cache.get("key") == "updated"

        cache.set("key", None)
        # Note: get returns None for missing keys, but here None is the stored value.
        # The cache stores (value, timestamp) so get() returns value which is None.
        # This is indistinguishable from a cache miss at the API level.
        result = cache.get("key")
        assert result is None

    def test_ttl_expiration(self):
        """Values should expire after the TTL elapses."""
        from unittest.mock import patch

        cache = SimpleCache(maxsize=10, ttl=0.05)

        with patch("src.core.performance.time") as mock_time:
            mock_time.time.return_value = 1000.0
            cache.set("ephemeral", "data")

            # Still within TTL
            mock_time.time.return_value = 1000.01
            assert cache.get("ephemeral") == "data"

            # Past TTL (0.05 seconds later)
            mock_time.time.return_value = 1000.1
            assert cache.get("ephemeral") is None

    def test_ttl_not_yet_expired(self):
        """Values should remain available before the TTL elapses."""
        from unittest.mock import patch

        cache = SimpleCache(maxsize=10, ttl=1.0)

        with patch("src.core.performance.time") as mock_time:
            mock_time.time.return_value = 1000.0
            cache.set("persistent", "data")

            # Well within TTL window
            mock_time.time.return_value = 1000.005
            assert cache.get("persistent") == "data"

    def test_lru_eviction(self):
        """When cache is full, the entry with the oldest timestamp should be evicted."""
        cache = SimpleCache(maxsize=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        # Cache is now full. Adding a fourth entry should evict "a" (oldest).
        cache.set("d", 4)

        assert cache.get("a") is None, "Oldest entry 'a' should have been evicted"
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_lru_eviction_respects_insertion_order(self):
        """Eviction should remove the entry with the earliest timestamp."""
        from unittest.mock import patch

        cache = SimpleCache(maxsize=2)

        with patch("src.core.performance.time") as mock_time:
            mock_time.time.return_value = 1000.0
            cache.set("first", 1)

            mock_time.time.return_value = 1001.0
            cache.set("second", 2)

            # This triggers eviction of "first" (oldest timestamp)
            mock_time.time.return_value = 1002.0
            cache.set("third", 3)

        assert cache.get("first") is None
        assert cache.get("second") == 2
        assert cache.get("third") == 3

    def test_lru_eviction_promotes_on_access(self):
        """get() marks an entry most-recently-used so it survives eviction (true LRU)."""
        cache = SimpleCache(maxsize=2)
        cache.set("a", 1)
        cache.set("b", 2)

        # Access "a" so it becomes the most-recently-used entry.
        assert cache.get("a") == 1

        # Inserting "c" must now evict the least-recently-used "b", not "a".
        cache.set("c", 3)
        assert cache.get("a") == 1, "recently-accessed 'a' must survive eviction"
        assert cache.get("b") is None, "least-recently-used 'b' should be evicted"
        assert cache.get("c") == 3

    def test_stats_counters(self):
        """Stats should accurately track hits, misses, size, and hit rate."""
        cache = SimpleCache(maxsize=10)

        # Initial stats: everything at zero
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0
        assert stats["hit_rate"] == 0

        # One miss (key not found)
        cache.get("missing_key")
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0

        # Set and then hit
        cache.set("key", "value")
        cache.get("key")  # hit
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 50.0

        # Two more hits
        cache.get("key")
        cache.get("key")
        stats = cache.stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 75.0

    def test_stats_after_clear(self):
        """Clear should reset all counters and remove all entries."""
        cache = SimpleCache(maxsize=10)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")  # hit
        cache.get("missing")  # miss

        cache.clear()

        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0
        assert stats["hit_rate"] == 0

        # Previously stored keys should be gone
        assert cache.get("a") is None
        assert cache.get("b") is None


class TestConcurrency:
    # [test->req~ring5.quality.bounded-caching~1]

    """Tests for thread safety under concurrent access."""

    def test_concurrent_get_set(self):
        """Multiple threads performing get/set simultaneously should not corrupt state."""
        cache = SimpleCache(maxsize=256)
        num_threads = 10
        ops_per_thread = 200
        barrier = threading.Barrier(num_threads)
        errors: list[Exception] = []

        def worker(thread_id: int) -> None:
            try:
                barrier.wait(timeout=5)
                for i in range(ops_per_thread):
                    key = f"t{thread_id}_k{i}"
                    value = f"t{thread_id}_v{i}"
                    cache.set(key, value)
                    # Read back the key we just wrote. Due to eviction from
                    # other threads, the value might be gone, but we should
                    # never see corrupted data.
                    result = cache.get(key)
                    if result is not None and result != value:
                        raise AssertionError(
                            f"Thread {thread_id}: expected {value!r}, got {result!r}"
                        )
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"

        # Cache should be in a consistent state
        stats = cache.stats()
        assert stats["size"] <= cache._maxsize
        assert stats["hits"] >= 0
        assert stats["misses"] >= 0

    def test_concurrent_set_with_eviction(self):
        """Concurrent sets that trigger evictions should not crash or corrupt."""
        cache = SimpleCache(maxsize=5)  # Tiny cache forces frequent evictions
        num_threads = 10
        ops_per_thread = 100
        barrier = threading.Barrier(num_threads)
        errors: list[Exception] = []

        def worker(thread_id: int) -> None:
            try:
                barrier.wait(timeout=5)
                for i in range(ops_per_thread):
                    cache.set(f"t{thread_id}_k{i}", i)
                    cache.get(f"t{thread_id}_k{i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"

        # Size must never exceed maxsize
        stats = cache.stats()
        assert stats["size"] <= 5

    def test_clear_under_concurrency(self):
        """Clearing the cache while other threads read/write should not crash."""
        cache = SimpleCache(maxsize=64)
        num_workers = 8
        ops_per_worker = 100
        barrier = threading.Barrier(num_workers + 1)  # +1 for the clear-thread
        errors: list[Exception] = []
        stop_event = threading.Event()

        def read_write_worker(thread_id: int) -> None:
            try:
                barrier.wait(timeout=5)
                for i in range(ops_per_worker):
                    if stop_event.is_set():
                        break
                    cache.set(f"w{thread_id}_k{i}", i)
                    cache.get(f"w{thread_id}_k{i}")
                    # Also read keys from other threads (may or may not exist)
                    cache.get(f"w{(thread_id + 1) % num_workers}_k{i}")
            except Exception as exc:
                errors.append(exc)

        def clear_worker() -> None:
            try:
                barrier.wait(timeout=5)
                for _ in range(20):
                    time.sleep(0.002)
                    cache.clear()
                stop_event.set()
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=read_write_worker, args=(tid,)) for tid in range(num_workers)
        ]
        threads.append(threading.Thread(target=clear_worker))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"

        # After everything settles, cache should be in a valid state
        stats = cache.stats()
        assert stats["size"] <= cache._maxsize
        assert stats["size"] >= 0

    def test_concurrent_stats(self):
        """Reading stats while other threads mutate the cache should not crash."""
        cache = SimpleCache(maxsize=32)
        num_threads = 6
        ops_per_thread = 200
        barrier = threading.Barrier(num_threads + 1)  # +1 for stats reader
        errors: list[Exception] = []

        def mutator(thread_id: int) -> None:
            try:
                barrier.wait(timeout=5)
                for i in range(ops_per_thread):
                    cache.set(f"t{thread_id}_{i}", i)
                    cache.get(f"t{thread_id}_{i}")
            except Exception as exc:
                errors.append(exc)

        def stats_reader() -> None:
            try:
                barrier.wait(timeout=5)
                for _ in range(ops_per_thread):
                    s = cache.stats()
                    # All stat values must be non-negative
                    assert s["hits"] >= 0
                    assert s["misses"] >= 0
                    assert s["size"] >= 0
                    assert 0 <= s["hit_rate"] <= 100
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=mutator, args=(tid,)) for tid in range(num_threads)]
        threads.append(threading.Thread(target=stats_reader))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"

    def test_concurrent_ttl_expiration(self):
        """Entries expiring under concurrent access should not cause errors."""
        cache = SimpleCache(maxsize=64, ttl=0.03)
        num_threads = 6
        barrier = threading.Barrier(num_threads)
        errors: list[Exception] = []

        def worker(thread_id: int) -> None:
            try:
                barrier.wait(timeout=5)
                for i in range(50):
                    key = f"t{thread_id}_k{i}"
                    cache.set(key, i)
                    time.sleep(0.002)
                    # Value may or may not have expired; either outcome is fine
                    result = cache.get(key)
                    if result is not None and result != i:
                        raise AssertionError(f"Thread {thread_id}: expected {i}, got {result}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"
