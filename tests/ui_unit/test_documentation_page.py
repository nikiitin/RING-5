"""Tests for the documentation hub page."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ── _link_card ───────────────────────────────────────────────────────


class TestLinkCard:
    """Tests for the ``_link_card`` helper function."""

    @patch("src.web.pages.documentation.st")
    def test_existing_file_no_coming_soon(self, mock_st: MagicMock) -> None:
        """Existing doc paths should not show '(coming soon)'."""
        from src.web.pages.documentation import _link_card

        # Use a path we know exists
        _link_card("🚀", "Quick Start", "Get started fast.", "webapp/Quick-Start.md")

        call_args = mock_st.markdown.call_args[0][0]
        assert "(coming soon)" not in call_args
        assert "Quick Start" in call_args

    @patch("src.web.pages.documentation.st")
    def test_missing_file_shows_coming_soon(self, mock_st: MagicMock) -> None:
        """Non-existent doc paths should show '(coming soon)' marker."""
        from src.web.pages.documentation import _link_card

        _link_card("🔮", "Future", "Not yet.", "does/not/exist.md")

        call_args = mock_st.markdown.call_args[0][0]
        assert "(coming soon)" in call_args

    @patch("src.web.pages.documentation.st")
    def test_card_contains_icon_and_title(self, mock_st: MagicMock) -> None:
        from src.web.pages.documentation import _link_card

        _link_card("📂", "Data Source", "Load data.", "webapp/pages/Data-Source.md")

        call_args = mock_st.markdown.call_args[0][0]
        assert "📂" in call_args
        assert "Data Source" in call_args
        assert "Load data." in call_args

    @patch("src.web.pages.documentation.st")
    def test_card_shows_doc_path(self, mock_st: MagicMock) -> None:
        from src.web.pages.documentation import _link_card

        _link_card("📄", "Test", "Desc.", "api/Backend-Facade.md")

        call_args = mock_st.markdown.call_args[0][0]
        assert "docs/api/Backend-Facade.md" in call_args


# ── show_documentation_page ──────────────────────────────────────────


class TestShowDocumentationPage:
    """Tests for the main ``show_documentation_page`` renderer."""

    @patch("src.web.pages.documentation.st")
    def test_renders_without_error(self, mock_st: MagicMock) -> None:
        """Full page renders without raising exceptions."""
        from src.web.pages.documentation import show_documentation_page

        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        show_documentation_page()

        # Page should call st.markdown for header
        assert mock_st.markdown.call_count > 0

    @patch("src.web.pages.documentation.st")
    def test_contains_all_three_sections(self, mock_st: MagicMock) -> None:
        """Page should render WebApp, API, and Developer sections."""
        from src.web.pages.documentation import show_documentation_page

        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        show_documentation_page()

        all_markdown = " ".join(str(c[0][0]) for c in mock_st.markdown.call_args_list if c[0])
        assert "WebApp Guide" in all_markdown
        assert "API Reference" in all_markdown
        assert "Developer Guides" in all_markdown

    @patch("src.web.pages.documentation.st")
    def test_uses_column_layout(self, mock_st: MagicMock) -> None:
        """Page should use st.columns for card layout."""
        from src.web.pages.documentation import show_documentation_page

        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        show_documentation_page()

        assert mock_st.columns.call_count >= 3  # WebApp + API + Developer

    @patch("src.web.pages.documentation.st")
    def test_link_cards_reference_real_docs(self, mock_st: MagicMock) -> None:
        """Cards should reference actual documentation paths."""
        from src.web.pages.documentation import show_documentation_page

        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        show_documentation_page()

        all_markdown = " ".join(str(c[0][0]) for c in mock_st.markdown.call_args_list if c[0])
        # Key docs should be referenced
        assert "Quick-Start.md" in all_markdown
        assert "Backend-Facade.md" in all_markdown
        assert "Architecture.md" in all_markdown
