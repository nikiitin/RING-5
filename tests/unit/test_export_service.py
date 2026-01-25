from unittest.mock import MagicMock, patch

import pytest

from src.plotting.export import ExportService


@pytest.fixture
def mock_streamlit():
    with patch("src.plotting.export.st") as mock_st:
        yield mock_st


def test_export_html(mock_streamlit):
    fig = MagicMock()
    config = {"download_format": "html"}
    
    with patch("plotly.io.to_html", return_value="<html></html>"):
        ExportService.render_download_button("test_plot", 1, fig, config)
        
    mock_streamlit.download_button.assert_called_once()
    args = mock_streamlit.download_button.call_args[1]
    assert args["mime"] == "text/html"
    assert args["file_name"] == "test_plot.html"


def test_export_static_kaleido_success(mock_streamlit):
    fig = MagicMock()
    config = {"download_format": "png"}
    
    # Mock kaleido success
    with patch("src.plotting.export.ExportService._export_with_kaleido") as mock_kaleido:
        mock_kaleido.return_value = b"fake_png_data"
        
        ExportService.render_download_button("test_plot", 1, fig, config)
        
        mock_kaleido.assert_called_once()
        mock_streamlit.download_button.assert_called_once()
        args = mock_streamlit.download_button.call_args[1]
        assert args["mime"] == "image/png"
        assert args["file_name"] == "test_plot.png"
        assert args["key"] == "dl_btn_1_png_hires"


def test_export_static_fallback(mock_streamlit):
    fig = MagicMock()
    config = {"download_format": "png"}
    
    # Mock kaleido failure and matplotlib success
    with patch("src.plotting.export.ExportService._export_with_kaleido", side_effect=ImportError("No kaleido")), \
         patch("src.plotting.export.ExportService._convert_to_matplotlib", return_value=b"fake_mpl_png") as mock_mpl:
        
        ExportService.render_download_button("test_plot", 1, fig, config)
        
        mock_mpl.assert_called_once()
        mock_streamlit.warning.assert_called()
        mock_streamlit.download_button.assert_called_once()
        args = mock_streamlit.download_button.call_args[1]
        assert args["key"] == "dl_btn_1_png_fallback"
