"""
Coverage tests for UploadComponents, shaper_config, PipelinePresenter,
PipelineStepPresenter, DataManager, and StyleManager.

Targets uncovered lines:
- upload_components.py: 26-35, 47-76, 88-100
- shaper_config.py: 122-134
- pipeline_presenter.py: 49, 116
- pipeline_step_presenter.py: 130-132
- data_manager.py: 25, 30
- manager.py: 90, 100
"""

from typing import Any, List
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _columns_side_effect(*args: Any, **kwargs: Any) -> List[MagicMock]:
    n = args[0] if args else kwargs.get("spec", 2)
    count = len(n) if isinstance(n, list) else n
    return [MagicMock() for _ in range(count)]


def _make_mock_api() -> MagicMock:
    api = MagicMock()
    api.state_manager = MagicMock()
    return api


# ===========================================================================
# UploadComponents
# ===========================================================================


class TestUploadComponentsParsedPreview:
    """Lines 26-35: render_parsed_data_preview."""

    @patch("src.web.pages.ui.components.upload_components.DataComponents")
    @patch("src.web.pages.ui.components.upload_components.st")
    def test_with_data(self, mock_st: MagicMock, mock_dc: MagicMock) -> None:
        from src.web.pages.ui.components.upload_components import UploadComponents

        api = _make_mock_api()
        df = pd.DataFrame({"a": [1, 2]})
        api.state_manager.get_data.return_value = df

        UploadComponents.render_parsed_data_preview(api)

        mock_st.markdown.assert_called()
        mock_st.success.assert_called()
        mock_dc.show_data_preview.assert_called_once_with(df)
        mock_dc.show_column_details.assert_called_once_with(df)
        mock_st.info.assert_called()

    @patch("src.web.pages.ui.components.upload_components.DataComponents")
    @patch("src.web.pages.ui.components.upload_components.st")
    def test_no_data(self, mock_st: MagicMock, mock_dc: MagicMock) -> None:
        from src.web.pages.ui.components.upload_components import UploadComponents

        api = _make_mock_api()
        api.state_manager.get_data.return_value = None

        UploadComponents.render_parsed_data_preview(api)

        mock_dc.show_data_preview.assert_not_called()


