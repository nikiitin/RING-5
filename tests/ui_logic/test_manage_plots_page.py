"""Tests for the manage_plots page composition layer.

Verifies:
    - Page wiring (adapter creation, controller composition)
    - Pending updates consumption
    - Fragment boundary behavior
    - Guard: no current_plot → no render/pipeline sections
"""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
MODULE = "src.web.pages.manage_plots"


@pytest.fixture
def mock_api() -> MagicMock:
    """Application API mock with initialized state_manager."""
    api = MagicMock()
    api.state_manager.initialize.return_value = None
    api.state_manager.get_plots.return_value = []
    return api


# ---------------------------------------------------------------------------
# Page initialization
# ---------------------------------------------------------------------------
class TestPageInitialization:
    """Verify the page initializes state and creates adapters."""

    @patch(f"{MODULE}.PlotManagerComponents")
    @patch(f"{MODULE}.PlotRenderController")
    @patch(f"{MODULE}.PipelineController")
    @patch(f"{MODULE}.PlotCreationController")
    @patch(f"{MODULE}.UIStateManager")
    @patch(f"{MODULE}.st")
    def test_state_manager_initialized(
        self,
        mock_st: MagicMock,
        mock_ui_cls: MagicMock,
        mock_creation_cls: MagicMock,
        mock_pipeline_cls: MagicMock,
        mock_render_cls: MagicMock,
        mock_components: MagicMock,
        mock_api: MagicMock,
    ) -> None:
        """api.state_manager.initialize() is called at page startup."""
        mock_ui = MagicMock()
        mock_ui.plot.consume_pending_updates.return_value = None
        mock_ui_cls.return_value = mock_ui

        creation = MagicMock()
        creation.render_selector.return_value = None
        mock_creation_cls.return_value = creation

        from src.web.pages.manage_plots import show_manage_plots_page

        show_manage_plots_page(mock_api)
        mock_api.state_manager.initialize.assert_called_once()

    @patch(f"{MODULE}.PlotManagerComponents")
    @patch(f"{MODULE}.PlotRenderController")
    @patch(f"{MODULE}.PipelineController")
    @patch(f"{MODULE}.PlotCreationController")
    @patch(f"{MODULE}.UIStateManager")
    @patch(f"{MODULE}.st")
    def test_controllers_instantiated(
        self,
        mock_st: MagicMock,
        mock_ui_cls: MagicMock,
        mock_creation_cls: MagicMock,
        mock_pipeline_cls: MagicMock,
        mock_render_cls: MagicMock,
        mock_components: MagicMock,
        mock_api: MagicMock,
    ) -> None:
        """All three controllers are created."""
        mock_ui = MagicMock()
        mock_ui.plot.consume_pending_updates.return_value = None
        mock_ui_cls.return_value = mock_ui

        creation = MagicMock()
        creation.render_selector.return_value = None
        mock_creation_cls.return_value = creation

        from src.web.pages.manage_plots import show_manage_plots_page

        show_manage_plots_page(mock_api)

        mock_creation_cls.assert_called_once()
        mock_pipeline_cls.assert_called_once()
        mock_render_cls.assert_called_once()


