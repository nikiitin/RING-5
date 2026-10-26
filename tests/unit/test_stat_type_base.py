"""Typed accumulator extension registration and base lifecycle hooks."""

from typing import Any, cast

import pytest

from src.parsing.gem5.types.base import StatType, StatTypeRegistry, register_type
from src.parsing.gem5.types.scalar import Scalar


def test_unknown_registered_type_is_visible() -> None:
    with pytest.raises(ValueError, match="Unknown stat type"):
        StatTypeRegistry.create("definitely_not_a_real_type")


def test_builtin_registry_returns_typed_accumulator() -> None:
    assert {"scalar", "configuration", "vector", "distribution", "histogram"} <= set(
        StatTypeRegistry.get_types()
    )
    stat = StatTypeRegistry.create("scalar", repeat=2)
    assert isinstance(stat, Scalar)
    stat.add_observation(1.5)
    stat.add_observation(2.5)
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content == 2.0


def test_base_requires_explicit_storage_and_reduction_hooks() -> None:
    with pytest.raises(TypeError, match="abstract"):
        cast(Any, StatType)()


def test_registered_extension_keeps_constructor_and_template_lifecycle() -> None:
    @register_type("test_scaled_point")
    class ScaledPoint(Scalar):
        __slots__ = ("_scale",)

        def __init__(self, repeat: int = 1, scale: float = 1.0) -> None:
            super().__init__(repeat)
            self._scale = scale

        def _reduce(self) -> float:
            return super()._reduce() * self._scale

    try:
        stat = StatTypeRegistry.create("test_scaled_point", repeat=2, scale=0.5)
        assert isinstance(stat, ScaledPoint)
        stat.add_observation(1.5)
        stat.add_observation(2.5)
        stat.balance_content()
        stat.reduce_duplicates()
        assert stat.reduced_content == 1.0
        with pytest.raises(RuntimeError, match="after balancing"):
            stat.add_observation(3.5)
        with pytest.raises(TypeError, match="unexpected keyword"):
            StatTypeRegistry.create("test_scaled_point", retired_option=True)
    finally:
        StatTypeRegistry._types.pop("test_scaled_point", None)


def test_failed_reduction_keeps_result_unpublished_and_can_retry() -> None:
    class FailsOnce(Scalar):
        __slots__ = ("_failed",)

        def __init__(self) -> None:
            super().__init__()
            self._failed = False

        def _reduce(self) -> float:
            if not self._failed:
                self._failed = True
                raise ValueError("reduction failed")
            return super()._reduce()

    stat = FailsOnce()
    stat.add_observation(1.5)
    stat.balance_content()
    with pytest.raises(ValueError, match="reduction failed"):
        stat.reduce_duplicates()
    assert not stat.is_reduced
    with pytest.raises(AttributeError):
        _ = stat.reduced_content
    stat.reduce_duplicates()
    assert stat.reduced_content == 1.5


def test_str_and_repr_use_declared_statistic_kind() -> None:
    stat = Scalar()
    stat.add_observation(42.5)
    assert str(stat) == "scalar(repeat=1, balanced=False, reduced=False, padded=0)"
    assert repr(stat) == str(stat)
