"""Tests for the download section UI function (render_download_section).

Covers:
- Engine-aware branch selection (Plotly vs Matplotlib)
- Format pills rendering for each engine
- Download button generation with correct MIME types
- Incomplete artifact rejection; the published figure selects the export engine
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import ring5
from src.web.models.render_artifact import RenderArtifact

import pandas as pd


@pytest.fixture
def plotly_artifact(plot_session: ring5.Session) -> RenderArtifact:
    """Return an actual public Plotly generation and its owned source rows."""
    plot = plot_session.create_plot(
        "bar",
        data=ring5.Table(pd.DataFrame({"benchmark": ["mcf"], "ipc": [2.1]})),
        config={"x": "benchmark", "y": "ipc", "width": 200, "height": 200},
    )
    plot_session.render(plot)
    return plot.render_artifact


@pytest.fixture
def matplotlib_artifact(plot_session: ring5.Session) -> RenderArtifact:
    """Return an actual public Matplotlib generation."""
    plot = plot_session.create_plot(
        "bar",
        data=ring5.Table(pd.DataFrame({"benchmark": ["mcf"], "ipc": [2.1]})),
        config={"x": "benchmark", "y": "ipc"},
    )
    plot_session.render(plot, engine="matplotlib")
    return plot.render_artifact


# Plotly branch


class TestRenderDownloadSectionPlotly:
    # [test->req~ring5.export.web-download~1]
    """render_download_section with Plotly engine active."""

    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_expander_created(
        self,
        mock_st: MagicMock,
        plotly_artifact: RenderArtifact,
    ) -> None:
        """An expander labelled '📥 Download' should be created."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        # Make pills return None (no selection yet)
        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.pills.return_value = None

        render_download_section(1, "plot", plotly_artifact)

        mock_st.expander.assert_called_once_with("📥 Download", expanded=False)

    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_plotly_pills_options(
        self,
        mock_st: MagicMock,
        plotly_artifact: RenderArtifact,
    ) -> None:
        """Plotly path should show png/svg/pdf pills."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.pills.return_value = None

        render_download_section(1, "plot", plotly_artifact)

        mock_st.pills.assert_called_once()
        _, kwargs = mock_st.pills.call_args
        assert kwargs["options"] == ["html", "png", "svg", "pdf"]
        assert kwargs["default"] == "html"

    @patch(
        "src.web.pages.ui.plotting.download_section.plotly_download_bytes",
        return_value=b"PDFDATA",
    )
    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_plotly_download_button_rendered(
        self,
        mock_st: MagicMock,
        mock_bytes: MagicMock,
        plotly_artifact: RenderArtifact,
    ) -> None:
        """The button should defer generation until it is clicked."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.pills.return_value = "pdf"
        mock_st.session_state = {}
        mock_st.download_button.return_value = True

        source_data = plotly_artifact.source_data
        with patch(
            "src.web.components.guided_analysis.GuidedAnalysisComponent.mark_exported"
        ) as mock_mark_exported:
            render_download_section(1, "myplot", plotly_artifact)

        mock_st.download_button.assert_called_once()
        _, kwargs = mock_st.download_button.call_args
        assert kwargs["label"] == "Download PDF"
        assert callable(kwargs["data"])
        mock_bytes.assert_not_called()
        assert kwargs["data"]() == b"PDFDATA"
        mock_bytes.assert_called_once()
        assert mock_bytes.call_args.kwargs["source_data"] is source_data
        assert mock_bytes.call_args.kwargs["scale"] == 1
        assert kwargs["file_name"] == "myplot.pdf"
        assert kwargs["mime"] == "application/pdf"
        assert callable(kwargs["on_click"])
        mock_mark_exported.assert_called_once_with()
        with patch(
            "src.web.components.guided_analysis.GuidedAnalysisComponent.mark_exported"
        ) as mock_callback_exported:
            kwargs["on_click"]()
        mock_callback_exported.assert_called_once_with()
        mock_st.rerun.assert_not_called()

    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_plotly_no_selection_no_download(
        self,
        mock_st: MagicMock,
        plotly_artifact: RenderArtifact,
    ) -> None:
        """When pills returns None, no download button should appear."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.pills.return_value = None

        render_download_section(1, "plot", plotly_artifact)

        mock_st.download_button.assert_not_called()


# Matplotlib branch


class TestRenderDownloadSectionMatplotlib:
    # [test->req~ring5.export.web-download~1]
    """render_download_section with Matplotlib engine active."""

    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_mpl_pills_options(
        self,
        mock_st: MagicMock,
        matplotlib_artifact: RenderArtifact,
    ) -> None:
        """Matplotlib path should show pdf/pgf/png/svg pills."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.pills.return_value = None

        render_download_section(1, "plot", matplotlib_artifact)

        mock_st.pills.assert_called_once()
        _, kwargs = mock_st.pills.call_args
        assert kwargs["options"] == ["pdf", "pgf", "png", "svg"]

    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_incomplete_artifact_fails_visibly(self, mock_st: MagicMock) -> None:
        """Detached config cannot masquerade as a published native download."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        with pytest.raises(TypeError, match="complete published native artifact"):
            render_download_section(1, "plot", RenderArtifact({}))
        mock_st.pills.assert_not_called()

    @patch(
        "src.web.pages.ui.plotting.download_section.matplotlib_download_bytes",
        return_value=b"PNGDATA",
    )
    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_mpl_download_button_rendered(
        self,
        mock_st: MagicMock,
        mock_bytes: MagicMock,
        matplotlib_artifact: RenderArtifact,
    ) -> None:
        """When format is selected, download button should appear."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.pills.return_value = "png"
        mock_st.download_button.return_value = True

        with patch(
            "src.web.components.guided_analysis.GuidedAnalysisComponent.mark_exported"
        ) as mock_mark_exported:
            render_download_section(5, "chart", matplotlib_artifact)

        mock_st.download_button.assert_called_once()
        _, kwargs = mock_st.download_button.call_args
        assert kwargs["label"] == "Download PNG"
        assert kwargs["data"] == b"PNGDATA"
        assert kwargs["file_name"] == "chart.png"
        assert kwargs["mime"] == "image/png"
        assert callable(kwargs["on_click"])
        mock_mark_exported.assert_called_once_with()
        with patch(
            "src.web.components.guided_analysis.GuidedAnalysisComponent.mark_exported"
        ) as mock_callback_exported:
            kwargs["on_click"]()
        mock_callback_exported.assert_called_once_with()
        mock_st.rerun.assert_not_called()

    @patch(
        "src.web.pages.ui.plotting.download_section.matplotlib_download_bytes",
        side_effect=[ValueError("PGF cannot contain raster images"), b"PDFDATA"],
    )
    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_pgf_raster_failure_falls_back_visibly_to_pdf(
        self,
        mock_st: MagicMock,
        mock_bytes: MagicMock,
        matplotlib_artifact: RenderArtifact,
    ) -> None:
        # [test->req~ring5.export.matplotlib-pgf~1]
        """Raster PGF failures warn and expose the actual PDF artifact."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        mock_st.expander.return_value.__enter__ = lambda context: context
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.session_state = {}
        mock_st.pills.return_value = "pgf"

        render_download_section(5, "chart", matplotlib_artifact)

        mock_st.warning.assert_called_once()
        assert [call.args[1] for call in mock_bytes.call_args_list] == ["pgf", "pdf"]
        _, kwargs = mock_st.download_button.call_args
        assert kwargs["label"] == "Download PDF"
        assert kwargs["data"] == b"PDFDATA"
        assert kwargs["file_name"] == "chart.pdf"
        assert kwargs["mime"] == "application/pdf"

    @patch("src.web.pages.ui.plotting.download_section.st")
    def test_widget_keys_scoped_to_plot_id(
        self,
        mock_st: MagicMock,
        plotly_artifact: RenderArtifact,
    ) -> None:
        """Widget keys must include plot_id to avoid collisions."""
        from src.web.pages.ui.plotting.download_section import render_download_section

        ctx = MagicMock()
        mock_st.expander.return_value.__enter__ = lambda s: ctx
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.pills.return_value = None

        render_download_section(42, "p", plotly_artifact)

        _, kwargs = mock_st.pills.call_args
        assert "42" in kwargs["key"]


@pytest.mark.parametrize("scale", [0.5, 1, 3])
@patch("src.web.pages.ui.plotting.download_section.plotly_download_bytes", return_value=b"SVG")
@patch("src.web.pages.ui.plotting.download_section.st")
def test_deferred_download_uses_the_same_published_figure_source_rows_and_scale(
    mock_st: MagicMock,
    mock_bytes: MagicMock,
    scale: float,
    plot_session: ring5.Session,
) -> None:
    # [test->req~ring5.export.plotly-scale~1]
    from src.web.pages.ui.plotting.download_section import render_download_section

    plot = plot_session.create_plot(
        "bar",
        data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [3.0]})),
        config={"x": "x", "y": "y", "export_scale": scale, "width": 900, "height": 540},
    )
    plot_session.render(plot)
    artifact = plot.render_artifact
    mock_st.pills.return_value = "svg"
    mock_st.download_button.return_value = False
    render_download_section(plot.plot_id, plot.name, artifact)
    generate = mock_st.download_button.call_args.kwargs["data"]
    mock_bytes.assert_not_called()
    assert generate() == b"SVG"
    mock_bytes.assert_called_once_with(
        artifact.figure,
        "svg",
        width=900,
        height=540,
        scale=scale,
        source_data=artifact.source_data,
    )