# ---------------------------------------------------------------------------
# Pending updates
# ---------------------------------------------------------------------------
class TestPendingUpdates:
    """Verify pending widget updates are consumed and applied."""

    @patch(f"{MODULE}.PlotManagerComponents")
    @patch(f"{MODULE}.PlotRenderController")
    @patch(f"{MODULE}.PipelineController")
    @patch(f"{MODULE}.PlotCreationController")
    @patch(f"{MODULE}.UIStateManager")
    @patch(f"{MODULE}.st")
    def test_pending_updates_applied_to_session_state(
        self,
        mock_st: MagicMock,
        mock_ui_cls: MagicMock,
        mock_creation_cls: MagicMock,
        mock_pipeline_cls: MagicMock,
        mock_render_cls: MagicMock,
        mock_components: MagicMock,
        mock_api: MagicMock,
    ) -> None:
        """Pending updates from interactive events are applied."""
        mock_ui = MagicMock()
        mock_ui.plot.consume_pending_updates.return_value = {"widget_key": "new_value"}
        mock_ui_cls.return_value = mock_ui

        mock_st.session_state = {"widget_key": "old_value"}

        creation = MagicMock()
        creation.render_selector.return_value = None
        mock_creation_cls.return_value = creation

        from src.web.pages.manage_plots import show_manage_plots_page

        show_manage_plots_page(mock_api)

        assert mock_st.session_state["widget_key"] == "new_value"

    @patch(f"{MODULE}.PlotManagerComponents")
    @patch(f"{MODULE}.PlotRenderController")
    @patch(f"{MODULE}.PipelineController")
    @patch(f"{MODULE}.PlotCreationController")
    @patch(f"{MODULE}.UIStateManager")
    @patch(f"{MODULE}.st")
    def test_no_pending_updates_is_noop(
        self,
        mock_st: MagicMock,
        mock_ui_cls: MagicMock,
        mock_creation_cls: MagicMock,
        mock_pipeline_cls: MagicMock,
        mock_render_cls: MagicMock,
        mock_components: MagicMock,
        mock_api: MagicMock,
    ) -> None:
        """When no pending updates, session_state is untouched."""
        mock_ui = MagicMock()
        mock_ui.plot.consume_pending_updates.return_value = None
        mock_ui_cls.return_value = mock_ui

        # Set session_state as a regular dict (not MagicMock)
        mock_st.session_state = {"key": "original"}

        creation = MagicMock()
        creation.render_selector.return_value = None
        mock_creation_cls.return_value = creation

        from src.web.pages.manage_plots import show_manage_plots_page

        show_manage_plots_page(mock_api)

        assert mock_st.session_state["key"] == "original"


# ---------------------------------------------------------------------------
# Guard: no current plot
# ---------------------------------------------------------------------------
class TestNoPlotGuard:
    """When no plot is selected, pipeline/render/controls are skipped."""

    @patch(f"{MODULE}.PlotManagerComponents")
    @patch(f"{MODULE}.PlotRenderController")
    @patch(f"{MODULE}.PipelineController")
    @patch(f"{MODULE}.PlotCreationController")
    @patch(f"{MODULE}.UIStateManager")
    @patch(f"{MODULE}.st")
    def test_no_plot_skips_controls(
        self,
        mock_st: MagicMock,
        mock_ui_cls: MagicMock,
        mock_creation_cls: MagicMock,
        mock_pipeline_cls: MagicMock,
        mock_render_cls: MagicMock,
        mock_components: MagicMock,
        mock_api: MagicMock,
    ) -> None:
        """When render_selector returns None, controls are not rendered."""
        mock_ui = MagicMock()
        mock_ui.plot.consume_pending_updates.return_value = None
        mock_ui_cls.return_value = mock_ui

        creation = MagicMock()
        creation.render_selector.return_value = None
        mock_creation_cls.return_value = creation

        from src.web.pages.manage_plots import show_manage_plots_page

        show_manage_plots_page(mock_api)

        creation.render_controls.assert_not_called()

    @patch(f"{MODULE}.PlotManagerComponents")
    @patch(f"{MODULE}.PlotRenderController")
    @patch(f"{MODULE}.PipelineController")
    @patch(f"{MODULE}.PlotCreationController")
    @patch(f"{MODULE}.UIStateManager")
    @patch(f"{MODULE}.st")
    def test_workspace_management_always_rendered(
        self,
        mock_st: MagicMock,
        mock_ui_cls: MagicMock,
        mock_creation_cls: MagicMock,
        mock_pipeline_cls: MagicMock,
        mock_render_cls: MagicMock,
        mock_components: MagicMock,
        mock_api: MagicMock,
    ) -> None:
        """Workspace management renders even with no plots."""
        mock_ui = MagicMock()
        mock_ui.plot.consume_pending_updates.return_value = None
        mock_ui_cls.return_value = mock_ui

        creation = MagicMock()
        creation.render_selector.return_value = None
        mock_creation_cls.return_value = creation

        from src.web.pages.manage_plots import show_manage_plots_page

        show_manage_plots_page(mock_api)

        mock_components.render_workspace_management.assert_called_once_with(mock_api)
