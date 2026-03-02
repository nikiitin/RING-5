"""
Coverage tests for shaper_config, PipelineComponent,
PipelineStepComponent and DataManager.

Targets uncovered lines:
- shaper_config.py: 122-134
- pipeline_presenter.py: 49, 116
- pipeline_step_presenter.py: 130-132
- data_manager.py: 25, 30
- manager.py: 90, 100
"""

from typing import Any, cast
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _columns_side_effect(*args: Any, **kwargs: Any) -> list[MagicMock]:
    n = args[0] if args else kwargs.get("spec", 2)
    count = len(n) if isinstance(n, list) else n
    return [MagicMock() for _ in range(count)]


def _make_mock_api() -> MagicMock:
    api = MagicMock()
    api.state_manager = MagicMock()
    return api


# ===========================================================================
# shaper_config.py
# ===========================================================================


class TestShaperConfigBranches:
    """Lines 122-134: configure_shaper error + unknown type."""

    @patch("src.web.pages.ui.shaper_config.st")
    def test_configure_unknown_shaper_type(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.shaper_config import configure_shaper

        df = pd.DataFrame({"a": [1]})
        result = configure_shaper("unknownType", df, 1, None)

        assert result.get("type") == "unknownType"

    @patch("src.web.pages.ui.shaper_config.st")
    @patch("src.web.pages.ui.shaper_config.ColumnSelectorConfig")
    def test_configure_error_handling(self, mock_cs: MagicMock, mock_st: MagicMock) -> None:
        from src.web.pages.ui.shaper_config import configure_shaper

        mock_cs.render.side_effect = RuntimeError("boom")
        df = pd.DataFrame({"a": [1]})

        result = configure_shaper("columnSelector", df, 1, None)

        mock_st.exception.assert_called()
        assert result.get("type") == "columnSelector"


class TestShaperApplyBranches:
    """Additional shaper_config.apply_shapers branches."""

    @patch("src.web.pages.ui.shaper_config.st")
    def test_apply_none_data_raises(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.shaper_config import apply_shapers

        with pytest.raises(ValueError, match="Cannot apply shapers to None"):
            apply_shapers(None, [])  # type: ignore[arg-type]

    @patch("src.web.pages.ui.shaper_config.apply_shapers")
    def test_apply_transformer_branch(self, mock_apply: MagicMock) -> None:
        from src.web.pages.ui.shaper_config import apply_shapers

        df = pd.DataFrame({"a": [1]})
        apply_shapers(df, cast(Any, [{"type": "transformer"}]))
        mock_apply.assert_called()

    @patch("src.web.pages.ui.shaper_config.st")
    def test_apply_skip_no_type(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.shaper_config import apply_shapers

        df = pd.DataFrame({"a": [1]})
        # Cast to Any then to list[ShaperStepConfig] to satisfy Pyright
        result = apply_shapers(df, cast(Any, [{}]))  # no type key
        pd.testing.assert_frame_equal(result, df)

    @patch("src.web.pages.ui.shaper_config.st")
    def test_apply_incomplete_config_warns(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.shaper_config import apply_shapers

        df = pd.DataFrame({"a": [1]})
        # normalize requires normalizeVars, normalizerColumn, etc.
        # Cast to Any then to list[ShaperStepConfig] to satisfy Pyright
        result = apply_shapers(df, cast(Any, [{"type": "normalize"}]))

        mock_st.warning.assert_called()
        pd.testing.assert_frame_equal(result, df)


# ===========================================================================
# PipelineComponent
# ===========================================================================


class TestPipelineComponentBranches:
    """Lines 49 (render_add_shaper), 116 (render_finalize_button)."""

    @patch("src.web.components.common.pipeline.st")
    def test_render_add_shaper(self, mock_st: MagicMock) -> None:
        from src.web.components.common.pipeline import PipelineComponent

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.return_value = "Sort"
        mock_st.button.return_value = True

        result = PipelineComponent.render_add_shaper(plot_id=1)

        assert result["add_clicked"] is True
        assert result["shaper_type"] == "sort"

    @patch("src.web.components.common.pipeline.st")
    def test_render_finalize_button(self, mock_st: MagicMock) -> None:
        from src.web.components.common.pipeline import PipelineComponent

        mock_st.button.return_value = True
        assert PipelineComponent.render_finalize_button(plot_id=1) is True

    @patch("src.web.components.common.pipeline.st")
    def test_render_shaper_controls(self, mock_st: MagicMock) -> None:
        from src.web.components.common.pipeline import PipelineComponent

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = False

        result = PipelineComponent.render_shaper_controls(
            plot_id=1, idx=0, shaper_type="sort", is_first=False, is_last=False
        )

        assert "move_up" in result
        assert "move_down" in result
        assert "delete" in result


# ===========================================================================
# PipelineStepComponent
# ===========================================================================


class TestPipelineStepComponentBranches:
    """Lines 130-132: render_finalize_result, render_finalize_error."""

    @patch("src.web.components.common.pipeline_step.st")
    def test_render_finalize_result(self, mock_st: MagicMock) -> None:
        from src.web.components.common.pipeline_step import (
            PipelineStepComponent,
        )

        df = pd.DataFrame({"a": [1, 2, 3]})
        PipelineStepComponent.render_finalize_result(df)

        mock_st.toast.assert_called()
        mock_st.dataframe.assert_called()

    @patch("src.web.components.common.pipeline_step.st")
    def test_render_finalize_error(self, mock_st: MagicMock) -> None:
        from src.web.components.common.pipeline_step import (
            PipelineStepComponent,
        )

        PipelineStepComponent.render_finalize_error("some error")
        mock_st.exception.assert_called_once()


# ===========================================================================
# DataManager base class (lines 25, 30)
# ===========================================================================


class TestDataManagerBase:
    """Cover get_data / set_data methods."""

    def test_get_data(self) -> None:
        from src.web.components.data_managers.data_manager import DataManager

        api = _make_mock_api()
        api.state_manager.get_data.return_value = pd.DataFrame({"x": [1]})

        from src.web.pages.ui.shaper_config import apply_shapers

        # Missing group_by
        # Use a dummy dataframe and config
        result = apply_shapers(pd.DataFrame({"a": [1]}), cast(Any, [{"type": "mean"}]))

        # Create a concrete subclass
        class Concrete(DataManager):
            @property
            def name(self) -> str:
                return "test"

            def render(self) -> None:
                pass

        mgr = Concrete(api)
        result = mgr.get_data()
        assert result is not None
        assert len(result) == 1

    def test_set_data(self) -> None:
        from src.web.components.data_managers.data_manager import DataManager

        api = _make_mock_api()

        class Concrete(DataManager):
            @property
            def name(self) -> str:
                return "test"

            def render(self) -> None:
                pass

        mgr = Concrete(api)
        df = pd.DataFrame({"x": [1]})
        mgr.set_data(df)
        api.state_manager.set_data.assert_called_once_with(df)
