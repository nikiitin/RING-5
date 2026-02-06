"""
Compliance test for TDD Chapter 4 rules.
Demonstrates: Separation of Testing Buckets (Commit vs Nightly vs Benchmark) behavior pattern.
"""

import time

import pytest

# --- Logic ---


def heavy_computation() -> int:
    """Simulates a heavy E2E task (e.g., real network/DB)."""
    time.sleep(0.1)  # Simulate delay
    return 42


def light_computation() -> int:
    """Simulates a fast unit task."""
    return 42


# --- Tests ---


@pytest.mark.benchmark
def test_performance_benchmark() -> None:
    """
    Performance Test (Ch 4).
    Should reside in /benchmarks, but demonstrated here with marker.
    NEVER mix with functional tests without markers.
    """
    start = time.time()
    result = heavy_computation()
    end = time.time()
    assert result == 42
    assert (end - start) >= 0.1


@pytest.mark.smoke
def test_functional_fake() -> None:
    """
    Commit Suite Test (Ch 4).
    Uses 'Fast/Fake' Logic. Runs in milliseconds.
    """
    result = light_computation()
    assert result == 42


@pytest.mark.slow
def test_e2e_real() -> None:
    """
    Nightly Suite Test (Ch 4).
    Uses 'Real/Slow' Logic.
    """
    # In a real app, this would hit the DB/Network
    result = heavy_computation()
    assert result == 42
