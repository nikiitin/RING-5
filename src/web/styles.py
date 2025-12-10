"""
RING-5 Web Application Styles
Centralized styling and theming for the Streamlit application.
"""


class AppStyles:
    """Central repository for application CSS styles."""

    # Color scheme
    PRIMARY_COLOR = "#667eea"
    SECONDARY_COLOR = "#764ba2"
    SUCCESS_COLOR = "#d4edda"
    SUCCESS_BORDER = "#c3e6cb"
    INFO_COLOR = "#d1ecf1"
    INFO_BORDER = "#bee5eb"
    BACKGROUND_LIGHT = "#f0f2f6"

    @staticmethod
    def get_custom_css() -> str:
        """Return the complete custom CSS for the application."""
        return """
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .step-header {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
    }
    .progress-container {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin: 1rem 0;
    }
</style>
"""

    @staticmethod
    def header(text: str) -> str:
        """Return HTML for a main header."""
        return f'<h1 class="main-header">{text}</h1>'

    @staticmethod
    def step_header(text: str) -> str:
        """Return HTML for a step header."""
        return f'<div class="step-header"><h2>{text}</h2></div>'

    @staticmethod
    def success_box(text: str) -> str:
        """Return HTML for a success message box."""
        return f'<div class="success-box">{text}</div>'

    @staticmethod
    def info_box(text: str) -> str:
        """Return HTML for an info message box."""
        return f'<div class="info-box">{text}</div>'


class PageConfig:
    """Configuration for Streamlit pages."""

    TITLE = "RING-5 Interactive Analyzer"
    ICON = "⚡"
    LAYOUT = "wide"
    SIDEBAR_STATE = "expanded"

    @staticmethod
    def apply():
        """Apply page configuration (should be called once at app start)."""
        import streamlit as st

        st.set_page_config(
            page_title=PageConfig.TITLE,
            page_icon=PageConfig.ICON,
            layout=PageConfig.LAYOUT,
            initial_sidebar_state=PageConfig.SIDEBAR_STATE,
        )
