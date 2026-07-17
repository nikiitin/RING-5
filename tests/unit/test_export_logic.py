"""End-to-end figure export through the public ring5 surface.

Uses only the zero-dependency formats (matplotlib pdf/svg, plotly html) so
the tests run on a machine with nothing but the pip install.
"""

import os
from typing import Any

import pandas as pd
import pytest

import ring5

pytestmark = pytest.mark.public_api


@pytest.fixture
def session() -> Any:
    return ring5.Session()


@pytest.fixture
def bar_plot(session: Any) -> Any:
    df = pd.DataFrame({"x": ["A", "B"], "y": [10.0, 20.0]})
    return session.create_plot(
        "bar",
        data=df,
        config={"x": "x", "y": "y", "title": "Test Title", "xlabel": "X", "ylabel": "Y"},
        name="Test Plot",
    )


def test_export_pdf_via_matplotlib(tmp_path: Any, session: Any, bar_plot: Any) -> None:
    """Full real path: render(engine=matplotlib) → .pdf file (no LaTeX/Chrome)."""
    fig = session.render(bar_plot, engine="matplotlib")
    path = session.export(fig, str(tmp_path / "test_plot.pdf"))

    assert os.path.exists(path)
    assert path.endswith("test_plot.pdf")
    with open(path, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_export_html_via_plotly(tmp_path: Any, session: Any, bar_plot: Any) -> None:
    """Plotly HTML export needs no external binary."""
    fig = session.render(bar_plot, engine="plotly")
    path = session.export(fig, str(tmp_path / "test_plot.html"))

    assert os.path.exists(path)
    data = open(path, "rb").read()
    assert b"<html" in data[:200].lower()
    assert os.path.getsize(path) > 0


def test_export_format_override(tmp_path: Any, session: Any, bar_plot: Any) -> None:
    """Explicit fmt wins over the file extension."""
    fig = session.render(bar_plot, engine="matplotlib")
    path = session.export(fig, str(tmp_path / "weird_ext.dat"), fmt="svg")

    data = open(path, "rb").read()
    assert b"<svg" in data[:500]


def test_export_rejects_invalid_format(tmp_path: Any, session: Any, bar_plot: Any) -> None:
    """Unknown formats (incl. traversal attempts) raise the typed error."""
    fig = session.render(bar_plot, engine="matplotlib")

    with pytest.raises(ring5.ExportError, match="not supported"):
        session.export(fig, str(tmp_path / "x.bin"), fmt="../../../etc/passwd")

    # html is plotly-only; pgf is matplotlib-only
    with pytest.raises(ring5.ExportError, match="not supported"):
        session.export(fig, str(tmp_path / "x.html"))

    plotly_fig = session.render(bar_plot, engine="plotly")
    with pytest.raises(ring5.ExportError, match="not supported"):
        session.export(plotly_fig, str(tmp_path / "x.pgf"))


def test_export_no_extension_no_fmt_raises(tmp_path: Any, session: Any, bar_plot: Any) -> None:
    fig = session.render(bar_plot, engine="matplotlib")
    with pytest.raises(ring5.ExportError, match="No format"):
        session.export(fig, str(tmp_path / "noext"))


def test_deterministic_mpl_pdf_byte_identical(tmp_path: Any, session: Any, bar_plot: Any) -> None:
    """deterministic=True makes re-exports byte-identical (CI contract)."""
    fig = session.render(bar_plot, engine="matplotlib")
    a = session.export_bytes(fig, "pdf", deterministic=True)
    b = session.export_bytes(fig, "pdf", deterministic=True)
    assert a == b


def test_deterministic_html_byte_identical(tmp_path: Any, session: Any, bar_plot: Any) -> None:
    fig = session.render(bar_plot, engine="plotly")
    a = session.export_bytes(fig, "html", deterministic=True)
    b = session.export_bytes(fig, "html", deterministic=True)
    assert a == b


def test_multi_heatmap_colorbar_font_matches_spec(session: Any) -> None:
    """Colorbars are created after the per-axes styling pass — they must
    still get spec.font_family, not the process default (regression)."""
    import matplotlib
    import matplotlib.text

    df = pd.DataFrame(
        {
            "config_abbrev": ["A", "B", "A", "B"],
            "benchmark_name": ["bm1", "bm1", "bm2", "bm2"],
            "m1": [10.0, 20.0, 30.0, 40.0],
            "m2": [11.0, 21.0, 31.0, 41.0],
        }
    )
    plot = session.create_plot(
        "heatmap",
        data=df,
        config={
            "x": "config_abbrev",
            "facet_col": "benchmark_name",
            "metric_columns": ["m1", "m2"],
            "aggregation": "mean",
        },
    )
    fig = session.render(plot, engine="matplotlib")
    spec_family = fig._ring5_spec.font_family
    assert spec_family, "spec must resolve a font family"

    # Every text artist on the figure — including the colorbar's tick
    # labels and title — must carry the spec family.
    wrong = [
        t.get_text()
        for t in fig.findobj(matplotlib.text.Text)
        if t.get_text().strip() and t.get_fontfamily() != [spec_family]
    ]
    assert wrong == [], f"artists with wrong font family: {wrong}"


def test_render_does_not_accumulate_pyplot_figures(session: Any, bar_plot: Any) -> None:
    """Headless renders are deregistered from pyplot — batch loops
    (render_portfolio) must not pin one open figure per plot."""
    import matplotlib.pyplot as plt

    before = len(plt.get_fignums())
    figs = [session.render(bar_plot, engine="matplotlib") for _ in range(5)]
    assert len(plt.get_fignums()) == before

    # The returned figures remain fully usable after deregistration.
    assert session.export_bytes(figs[-1], "pdf")[:5] == b"%PDF-"
