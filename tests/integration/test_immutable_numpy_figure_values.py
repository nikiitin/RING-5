"""Immutable scientific scalars survive the public figure value boundary."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Literal

import numpy as np
import pytest

import ring5

pytestmark = pytest.mark.public_api


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_computed_pandas_range_renders_through_both_engines(
    engine: Literal["plotly", "matplotlib"],
) -> None:
    # [test->req~ring5.api.figure-spec~1]
    table = ring5.Table.from_rows([{"x": "a", "v": 1.0}, {"x": "b", "v": 2.0}])
    maximum = table.frame["v"].max()
    assert type(maximum) is np.float64
    spec = ring5.FigureSpec(x="x", y_columns=["v"], y_range=(0.0, maximum))
    assert spec.y_range[1] is maximum
    assert spec.to_config()["range_y"] == [0.0, 2.0]
    assert type(spec.to_config()["range_y"][1]) is float
    with ring5.Session() as session:
        figure = session.plot("bar", data=table, config=spec, engine=engine)
        if engine == "plotly":
            assert list(figure.layout.yaxis.range) == [0.0, 2.0]
        else:
            assert figure.axes[0].get_ylim() == pytest.approx((0.0, 2.0))


def test_numpy_real_bool_and_text_leaves_remain_exact_in_owned_projections() -> None:
    # [test->req~ring5.api.figure-spec~1]
    real = np.longdouble("1.0000000000000000001")
    leaves = {
        "real": real,
        "small": np.float32(1.5),
        "integer": np.int64(2),
        "long_integer": np.longlong(3),
        "unsigned": np.uint64(4),
        "enabled": np.bool_(True),
        "text": np.str_("Value"),
    }
    values = dict(leaves)
    spec = ring5.FigureSpec(extra={"metadata": values})
    values.clear()
    first = spec.to_config()
    for name, value in leaves.items():
        assert type(spec.extra["metadata"][name]) is type(value)
        assert first["metadata"][name] is value
    if np.finfo(np.longdouble).nmant > np.finfo(float).nmant:
        assert real != np.longdouble(float(real))
    with pytest.raises(TypeError):
        spec.extra["metadata"]["real"] = 0
    first["metadata"]["real"] = 0
    second = spec.to_config()
    assert second["metadata"]["real"] is real


@pytest.mark.parametrize(
    "value",
    [
        np.array([(1,)], dtype=[("value", "i8")])[0],
        np.array([{"values": [1]}], dtype=object),
        np.object_(object()),
        np.complex128(1 + 2j),
        np.bytes_(b"value"),
    ],
)
def test_mutable_or_unsupported_numpy_values_are_rejected(value: object) -> None:
    with pytest.raises(TypeError, match="Unsupported mutable figure value"):
        ring5.FigureSpec(extra={"value": value})


def test_mutable_numpy_scalar_subclasses_are_rejected() -> None:
    class MutableFloat(np.float64):
        pass

    value = MutableFloat(1.0)
    value.state = []
    with pytest.raises(TypeError, match="Unsupported mutable figure value"):
        ring5.FigureSpec(extra={"value": value})


def test_cold_public_import_and_native_spec_do_not_import_numpy() -> None:
    root = Path(__file__).resolve().parents[2]
    script = (
        "import sys; "
        f"sys.path.insert(0, {str(root)!r}); "
        "import ring5; "
        "assert 'numpy' not in sys.modules; "
        "ring5.FigureSpec(x='x', y_columns=['v']).to_config(); "
        "assert 'numpy' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, timeout=10)
