import plotly.graph_objects as go
import pytest

from src.plotting.styles.applicator import StyleApplicator


@pytest.fixture
def applicator():
    return StyleApplicator(plot_type="bar")


def test_apply_axes_styling_standoff(applicator):
    """Test that Y-axis title standoff is applied."""
    fig = go.Figure()
    # Mock update_yaxes so we can inspect calls easily if needed,
    # but inspecting the figure object is better for integration testing the logic.

    config = {"yaxis_title": "My Y Axis", "yaxis_title_standoff": 42}

    fig = applicator._apply_axes_styling(fig, config)

    # Check that fig layout has the property
    # Plotly stores this deep in layout
    assert fig.layout.yaxis.title.text == "My Y Axis"
    assert fig.layout.yaxis.title.standoff == 42
