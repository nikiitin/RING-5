"""Tests for engine-specific controls in the Advanced section."""

from typing import Any
from unittest.mock import MagicMock, patch

_MODULE = "src.web.components.plotting.settings.engine_settings"
_WF = "src.web.components.plotting.settings.widget_factory.st"


class TestEngineSpecificControls:
    """Verify render_engine_controls shows correct widgets per engine."""

    @patch(f"{_MODULE}.EngineManager")
    @patch(f"{_MODULE}.st")
    def test_plotly_shows_hovermode(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """When engine is Plotly, a hovermode selectbox is rendered."""
        from src.web.components.plotting.settings.engine_settings import (
            render_engine_controls,
        )

        mock_em.is_plotly.return_value = True
        mock_em.is_matplotlib.return_value = False
        mock_st.selectbox.return_value = "x unified"

        config: dict[str, Any] = {}
        with patch(_WF, mock_st):
            render_engine_controls(1, {}, config)

        mock_st.selectbox.assert_called_once()
        _, kwargs = mock_st.selectbox.call_args
        assert kwargs["label"] == "Hover mode"
        assert config["hovermode"] == "x unified"

    @patch(f"{_MODULE}.EngineManager")
    @patch(f"{_MODULE}.st")
    def test_matplotlib_disables_latex_preamble(
        self, mock_st: MagicMock, mock_em: MagicMock
    ) -> None:
        """Matplotlib fixes the preamble while still exposing the TeX system."""
        from src.web.components.plotting.settings.engine_settings import (
            render_engine_controls,
        )

        mock_em.is_plotly.return_value = False
        mock_em.is_matplotlib.return_value = True
        mock_st.text_area.return_value = "\\usepackage{amsmath}"
        mock_st.selectbox.return_value = "xelatex"

        config: dict[str, Any] = {}
        with patch(_WF, mock_st):
            render_engine_controls(1, {}, config)

        mock_st.text_area.assert_not_called()
        mock_st.caption.assert_called_once()
        assert config["latex_extra_preamble"] == ""

        # selectbox for TeX system
        mock_st.selectbox.assert_called_once()
        assert config["tex_system"] == "xelatex"

    @patch(f"{_MODULE}.EngineManager")
    @patch(f"{_MODULE}.st")
    def test_plotly_no_latex_widgets(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """Plotly mode does not render LaTeX-specific widgets."""
        from src.web.components.plotting.settings.engine_settings import (
            render_engine_controls,
        )

        mock_em.is_plotly.return_value = True
        mock_em.is_matplotlib.return_value = False
        mock_st.selectbox.return_value = "closest"

        config: dict[str, Any] = {}
        with patch(_WF, mock_st):
            render_engine_controls(1, {}, config)

        mock_st.text_area.assert_not_called()
        assert "latex_extra_preamble" not in config
        assert "tex_system" not in config

    @patch(f"{_MODULE}.EngineManager")
    @patch(f"{_MODULE}.st")
    def test_matplotlib_no_hovermode(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """Matplotlib mode does not render hovermode selectbox."""
        from src.web.components.plotting.settings.engine_settings import (
            render_engine_controls,
        )

        mock_em.is_plotly.return_value = False
        mock_em.is_matplotlib.return_value = True
        mock_st.text_area.return_value = ""
        mock_st.selectbox.return_value = "pdflatex"

        config: dict[str, Any] = {}
        with patch(_WF, mock_st):
            render_engine_controls(1, {}, config)

        assert "hovermode" not in config

    @patch(f"{_MODULE}.EngineManager")
    @patch(f"{_MODULE}.st")
    def test_saved_hovermode_preserved(self, mock_st: MagicMock, mock_em: MagicMock) -> None:
        """Previously saved hovermode value is used as default index."""
        from src.web.components.plotting.settings.engine_settings import (
            render_engine_controls,
        )

        mock_em.is_plotly.return_value = True
        mock_em.is_matplotlib.return_value = False
        mock_st.selectbox.return_value = "closest"

        config: dict[str, Any] = {}
        with patch(_WF, mock_st):
            render_engine_controls(1, {"hovermode": "closest"}, config)

        args, kwargs = mock_st.selectbox.call_args
        assert kwargs["index"] == 1  # "closest" is at index 1
