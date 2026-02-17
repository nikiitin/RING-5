"""Tests for engine-specific controls in Advanced section (Step 30)."""

from typing import Any, Dict
from unittest.mock import MagicMock, patch


class TestEngineSpecificControls:
    """Verify _render_engine_specific_controls shows correct widgets per engine."""

    def _make_plot(self) -> MagicMock:
        """Create a mock with real _render_engine_specific_controls bound."""
        from src.web.pages.ui.plotting.base_plot import BasePlot

        plot = MagicMock()
        plot.plot_id = 1
        plot._render_engine_specific_controls = BasePlot._render_engine_specific_controls.__get__(
            plot, type(plot)
        )
        return plot

    @patch("src.web.pages.ui.plotting.base_plot.EngineManager")
    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_plotly_shows_hovermode(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """When engine is Plotly, a hovermode selectbox is rendered."""
        mock_em.is_plotly.return_value = True
        mock_em.is_matplotlib.return_value = False
        mock_st.selectbox.return_value = "x unified"

        plot = self._make_plot()
        config: Dict[str, Any] = {}
        plot._render_engine_specific_controls({}, config)

        mock_st.selectbox.assert_called_once()
        args, kwargs = mock_st.selectbox.call_args
        assert args[0] == "Hover mode"
        assert config["hovermode"] == "x unified"

    @patch("src.web.pages.ui.plotting.base_plot.EngineManager")
    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_matplotlib_shows_latex_preamble(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """When engine is Matplotlib, LaTeX preamble and TeX system are shown."""
        mock_em.is_plotly.return_value = False
        mock_em.is_matplotlib.return_value = True
        mock_st.text_area.return_value = "\\usepackage{amsmath}"
        mock_st.selectbox.return_value = "xelatex"

        plot = self._make_plot()
        config: Dict[str, Any] = {}
        plot._render_engine_specific_controls({}, config)

        # text_area for preamble
        mock_st.text_area.assert_called_once()
        assert config["latex_extra_preamble"] == "\\usepackage{amsmath}"

        # selectbox for TeX system
        mock_st.selectbox.assert_called_once()
        assert config["tex_system"] == "xelatex"

    @patch("src.web.pages.ui.plotting.base_plot.EngineManager")
    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_plotly_no_latex_widgets(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """Plotly mode does not render LaTeX-specific widgets."""
        mock_em.is_plotly.return_value = True
        mock_em.is_matplotlib.return_value = False
        mock_st.selectbox.return_value = "closest"

        plot = self._make_plot()
        config: Dict[str, Any] = {}
        plot._render_engine_specific_controls({}, config)

        mock_st.text_area.assert_not_called()
        assert "latex_extra_preamble" not in config
        assert "tex_system" not in config

    @patch("src.web.pages.ui.plotting.base_plot.EngineManager")
    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_matplotlib_no_hovermode(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """Matplotlib mode does not render hovermode selectbox."""
        mock_em.is_plotly.return_value = False
        mock_em.is_matplotlib.return_value = True
        mock_st.text_area.return_value = ""
        mock_st.selectbox.return_value = "pdflatex"

        plot = self._make_plot()
        config: Dict[str, Any] = {}
        plot._render_engine_specific_controls({}, config)

        assert "hovermode" not in config

    @patch("src.web.pages.ui.plotting.base_plot.EngineManager")
    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_saved_hovermode_preserved(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """Previously saved hovermode value is used as default index."""
        mock_em.is_plotly.return_value = True
        mock_em.is_matplotlib.return_value = False
        mock_st.selectbox.return_value = "closest"

        plot = self._make_plot()
        config: Dict[str, Any] = {}
        plot._render_engine_specific_controls({"hovermode": "closest"}, config)

        args, kwargs = mock_st.selectbox.call_args
        assert kwargs["index"] == 1  # "closest" is at index 1
