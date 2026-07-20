"""Tests for shaper configuration, pipeline components, and data management."""

from typing import Any, cast
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


def _columns_side_effect(*args: Any, **kwargs: Any) -> list[MagicMock]:
    n = args[0] if args else kwargs.get("spec", 2)
    count = len(n) if isinstance(n, list) else n
    return [MagicMock() for _ in range(count)]


def _make_mock_api() -> MagicMock:
    api = MagicMock()
    api.state_manager = MagicMock()
    return api


class TestShaperConfig:
    """Tests for shaper selection and validation."""

    @patch("src.web.pages.ui.shaper_config.st")
    def test_configure_unknown_shaper_type(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.shaper_config import configure_shaper

        df = pd.DataFrame({"a": [1]})
        result = configure_shaper("unknownType", df, 1, None)

        assert result.get("type") == "unknownType"

    @patch("src.web.pages.ui.shaper_config.st")
    def test_configure_error_handling(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.shaper_config import CONFIG_DISPATCH, configure_shaper

        mock_render = MagicMock(side_effect=RuntimeError("boom"))
        df = pd.DataFrame({"a": [1]})

        with patch.dict(CONFIG_DISPATCH, {"columnSelector": mock_render}):
            result = configure_shaper("columnSelector", df, 1, None)

        mock_st.exception.assert_called()
        assert result.get("type") == "columnSelector"


class TestShaperApplication:
    """Tests for applying shaper configurations."""

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


class TestPipelineComponent:
    """Tests for pipeline controls and finalization."""

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

    @patch("src.web.components.common.pipeline.st")
    def test_render_exchange_returns_upload_and_renders_download(self, mock_st: MagicMock) -> None:
        from src.web.components.common.pipeline import PipelineComponent

        uploaded = MagicMock()
        uploaded.getvalue.return_value = b'{"format":"ring5.pipeline-configuration"}'
        mock_st.text_input.return_value = "Paper pipeline"
        mock_st.text_area.return_value = "Reviewed"
        mock_st.file_uploader.return_value = uploaded
        mock_st.selectbox.return_value = "rename"
        mock_st.button.return_value = True
        export_fn = MagicMock(return_value=b"{}")

        result = PipelineComponent.render_exchange(1, "Plot", export_fn)

        export_fn.assert_called_once_with("Paper pipeline", "Reviewed")
        mock_st.download_button.assert_called_once()
        assert result == {
            "import_clicked": True,
            "payload": b'{"format":"ring5.pipeline-configuration"}',
            "conflict": "rename",
        }


class TestPipelineStepComponent:
    """Tests for pipeline-step result reporting."""

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


class TestDataManagerBase:
    """Tests for stored dataframe access."""

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
        api.update_selected_dataset.assert_called_once_with(df, operation="Update dataset")
