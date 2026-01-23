import plotly.graph_objects as go

from src.plotting.styles.applicator import StyleApplicator


def test_legend_fixed_pixel_columns():
    """Verify that ncols creates fixed pixel entrywidth for stable columns."""
    applicator = StyleApplicator(plot_type="bar")

    # Create figure with 6 traces
    fig = go.Figure()
    for i in range(6):
        fig.add_trace(go.Bar(y=[1, 2], name=f"Trace {i}"))

    # ---------------------------------------------------------
    # TEST 1: Request 3 columns with 800px plot width
    # ---------------------------------------------------------
    config = {
        "legend_ncols": 3,
        "legend_x": 0.5,
        "legend_y": 1.02,
        "width": 800,
    }

    fig = applicator.apply_styles(fig, config)

    layout_json = fig.layout.to_plotly_json()

    # Check that only ONE legend exists
    legend_keys = [k for k in layout_json.keys() if k.startswith("legend")]
    assert len(legend_keys) == 1, f"Expected 1 legend, got {legend_keys}"

    # Check entrywidth is pixel-based: (800 * 0.8) / 3 = 213
    expected_width = int((800 * 0.8) / 3)
    assert (
        layout_json["legend"]["entrywidth"] == expected_width
    ), f"Expected {expected_width}, got {layout_json['legend']['entrywidth']}"
    assert layout_json["legend"]["entrywidthmode"] == "pixels"
    assert layout_json["legend"]["orientation"] == "h"

    # ---------------------------------------------------------
    # TEST 2: Request 2 columns with 1000px plot width
    # ---------------------------------------------------------
    fig2 = go.Figure()
    for i in range(4):
        fig2.add_trace(go.Bar(y=[1, 2], name=f"Trace {i}"))

    config2 = {
        "legend_ncols": 2,
        "legend_x": 1.02,
        "legend_y": 1.0,
        "width": 1000,
    }

    fig2 = applicator.apply_styles(fig2, config2)
    layout_json2 = fig2.layout.to_plotly_json()

    # Check entrywidth: (1000 * 0.8) / 2 = 400
    expected_width2 = int((1000 * 0.8) / 2)
    assert layout_json2["legend"]["entrywidth"] == expected_width2

    # ---------------------------------------------------------
    # TEST 3: No cols - should not set entrywidth
    # ---------------------------------------------------------
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(y=[1, 2], name="Test"))

    config3 = {
        "legend_ncols": 0,
        "legend_x": 1.0,
        "legend_y": 1.0,
    }

    fig3 = applicator.apply_styles(fig3, config3)
    layout_json3 = fig3.layout.to_plotly_json()

    # entrywidth should not be set when ncols=0
    assert layout_json3["legend"].get("entrywidth") is None

    print("All tests passed!")


if __name__ == "__main__":
    try:
        test_legend_fixed_pixel_columns()
        print("Verification PASSED: Fixed pixel entrywidth for stable columns.")
    except AssertionError as e:
        print(f"Verification FAILED: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
