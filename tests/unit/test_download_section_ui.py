"""Tests for the download section UI function (render_download_section).

Covers:
- Engine-aware branch selection (Plotly vs Matplotlib)
- Format pills rendering for each engine
- Download button generation with correct MIME types
- Matplotlib fallback when no figure is stored in session state
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import plotly.graph_objects as go
from matplotlib.figure import Figure as MplFigure

# ── Helpers ──────────────────────────────────────────────────────


def _simple_plotly_fig() -> go.Figure:
    """Return a tiny Plotly figure."""
    fig = go.Figure(go.Bar(x=["a"], y=[1]))
    fig.update_layout(width=200, height=200)
    return fig


def _simple_mpl_fig() -> MplFigure:
    """Return a tiny Matplotlib figure."""
    fig = MplFigure(figsize=(2, 2))
    ax = fig.add_subplot(111)
    ax.bar(["a"], [1])
    return fig


# ── Plotly branch ────────────────────────────────────────────────


class TestRenderDownloadSectionPlotly:
    """render_download_section with Plotly engine active."""

    @patch("src.web.pages.ui.plotting.download_section.EngineManager")
    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_expander_created(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """An expander labelled '📥 Download' should be created."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        mock_em.is_matplotlib.return_value = False
        # Make pills return None (no selection yet)
        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.pills.return_value = None

        render_download_section(1, "plot", _simple_plotly_fig())

        mock_st.expander.assert_called_once_with("📥 Download", expanded=False)

    @patch("src.web.pages.ui.plotting.download_section.EngineManager")
    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_plotly_pills_options(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """Plotly path should show png/svg/pdf pills."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        mock_em.is_matplotlib.return_value = False
        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.pills.return_value = None

        render_download_section(1, "plot", _simple_plotly_fig())

        mock_st.pills.assert_called_once()
        _, kwargs = mock_st.pills.call_args
        assert kwargs["options"] == ["html", "png", "svg", "pdf"]
        assert kwargs["default"] == "html"

    @patch(
        "src.web.pages.ui.plotting.download_section.plotly_download_bytes",
        return_value=b"PDFDATA",
    )
    @patch("src.web.pages.ui.plotting.download_section.EngineManager")
    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_plotly_download_button_rendered(
        self,
        mock_st: MagicMock,
        mock_em: MagicMock,
        mock_bytes: MagicMock,
    ) -> None:
        """When a format is selected, a download button should appear."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        mock_em.is_matplotlib.return_value = False
        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.pills.return_value = "pdf"

        render_download_section(1, "myplot", _simple_plotly_fig())

        mock_st.download_button.assert_called_once()
        _, kwargs = mock_st.download_button.call_args
        assert kwargs["label"] == "Download PDF"
        assert kwargs["data"] == b"PDFDATA"
        assert kwargs["file_name"] == "myplot.pdf"
        assert kwargs["mime"] == "application/pdf"

    @patch("src.web.pages.ui.plotting.download_section.EngineManager")
    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_plotly_no_selection_no_download(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """When pills returns None, no download button should appear."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        mock_em.is_matplotlib.return_value = False
        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.pills.return_value = None

        render_download_section(1, "plot", _simple_plotly_fig())

        mock_st.download_button.assert_not_called()


# ── Matplotlib branch ────────────────────────────────────────────


class TestRenderDownloadSectionMatplotlib:
    """render_download_section with Matplotlib engine active."""

    @patch("src.web.pages.ui.plotting.download_section.EngineManager")
    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_mpl_pills_options(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """Matplotlib path should show pdf/pgf/png/svg pills."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        mock_em.is_matplotlib.return_value = True
        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.session_state = {"plot.1.mpl_fig": _simple_mpl_fig()}
        mock_st.pills.return_value = None

        render_download_section(1, "plot", _simple_plotly_fig())

        mock_st.pills.assert_called_once()
        _, kwargs = mock_st.pills.call_args
        assert kwargs["options"] == ["pdf", "pgf", "png", "svg"]

    @patch("src.web.pages.ui.plotting.download_section.EngineManager")
    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_mpl_no_fig_shows_warning(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """When no mpl figure is in session state, show a warning."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        mock_em.is_matplotlib.return_value = True
        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.session_state = {}  # no mpl_fig stored

        render_download_section(1, "plot", _simple_plotly_fig())

        mock_st.warning.assert_called_once()
        mock_st.pills.assert_not_called()

    @patch(
        "src.web.pages.ui.plotting.download_section.matplotlib_download_bytes",
        return_value=b"PNGDATA",
    )
    @patch("src.web.pages.ui.plotting.download_section.EngineManager")
    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_mpl_download_button_rendered(
        self,
        mock_st: MagicMock,
        mock_em: MagicMock,
        mock_bytes: MagicMock,
    ) -> None:
        """When format is selected, download button should appear."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        mock_em.is_matplotlib.return_value = True
        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.session_state = {"plot.5.mpl_fig": _simple_mpl_fig()}
        mock_st.pills.return_value = "png"

        render_download_section(5, "chart", _simple_plotly_fig())

        mock_st.download_button.assert_called_once()
        _, kwargs = mock_st.download_button.call_args
        assert kwargs["label"] == "Download PNG"
        assert kwargs["data"] == b"PNGDATA"
        assert kwargs["file_name"] == "chart.png"
        assert kwargs["mime"] == "image/png"

    @patch("src.web.pages.ui.plotting.download_section.EngineManager")
    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_widget_keys_scoped_to_plot_id(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """Widget keys must include plot_id to avoid collisions."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        mock_em.is_matplotlib.return_value = False
        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.pills.return_value = None

        render_download_section(42, "p", _simple_plotly_fig())

        _, kwargs = mock_st.pills.call_args
        assert "42" in kwargs["key"]
