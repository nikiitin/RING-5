"""Tests for the documentation hub page."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestPublishedUrl:
    """Tests for published documentation URL construction."""

    def test_normalizes_route_slashes(self) -> None:
        from src.web.pages.documentation import _published_url

        assert _published_url("/user-guide/workflows/plotting/") == (
            "https://nikiitin.github.io/RING-5/user-guide/workflows/plotting/"
        )


class TestLinkCard:
    """Tests for the ``_link_card`` helper."""

    @patch("src.web.pages.documentation.st")
    def test_card_links_to_published_page(self, mock_st: MagicMock) -> None:
        from src.web.pages.documentation import _link_card

        _link_card(
            "First analysis", "Create a figure.", "user-guide/getting-started/first-analysis"
        )

        markdown = mock_st.markdown.call_args.args[0]
        assert "First analysis" in markdown
        assert "Create a figure." in markdown
        assert (
            "https://nikiitin.github.io/RING-5/user-guide/getting-started/first-analysis/"
            in markdown
        )
        assert "docs/" not in markdown


class TestShowDocumentationPage:
    """Tests for the documentation hub renderer."""

    @patch("src.web.pages.documentation.st")
    def test_renders_two_guide_sections(self, mock_st: MagicMock) -> None:
        # [test->req~ring5.workspace.documentation-hub~1]
        from src.web.pages.documentation import show_documentation_page

        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        show_documentation_page()

        markdown = " ".join(call.args[0] for call in mock_st.markdown.call_args_list)
        assert "Analysis workflows" in markdown
        assert "Developer Guide" in markdown
        assert "Engineering Reference" not in markdown

    @patch("src.web.pages.documentation.st")
    def test_cards_use_canonical_published_routes(self, mock_st: MagicMock) -> None:
        from src.web.pages.documentation import show_documentation_page

        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        show_documentation_page()

        markdown = " ".join(call.args[0] for call in mock_st.markdown.call_args_list)
        assert "https://nikiitin.github.io/RING-5/user-guide/workflows/loading-data/" in markdown
        assert "https://nikiitin.github.io/RING-5/developer-guide/architecture/" in markdown
        assert ".md" not in markdown
        assert "user-guide/features/" not in markdown

    @patch("src.web.pages.documentation.st")
    def test_uses_two_column_card_grids(self, mock_st: MagicMock) -> None:
        from src.web.pages.documentation import show_documentation_page

        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        show_documentation_page()

        assert mock_st.columns.call_count == 4
        mock_st.columns.assert_called_with(2)
