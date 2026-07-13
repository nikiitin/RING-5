"""Tests for ordering_settings component."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tests.conftest import columns_side_effect


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Sample DataFrame for ordering tests."""
    return pd.DataFrame(
        {
            "benchmark": ["bzip2", "gcc", "mcf", "bzip2", "gcc", "mcf"],
            "config": ["base", "base", "base", "opt", "opt", "opt"],
            "color_col": ["A", "B", "A", "B", "A", "B"],
            "value": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
    )


@pytest.fixture
def mock_st() -> Generator[MagicMock]:
    """Mock Streamlit for ordering_settings."""
    with (
        patch("src.web.components.plotting.settings.ordering_settings.st") as m_st,
        patch("src.web.components.common.reorderable_list.st", m_st),
    ):
        m_st.columns.side_effect = columns_side_effect
        m_st.expander.return_value.__enter__ = MagicMock(return_value=MagicMock())
        m_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        m_st.session_state = {}
        yield m_st


class TestRenderOrderingUi:
    """Tests for ``render_ordering_ui``."""

    def test_no_x_column_skips_xaxis_section(
        self, mock_st: MagicMock, sample_data: pd.DataFrame
    ) -> None:
        """When saved_config has no 'x' key, x-axis ordering is skipped."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        config: dict[str, Any] = {}
        render_ordering_ui(
            plot_id=1,
            saved_config={},
            data=sample_data,
            config=config,
        )
        assert "xaxis_order" not in config

    def test_x_column_populates_xaxis_order(
        self, mock_st: MagicMock, sample_data: pd.DataFrame
    ) -> None:
        """When saved_config has 'x' matching a column, ordering appears."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        config: dict[str, Any] = {}
        render_ordering_ui(
            plot_id=1,
            saved_config={"x": "benchmark"},
            data=sample_data,
            config=config,
        )
        # Should set xaxis_order
        assert "xaxis_order" in config

    def test_group_column_populates_group_order(
        self, mock_st: MagicMock, sample_data: pd.DataFrame
    ) -> None:
        """When saved_config has 'group' matching a column, group ordering appears."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        config: dict[str, Any] = {}
        render_ordering_ui(
            plot_id=1,
            saved_config={"group": "config"},
            data=sample_data,
            config=config,
        )
        assert "group_order" in config

    def test_color_column_populates_legend_order(
        self, mock_st: MagicMock, sample_data: pd.DataFrame
    ) -> None:
        """When saved_config has 'color' matching a column, legend ordering appears."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        config: dict[str, Any] = {}
        render_ordering_ui(
            plot_id=1,
            saved_config={"color": "color_col"},
            data=sample_data,
            config=config,
        )
        assert "legend_order" in config

    def test_nonexistent_x_column_skips(
        self, mock_st: MagicMock, sample_data: pd.DataFrame
    ) -> None:
        """x column not in DataFrame should skip x-axis ordering."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        config: dict[str, Any] = {}
        render_ordering_ui(
            plot_id=1,
            saved_config={"x": "nonexistent_col"},
            data=sample_data,
            config=config,
        )
        assert "xaxis_order" not in config

    def test_all_sections_rendered(self, mock_st: MagicMock, sample_data: pd.DataFrame) -> None:
        """All three ordering sections when all columns present."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        config: dict[str, Any] = {}
        render_ordering_ui(
            plot_id=1,
            saved_config={
                "x": "benchmark",
                "group": "config",
                "color": "color_col",
            },
            data=sample_data,
            config=config,
        )
        assert "xaxis_order" in config
        assert "group_order" in config
        assert "legend_order" in config

    def test_markdown_header_rendered(self, mock_st: MagicMock, sample_data: pd.DataFrame) -> None:
        """Should render the 'Ordering Control' header."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        render_ordering_ui(
            plot_id=1,
            saved_config={},
            data=sample_data,
            config={},
        )
        mock_st.markdown.assert_called_with("#### Ordering Control")
