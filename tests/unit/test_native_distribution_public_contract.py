"""The public custom-backend surface owns explicit nullable native declarations."""

import copy

import pandas as pd
import pytest

import ring5


def layout_payload(kind):
    native = kind == "gem5_distribution"
    labels = ["underflows", "0", "overflows"]
    payload = {
        "kind": kind,
        "basis": "request",
        "columns": [
            {
                "column": f"d..{label}",
                "source_label": label,
                "role": (["underflow", "bucket", "overflow"][index] if native else "source"),
                "native_index": (0 if native and index == 1 else None),
            }
            for index, label in enumerate(labels)
        ],
    }
    if native:
        payload.update(
            geometry={"minimum": 0.0, "maximum": 0.0, "bucket_size": 1.0}, zero_policy="missing"
        )
    return payload


def test_public_lazy_layout_constructors_bind_arbitrary_exact_physical_names():
    geometry = ring5.DistributionGeometry(0.25, 0.25, 1)
    bindings = (
        ring5.DistributionColumn("left", "underflows", "underflow", None),
        ring5.DistributionColumn("cell", "0.25", "bucket", 0),
        ring5.DistributionColumn("right", "overflows", "overflow", None),
    )
    layout = ring5.NativeDistributionLayout(geometry, "missing", bindings)
    variable = ring5.ParsedVariableResult(
        "source",
        "number",
        "entries",
        (
            ring5.ParsedCell("left", "number", 0.0),
            ring5.ParsedCell("cell", "number", 2.0),
            ring5.ParsedCell("right", "number", 0.0),
        ),
        layout=layout,
    )
    assert variable.schema.layout is layout
    opaque = ring5.OpaqueDistributionLayout(
        (ring5.DistributionColumn("literal", "0-1", "source", None),)
    )
    assert opaque.kind == "distribution_source_labels"
    for name in (
        "DistributionGeometry",
        "DistributionColumn",
        "NativeDistributionLayout",
        "OpaqueDistributionLayout",
    ):
        assert name in ring5.__all__ and getattr(ring5, name) is not None
    with pytest.raises(TypeError, match="layout"):
        ring5.ParsedVariableSchema("ordinary", "number", "scalar")
    assert ring5.ParsedVariableSchema("ordinary", "number", "scalar", layout=None).layout is None


@pytest.mark.parametrize("kind", ["gem5_distribution", "distribution_source_labels"])
@pytest.mark.parametrize("engine", ["matplotlib", "plotly"])
def test_declared_native_layout_rejects_generic_histogram_without_mutation(
    kind, engine, platformdirs_isolated
):
    frame = pd.DataFrame({"d..underflows": [0.0], "d..0": [2.0], "d..overflows": [0.0]})
    frame.attrs["ring5.distribution_layouts"] = {"d": layout_payload(kind)}
    before = frame.copy(deep=True)
    attrs = copy.deepcopy(frame.attrs)
    with ring5.Session() as session:
        previous = session.plot(
            "bar",
            data=ring5.Table.from_rows([{"name": "a", "value": 3.0}]),
            config=ring5.FigureSpec(x="name", y_columns=["value"]),
            engine="matplotlib",
        )
        with pytest.raises(ring5.RenderError, match="Native Distribution"):
            session.plot(
                "histogram",
                data=ring5.Table(frame),
                config=ring5.FigureSpec(extra={"histogram_variable": "d"}),
                engine=engine,
            )
        assert previous.axes[0].patches[0].get_height() == 3.0
    pd.testing.assert_frame_equal(frame, before)
    assert frame.attrs == attrs


def test_ordinary_vector_generic_histogram_keeps_explicit_interval_interpretation():
    from src.web.pages.ui.plotting.types.histogram_plot import HistogramPlot

    frame = pd.DataFrame({"d..0-1": [2.0], "d..2-3": [4.0]})
    before = frame.copy(deep=True)
    result = HistogramPlot(1, "generic").create_traces(frame, {"histogram_variable": "d"})
    assert result.traces[0].y == [2.0, 4.0]
    assert result.traces[0].x_positions == [1.0, 3.0]
    pd.testing.assert_frame_equal(frame, before)
