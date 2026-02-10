"""
Compliance test for TDD Chapter 10 rules.
Demonstrates: Property-Based Testing (Hypothesis) and Invariant checking.
"""

import base64
from typing import List

from hypothesis import given
from hypothesis import strategies as st

# --- Logic to Test ---


def encode(s: str) -> str:
    """Encodes string to base64."""
    return base64.b64encode(s.encode("utf-8")).decode("utf-8")


def decode(s: str) -> str:
    """Decodes base64 to string."""
    return base64.b64decode(s.encode("utf-8")).decode("utf-8")


def my_sort(items: List[int]) -> List[int]:
    """Standard sort."""
    return sorted(items)


# --- Tests ---


@given(st.text())
def test_round_trip_invariant(s: str) -> None:
    """
    Demonstrates Round-Trip Property (Ch 10).
    f^-1(f(x)) == x
    """
    assert decode(encode(s)) == s


@given(st.lists(st.integers()))
def test_idempotence_invariant(items: List[int]) -> None:
    """
    Demonstrates Idempotence Property (Ch 10).
    f(f(x)) == f(x)
    Sorting an already sorted list should not change it.
    """
    sorted_once = my_sort(items)
    sorted_twice = my_sort(sorted_once)
    assert sorted_once == sorted_twice
