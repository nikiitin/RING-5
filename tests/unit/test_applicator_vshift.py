import plotly.graph_objects as go
import pytest

from src.plotting.styles.applicator import StyleApplicator


@pytest.fixture
def applicator():
    return StyleApplicator(plot_type="bar")


def test_yaxis_title_standard_mode(applicator):
    """Test standard mode (vshift=0) uses native axis title."""
    fig = go.Figure()
    config = {"yaxis_title": "Standard Title", "yaxis_title_vshift": 0}

    fig = applicator._apply_axes_styling(fig, config)

    # Check native title
    assert fig.layout.yaxis.title.text == "Standard Title"
    # Check NO annotations
    assert len(fig.layout.annotations) == 0


def test_yaxis_title_vshift_mode(applicator):
    """Test vshift mode uses annotation and clears native title."""
    fig = go.Figure()
    config = {"yaxis_title": "Shifted Title", "yaxis_title_vshift": 50, "yaxis_title_standoff": 10}

    fig = applicator._apply_axes_styling(fig, config)

    # Check native title is cleared
    # Note: applicator logic sets it to ""
    assert fig.layout.yaxis.title.text == ""

    # Check annotation created
    assert len(fig.layout.annotations) == 1
    ann = fig.layout.annotations[0]

    assert ann.text == "Shifted Title"
    assert ann.yshift == 50
    # xshift = -standoff - 40 => -10 - 40 = -50
    assert ann.xshift == -50
    assert ann.xref == "paper"
    assert ann.yref == "paper"