class TestUploadComponentsFileUpload:
    """Lines 47-76: render_file_upload_tab."""

    @patch("src.web.pages.ui.components.upload_components.DataComponents")
    @patch("src.web.pages.ui.components.upload_components.sanitize_filename", return_value="f.csv")
    @patch("src.web.pages.ui.components.upload_components.st")
    def test_successful_upload(
        self, mock_st: MagicMock, mock_san: MagicMock, mock_dc: MagicMock
    ) -> None:
        from src.web.pages.ui.components.upload_components import UploadComponents

        api = _make_mock_api()
        api.state_manager.get_temp_dir.return_value = "/tmp/dir"
        df = pd.DataFrame({"a": [1]})
        api.state_manager.get_data.return_value = df

        uploaded = MagicMock()
        uploaded.name = "file.csv"
        uploaded.getbuffer.return_value = b"a\n1"
        mock_st.file_uploader.return_value = uploaded

        with patch("builtins.open", MagicMock()):
            UploadComponents.render_file_upload_tab(api)

        api.load_data.assert_called_once()
        mock_st.success.assert_called()

    @patch("src.web.pages.ui.components.upload_components.st")
    def test_upload_no_file(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.components.upload_components import UploadComponents

        api = _make_mock_api()
        mock_st.file_uploader.return_value = None

        UploadComponents.render_file_upload_tab(api)
        api.load_data.assert_not_called()

    @patch("src.web.pages.ui.components.upload_components.sanitize_filename", return_value="f.csv")
    @patch("src.web.pages.ui.components.upload_components.st")
    def test_upload_error(self, mock_st: MagicMock, mock_san: MagicMock) -> None:
        from src.web.pages.ui.components.upload_components import UploadComponents

        api = _make_mock_api()
        api.state_manager.get_temp_dir.return_value = "/tmp/dir"
        api.load_data.side_effect = Exception("fail")

        uploaded = MagicMock()
        uploaded.name = "f.csv"
        uploaded.getbuffer.return_value = b"x"
        mock_st.file_uploader.return_value = uploaded

        with patch("builtins.open", MagicMock()):
            UploadComponents.render_file_upload_tab(api)

        mock_st.error.assert_called()

    @patch("src.web.pages.ui.components.upload_components.sanitize_filename", return_value="f.csv")
    @patch("src.web.pages.ui.components.upload_components.st")
    def test_upload_no_temp_dir_created(self, mock_st: MagicMock, mock_san: MagicMock) -> None:
        """Cover the branch where temp dir creation fails (get_temp_dir returns None twice)."""
        from src.web.pages.ui.components.upload_components import UploadComponents

        api = _make_mock_api()
        # First call: None → triggers set_temp_dir, second call: still None → RuntimeError
        api.state_manager.get_temp_dir.return_value = None

        uploaded = MagicMock()
        uploaded.name = "f.csv"
        uploaded.getbuffer.return_value = b"x"
        mock_st.file_uploader.return_value = uploaded

        with patch("src.web.pages.ui.components.upload_components.tempfile") as mock_tmp:
            mock_tmp.mkdtemp.return_value = "/tmp/new"
            # After set_temp_dir, second call still returns None
            api.state_manager.get_temp_dir.side_effect = [None, None]

            UploadComponents.render_file_upload_tab(api)

        mock_st.error.assert_called()


class TestUploadComponentsPasteData:
    """Lines 88-100: render_paste_data_tab."""

    @patch("src.web.pages.ui.components.upload_components.st")
    def test_paste_no_text(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.components.upload_components import UploadComponents

        api = _make_mock_api()
        mock_st.text_area.return_value = ""

        UploadComponents.render_paste_data_tab(api)
        api.state_manager.set_data.assert_not_called()

    @patch("src.web.pages.ui.components.upload_components.st")
    def test_paste_success(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.components.upload_components import UploadComponents

        api = _make_mock_api()
        mock_st.text_area.return_value = "a,b\n1,2\n3,4"
        mock_st.button.return_value = True

        UploadComponents.render_paste_data_tab(api)

        api.state_manager.set_data.assert_called_once()
        mock_st.success.assert_called()

    @patch("src.web.pages.ui.components.upload_components.st")
    def test_paste_error(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.components.upload_components import UploadComponents

        api = _make_mock_api()
        mock_st.text_area.return_value = "not valid csv at all \\x00"
        mock_st.button.return_value = True

        # Force pd.read_csv to fail
        with patch(
            "src.web.pages.ui.components.upload_components.pd.read_csv",
            side_effect=Exception("bad"),
        ):
            UploadComponents.render_paste_data_tab(api)

        mock_st.error.assert_called()

    @patch("src.web.pages.ui.components.upload_components.st")
    def test_paste_button_not_clicked(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.components.upload_components import UploadComponents

        api = _make_mock_api()
        mock_st.text_area.return_value = "a,b\n1,2"
        mock_st.button.return_value = False

        UploadComponents.render_paste_data_tab(api)
        api.state_manager.set_data.assert_not_called()


# ===========================================================================
# shaper_config.py
# ===========================================================================


class TestShaperConfigBranches:
    """Lines 122-134: configure_shaper error + unknown type."""

    @patch("src.web.pages.ui.shaper_config.st")
    def test_configure_unknown_shaper_type(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.shaper_config import configure_shaper

        df = pd.DataFrame({"a": [1]})
        result = configure_shaper("unknownType", df, "s1", None)

        assert result["type"] == "unknownType"

    @patch("src.web.pages.ui.shaper_config.st")
    @patch("src.web.pages.ui.shaper_config.ColumnSelectorConfig")
    def test_configure_error_handling(self, mock_cs: MagicMock, mock_st: MagicMock) -> None:
        from src.web.pages.ui.shaper_config import configure_shaper

        mock_cs.render.side_effect = RuntimeError("boom")
        df = pd.DataFrame({"a": [1]})

        result = configure_shaper("columnSelector", df, "s1", None)

        mock_st.error.assert_called()
        assert result["type"] == "columnSelector"


class TestShaperApplyBranches:
    """Additional shaper_config.apply_shapers branches."""

    @patch("src.web.pages.ui.shaper_config.st")
    def test_apply_none_data_raises(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.shaper_config import apply_shapers

        with pytest.raises(ValueError, match="Cannot apply shapers to None"):
            apply_shapers(None, [])  # type: ignore[arg-type]

    @patch("src.web.pages.ui.shaper_config.st")
    def test_apply_skip_no_type(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.shaper_config import apply_shapers

        df = pd.DataFrame({"a": [1]})
        result = apply_shapers(df, [{}])  # no type key
        pd.testing.assert_frame_equal(result, df)

    @patch("src.web.pages.ui.shaper_config.st")
    def test_apply_incomplete_config_warns(self, mock_st: MagicMock) -> None:
        from src.web.pages.ui.shaper_config import apply_shapers

        df = pd.DataFrame({"a": [1]})
        # normalize requires normalizeVars, normalizerColumn, etc.
        result = apply_shapers(df, [{"type": "normalize"}])

        mock_st.warning.assert_called()
        pd.testing.assert_frame_equal(result, df)


# ===========================================================================
# PipelinePresenter
# ===========================================================================


class TestPipelinePresenterBranches:
    """Lines 49 (render_add_shaper), 116 (render_finalize_button)."""

    @patch("src.web.presenters.plot.pipeline_presenter.st")
    def test_render_add_shaper(self, mock_st: MagicMock) -> None:
        from src.web.presenters.plot.pipeline_presenter import PipelinePresenter

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.return_value = "Sort"
        mock_st.button.return_value = True

        result = PipelinePresenter.render_add_shaper(plot_id=1)

        assert result["add_clicked"] is True
        assert result["shaper_type"] == "sort"

    @patch("src.web.presenters.plot.pipeline_presenter.st")
    def test_render_finalize_button(self, mock_st: MagicMock) -> None:
        from src.web.presenters.plot.pipeline_presenter import PipelinePresenter

        mock_st.button.return_value = True
        assert PipelinePresenter.render_finalize_button(plot_id=1) is True

    @patch("src.web.presenters.plot.pipeline_presenter.st")
    def test_render_shaper_controls(self, mock_st: MagicMock) -> None:
        from src.web.presenters.plot.pipeline_presenter import PipelinePresenter

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = False

        result = PipelinePresenter.render_shaper_controls(
            plot_id=1, idx=0, shaper_type="sort", is_first=False, is_last=False
        )

        assert "move_up" in result
        assert "move_down" in result
        assert "delete" in result


# ===========================================================================
# PipelineStepPresenter
# ===========================================================================


class TestPipelineStepPresenterBranches:
    """Lines 130-132: render_finalize_result, render_finalize_error."""

    @patch("src.web.presenters.plot.pipeline_step_presenter.st")
    def test_render_finalize_result(self, mock_st: MagicMock) -> None:
        from src.web.presenters.plot.pipeline_step_presenter import PipelineStepPresenter

        df = pd.DataFrame({"a": [1, 2, 3]})
        PipelineStepPresenter.render_finalize_result(df)

        mock_st.success.assert_called()
        mock_st.dataframe.assert_called()

    @patch("src.web.presenters.plot.pipeline_step_presenter.st")
    def test_render_finalize_error(self, mock_st: MagicMock) -> None:
        from src.web.presenters.plot.pipeline_step_presenter import PipelineStepPresenter

        PipelineStepPresenter.render_finalize_error("some error")
        mock_st.error.assert_called_once()


# ===========================================================================
# DataManager base class (lines 25, 30)
# ===========================================================================


class TestDataManagerBase:
    """Cover get_data / set_data methods."""

    def test_get_data(self) -> None:
        from src.web.pages.ui.data_managers.data_manager import DataManager

        api = _make_mock_api()
        api.state_manager.get_data.return_value = pd.DataFrame({"x": [1]})

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
        from src.web.pages.ui.data_managers.data_manager import DataManager

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


# ===========================================================================
# StyleManager (lines 90, 100)
# ===========================================================================


class TestStyleManagerBranches:
    """Cover render_series_renaming_ui and render_xaxis_labels_ui."""

    @patch("src.web.pages.ui.plotting.styles.manager.StyleUIFactory")
    def test_render_series_renaming_ui(self, mock_factory: MagicMock) -> None:
        from src.web.pages.ui.plotting.styles.manager import StyleManager

        mock_ui = MagicMock()
        mock_ui.render_series_renaming_ui.return_value = {"name": "val"}
        mock_factory.get_strategy.return_value = mock_ui

        mgr = StyleManager(plot_id=1, plot_type="bar")
        result = mgr.render_series_renaming_ui(saved_config={}, data=None, items=["a"])

        assert result == {"name": "val"}
        mock_ui.render_series_renaming_ui.assert_called_once()

    @patch("src.web.pages.ui.plotting.styles.manager.StyleUIFactory")
    def test_render_xaxis_labels_ui(self, mock_factory: MagicMock) -> None:
        from src.web.pages.ui.plotting.styles.manager import StyleManager

        mock_ui = MagicMock()
        mock_ui.render_xaxis_labels_ui.return_value = {"x": "label"}
        mock_factory.get_strategy.return_value = mock_ui

        mgr = StyleManager(plot_id=1, plot_type="bar")
        result = mgr.render_xaxis_labels_ui(saved_config={})

        assert result == {"x": "label"}
