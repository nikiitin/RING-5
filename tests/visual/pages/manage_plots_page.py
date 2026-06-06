"""Page Object for the Manage Plots page.

Covers:
- Plot creation form
- Plot selector pills
- Plot controls (rename, save/load pipeline, delete, duplicate)
- Shaper pipeline editor (add/remove/reorder transformations)
- Pipeline step configuration & preview
- Visualization section (config, chart, engine selector)
- Download section
- Workspace management
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from tests.visual.pages.base_page import BasePage

# Available plot types (selectbox options — raw factory keys)
PLOT_TYPES: tuple[str, ...] = (
    "bar",
    "dual_axis_bar_dot",
    "grouped_bar",
    "stacked_bar",
    "grouped_stacked_bar",
    "histogram",
    "line",
    "scatter",
)

# Available shapers (Add transformation selectbox options)
SHAPER_TYPES: tuple[str, ...] = (
    "Column Selector",
    "Sort",
    "Mean Calculator",
    "Normalize",
    "Filter",
    "Split-Apply (Per-Axis)",
    "Transformer",
)


class ManagePlotsPage(BasePage):
    """POM for the *Manage Plots* page.

    Covers: plot creation, selector pills, controls row,
    pipeline editor, visualization / config / chart, download,
    and workspace management.
    """

    PAGE_NAME: str = "Manage Plots"

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _by_label(self, test_id: str, label_text: str) -> Locator:
        """Return a widget locator filtered by its visible label text.

        Streamlit can render multiple widgets with the same
        ``data-testid`` in different sections; filtering by label
        prevents ambiguity.
        """
        return self.page.locator(f"[data-testid='{test_id}']").filter(has_text=label_text)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(self) -> None:
        """Open the Manage Plots page via sidebar."""
        self.navigate_to(self.PAGE_NAME)

    # ==================================================================
    #  1. Page-level locators
    # ==================================================================

    @property
    def page_header(self) -> Locator:
        """The 'Manage Plots' heading (scoped to main content)."""
        return self.page.locator("[data-testid='stMainBlockContainer']").get_by_text("Manage Plots")

    # ==================================================================
    #  2. Create Plot form
    # ==================================================================

    @property
    def plot_name_input(self) -> Locator:
        """Text input for new plot name (key=new_plot_name)."""
        return self.page.get_by_label("New plot name")

    @property
    def plot_type_selectbox(self) -> Locator:
        """Plot type selectbox inside the creation form (key=new_plot_type)."""
        return self.page.locator("[data-testid='stForm'] [data-testid='stSelectbox']")

    @property
    def create_plot_button(self) -> Locator:
        """'Create Plot' form submit button."""
        return self.page.get_by_role("button", name="Create Plot")

    # ==================================================================
    #  3. Plot selector pills
    # ==================================================================

    @property
    def plot_selector_pills(self) -> Locator:
        """The st.pills widget for selecting plots (key=plot_selector)."""
        return self.page.locator(
            "[data-testid='stMainBlockContainer'] " "[data-testid='stButtonGroup']"
        ).first

    @property
    def no_plots_warning(self) -> Locator:
        """Warning shown when no plots exist."""
        return self.page.locator("[data-testid='stAlertContentWarning']").filter(
            has_text="No plots yet"
        )

    def get_plot_pill(self, plot_name: str) -> Locator:
        """Return the pill button for a specific plot.

        Args:
            plot_name: Display name of the plot.
        """
        return self.plot_selector_pills.get_by_role("button", name=plot_name, exact=True)

    # ==================================================================
    #  4. Controls row (rename / save / load / delete / duplicate)
    # ==================================================================

    @property
    def rename_input(self) -> Locator:
        """Rename text input (key=rename_{plot_id})."""
        return self._by_label("stTextInput", "Rename plot").locator("input")

    @property
    def delete_button(self) -> Locator:
        """'Delete' plot button."""
        return self.page.get_by_role("button", name="Delete")

    @property
    def duplicate_button(self) -> Locator:
        """'Duplicate' plot button."""
        return self.page.get_by_role("button", name="Duplicate")

    # ==================================================================
    #  5. Pipeline editor (st.fragment)
    # ==================================================================

    @property
    def add_transformation_selectbox(self) -> Locator:
        """'Add transformation' selectbox (key=shaper_add_{plot_id})."""
        return self._by_label("stSelectbox", "Add transformation")

    @property
    def add_to_pipeline_button(self) -> Locator:
        """'Add to Pipeline' button."""
        return self.page.get_by_role("button", name="Add to Pipeline")

    @property
    def pipeline_steps(self) -> Locator:
        """All pipeline step expanders (numbered: '1. Sort', '2. Filter', …).

        Excludes non-pipeline expanders (e.g. Download, Advanced Options,
        View Current Data) by filtering out expanders whose summary label
        is known to be outside the pipeline section.
        """
        return (
            self.page.locator("[data-testid='stExpander']")
            .filter(has_not_text="📥 Download")
            .filter(has_not_text="Advanced Options")
            .filter(has_not_text="Theme & Style")
            .filter(has_not_text="Reorder")
            .filter(has_not_text="Rename Items")
            .filter(has_not_text="Rename X-Axis")
            .filter(has_not_text="Reference Line")
            .filter(has_not_text="Marker & Line")
            .filter(has_not_text="Add New Shape")
            .filter(has_not_text="View Current Data")
            .filter(has_not_text="Show Errors")
        )

    @property
    def finalize_button(self) -> Locator:
        """'Finalize Pipeline for Plotting' primary button."""
        return self.page.get_by_role("button", name="Finalize Pipeline for Plotting")

    def get_pipeline_step(self, index: int) -> Locator:
        """Return the *n*-th pipeline step expander (0-based).

        Args:
            index: Zero-based step index.
        """
        return self.pipeline_steps.nth(index)

    def get_step_up_button(self, index: int) -> Locator:
        """'Up' button for a specific pipeline step."""
        step = self.get_pipeline_step(index)
        return step.get_by_role("button", name="Up")

    def get_step_down_button(self, index: int) -> Locator:
        """'Down' button for a specific pipeline step."""
        step = self.get_pipeline_step(index)
        return step.get_by_role("button", name="Down")

    def get_step_delete_button(self, index: int) -> Locator:
        """'Del' button for a specific pipeline step."""
        step = self.get_pipeline_step(index)
        return step.get_by_role("button", name="Del")

    # -- Column Selector shaper widgets -------

    @property
    def column_selector_multiselect(self) -> Locator:
        """'Select columns' multiselect inside Column Selector step."""
        return self._by_label("stMultiSelect", "Select columns")

    @property
    def column_select_all_button(self) -> Locator:
        """'Select All' quick-action button (Column Selector)."""
        return self.page.get_by_role("button", name="Select All")

    @property
    def column_clear_all_button(self) -> Locator:
        """'Clear All' quick-action button (Column Selector)."""
        return self.page.get_by_role("button", name="Clear All")

    @property
    def column_numeric_only_button(self) -> Locator:
        """'Numeric Only' quick-action button (Column Selector)."""
        return self.page.get_by_role("button", name="Numeric Only")

    # -- Sort shaper widgets -------

    @property
    def sort_column_selectbox(self) -> Locator:
        """'Sort by column' selectbox."""
        return self._by_label("stSelectbox", "Sort by column")

    @property
    def sort_order_selectbox(self) -> Locator:
        """Sort order selectbox (Ascending/Descending)."""
        return self._by_label("stSelectbox", "Order")

    # -- Filter (conditionSelector) shaper widgets -------

    @property
    def filter_column_selectbox(self) -> Locator:
        """'Column' selectbox in Filter step."""
        return self._by_label("stSelectbox", "Column")

    @property
    def filter_operator_selectbox(self) -> Locator:
        """'Operator' selectbox in Filter step."""
        return self._by_label("stSelectbox", "Operator")

    @property
    def filter_value_input(self) -> Locator:
        """'Value' text input in Filter step."""
        return self._by_label("stTextInput", "Value").locator("input")

    # -- Normalize shaper widgets -------

    @property
    def normalize_column_selectbox(self) -> Locator:
        """'Column to normalize' selectbox."""
        return self._by_label("stSelectbox", "Column to normalize")

    @property
    def normalize_method_selectbox(self) -> Locator:
        """'Normalization method' selectbox."""
        return self._by_label("stSelectbox", "Normalization method")

    # -- Mean Calculator shaper widgets -------

    @property
    def mean_group_by_multiselect(self) -> Locator:
        """'Group by columns' multiselect in Mean Calculator."""
        return self._by_label("stMultiSelect", "Group by columns")

    @property
    def mean_calculate_for_multiselect(self) -> Locator:
        """'Calculate mean for' multiselect in Mean Calculator."""
        return self._by_label("stMultiSelect", "Calculate mean for")

    # -- Transformer shaper widgets -------

    @property
    def transformer_source_selectbox(self) -> Locator:
        """'Source column' selectbox in Transformer."""
        return self._by_label("stSelectbox", "Source column")

    @property
    def transformer_transformation_selectbox(self) -> Locator:
        """'Transformation' selectbox in Transformer."""
        return self._by_label("stSelectbox", "Transformation")

    @property
    def transformer_new_name_input(self) -> Locator:
        """'New column name' text input in Transformer."""
        return self._by_label("stTextInput", "New column name").locator("input")

    # ==================================================================
    #  6. Visualization section (st.fragment)
    # ==================================================================

    @property
    def viz_plot_type_selectbox(self) -> Locator:
        """'Plot Type' selectbox in visualization config (excludes creation form)."""
        # The creation form also has a "Plot type" selectbox — use .last
        # to get the config-section one (rendered below the form).
        return self._by_label("stSelectbox", "Plot Type").last

    @property
    def viz_x_axis_selectbox(self) -> Locator:
        """'X-axis' selectbox."""
        return self._by_label("stSelectbox", "X-axis")

    @property
    def viz_y_axis_selectbox(self) -> Locator:
        """'Y-axis' selectbox."""
        return self._by_label("stSelectbox", "Y-axis")

    @property
    def viz_y_bar_selectbox(self) -> Locator:
        """'Y-axis (Bars – left)' selectbox (dual-axis bar+dot plot).

        Filtered on the distinctive plural 'Bars' to avoid the en-dash and
        to not collide with the singular 'Dot Symbol'/'Dot Size' widgets.
        """
        return self._by_label("stSelectbox", "Bars")

    @property
    def viz_y_dot_selectbox(self) -> Locator:
        """'Y-axis (Dots – right)' selectbox (dual-axis bar+dot plot)."""
        return self._by_label("stSelectbox", "Dots")

    @property
    def viz_color_by_selectbox(self) -> Locator:
        """'Color by' selectbox (optional — may not be rendered)."""
        return self._by_label("stSelectbox", "Color by")

    @property
    def viz_group_by_selectbox(self) -> Locator:
        """'Group by' selectbox (for Grouped Bar)."""
        return self._by_label("stSelectbox", "Group by")

    @property
    def viz_stack_by_selectbox(self) -> Locator:
        """'Stack by' selectbox (for Stacked Bar)."""
        return self._by_label("stSelectbox", "Stack by")

    @property
    def viz_size_by_selectbox(self) -> Locator:
        """'Size by' selectbox (for Scatter)."""
        return self._by_label("stSelectbox", "Size by")

    @property
    def viz_title_input(self) -> Locator:
        """'Title' text input for the chart.

        Uses an exact-name role locator: a ``has_text='Title'`` filter also
        matches the dual-axis plot's 'Legend Title' field (strict-mode clash).
        """
        return self.page.get_by_role("textbox", name="Title", exact=True)

    @property
    def viz_x_label_input(self) -> Locator:
        """'X-axis label' text input."""
        return self._by_label("stTextInput", "X-axis label").locator("input")

    @property
    def viz_y_label_input(self) -> Locator:
        """'Y-axis label' text input."""
        return self._by_label("stTextInput", "Y-axis label").locator("input")

    @property
    def viz_auto_refresh_toggle(self) -> Locator:
        """'Auto-refresh' toggle."""
        return self.page.get_by_text("Auto-refresh")

    @property
    def viz_refresh_button(self) -> Locator:
        """'Refresh Plot' button."""
        return self.page.get_by_role("button", name="Refresh Plot")

    @property
    def viz_show_advanced_toggle(self) -> Locator:
        """'Show advanced settings' toggle."""
        return self.page.get_by_text("Show advanced settings")

    @property
    def viz_settings_pills(self) -> Locator:
        """Settings navigation pills (key=settings_nav)."""
        return self.page.locator(
            "[data-testid='stMainBlockContainer'] " "[data-testid='stButtonGroup']"
        ).filter(has_text="layout")

    @property
    def viz_engine_pills(self) -> Locator:
        """Engine selector pills (plotly / matplotlib)."""
        return self.page.locator(
            "[data-testid='stMainBlockContainer'] " "[data-testid='stButtonGroup']"
        ).filter(has_text="plotly")

    @property
    def viz_preset_pills(self) -> Locator:
        """Preset selector pills."""
        return self.page.locator(
            "[data-testid='stMainBlockContainer'] " "[data-testid='stButtonGroup']"
        ).filter(has_text="Preset")

    # -- Chart output -------

    @property
    def plotly_chart(self) -> Locator:
        """The rendered Plotly chart (custom interactive component via iframe)."""
        return self.page.locator("[data-testid='stCustomComponentV1']")

    @property
    def matplotlib_chart(self) -> Locator:
        """The rendered Matplotlib chart (st.pyplot image)."""
        return self.page.locator("[data-testid='stImage']")

    @property
    def no_processed_data_warning(self) -> Locator:
        """Warning when no processed data is available for plotting."""
        return self.page.locator("[data-testid='stAlertContentWarning']").filter(
            has_text="No processed data"
        )

    # ==================================================================
    #  7. Download section
    # ==================================================================

    @property
    def download_expander(self) -> Locator:
        """The download expander container."""
        return self.page.locator("[data-testid='stExpander']").filter(has_text="Download")

    @property
    def download_format_pills(self) -> Locator:
        """Format selector pills inside the download expander."""
        return self.download_expander.locator("[data-testid='stButtonGroup']")

    @property
    def download_button(self) -> Locator:
        """Download button inside the download expander."""
        return self.download_expander.get_by_role("button", name="Download")

    # ==================================================================
    #  8. Workspace management
    # ==================================================================

    @property
    def export_path_input(self) -> Locator:
        """'Local Download Path' text input (key=export_path_input)."""
        return self._by_label("stTextInput", "Local Download Path").locator("input")

    @property
    def force_format_selectbox(self) -> Locator:
        """'Force Format' selectbox (key=export_fmt_override)."""
        return self._by_label("stSelectbox", "Force Format")

    @property
    def download_all_button(self) -> Locator:
        """'Download All' primary button."""
        return self.page.get_by_role("button", name="Download All")

    @property
    def process_all_button(self) -> Locator:
        """'Process All Plots in Parallel' button."""
        return self.page.get_by_role("button", name="Process All Plots in Parallel")

    @property
    def save_workspace_button(self) -> Locator:
        """'Save Entire Workspace' button."""
        return self.page.get_by_role("button", name="Save Entire Workspace")

    # ==================================================================
    #  ACTIONS — Create Plot
    # ==================================================================

    def fill_plot_name(self, name: str) -> None:
        """Fill the new plot name input.

        Args:
            name: Desired plot name.
        """
        self.plot_name_input.fill(name)

    def create_plot(self, name: str, plot_type: str | None = None) -> None:
        """Fill the form and click 'Create Plot'.

        Args:
            name: Desired plot name.
            plot_type: Optional plot type label to select (e.g. "Bar Chart").
                If *None*, the default is kept.
        """
        self.plot_name_input.fill(name)
        if plot_type is not None:
            self.select_plot_type(plot_type)
        self.create_plot_button.click()
        self.wait_for_streamlit()
        # Confirm creation registered (the pill appears) before callers proceed.
        expect(self.get_plot_pill(name).first).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def _select_dropdown_option(self, option_text: str) -> None:
        """Click an option in the currently-open Streamlit selectbox dropdown.

        Streamlit renders selectbox options as ``<li>`` elements inside a
        ``[data-testid='stSelectboxVirtualDropdown']`` container. Waits for the
        option to render (rather than a fixed sleep) so it is deterministic
        under load.

        Args:
            option_text: Exact display label of the option.
        """
        option = self.page.locator("[data-testid='stSelectboxVirtualDropdown'] li").get_by_text(
            option_text, exact=True
        )
        expect(option.first).to_be_visible(timeout=self.RENDER_TIMEOUT)
        option.first.click()
        self.wait_for_streamlit()

    def _open_and_select(self, selectbox: Locator, value: str) -> None:
        """Verify-then-act: wait for a selectbox to render, open it, choose *value*.

        Waiting for the selectbox before clicking avoids racing a not-yet-rendered
        visualization fragment under load (a major source of e2e flakiness).
        """
        expect(selectbox).to_be_visible(timeout=self.RENDER_TIMEOUT)
        selectbox.click()
        self._select_dropdown_option(value)

    def select_plot_type(self, plot_type: str) -> None:
        """Select a plot type in the create-plot form selectbox, verifying it took.

        Args:
            plot_type: Exact factory key (e.g. "bar", "dual_axis_bar_dot").
        """
        self._open_and_select(self.plot_type_selectbox, plot_type)
        # Confirm the selection registered — guards the "selected dual_axis but a
        # bar plot got created" race seen under -n 3.
        expect(self.plot_type_selectbox).to_contain_text(plot_type, timeout=self.RENDER_TIMEOUT)

    # ==================================================================
    #  ACTIONS — Plot Selector
    # ==================================================================

    def select_plot(self, plot_name: str) -> None:
        """Select a plot by clicking its pill.

        Args:
            plot_name: Display name of the plot.
        """
        self.get_plot_pill(plot_name).click()
        self.wait_for_streamlit()

    # ==================================================================
    #  ACTIONS — Controls row
    # ==================================================================

    def rename_plot(self, new_name: str) -> None:
        """Rename the currently selected plot.

        Args:
            new_name: New plot name.
        """
        self.rename_input.fill(new_name)
        self.rename_input.press("Enter")
        self.wait_for_streamlit()

    def delete_plot(self) -> None:
        """Delete the currently selected plot."""
        self.delete_button.click()
        self.wait_for_streamlit()

    def duplicate_plot(self) -> None:
        """Duplicate the currently selected plot."""
        self.duplicate_button.click()
        self.wait_for_streamlit()

    # ==================================================================
    #  ACTIONS — Pipeline editor
    # ==================================================================

    def add_shaper(self, shaper_name: str) -> None:
        """Select a shaper type and click 'Add to Pipeline'.

        Args:
            shaper_name: Exact display label (e.g. "Column Selector").
        """
        self._open_and_select(self.add_transformation_selectbox, shaper_name)
        self.add_to_pipeline_button.click()
        self.wait_for_streamlit()

    def finalize_pipeline(self) -> None:
        """Click 'Finalize Pipeline for Plotting' and wait."""
        self.finalize_button.click()
        self.wait_for_streamlit()

    def delete_step(self, index: int) -> None:
        """Delete a pipeline step by index.

        Args:
            index: Zero-based step index.
        """
        self.get_step_delete_button(index).click()
        self.wait_for_streamlit()

    def move_step_up(self, index: int) -> None:
        """Move a pipeline step up.

        Args:
            index: Zero-based step index.
        """
        self.get_step_up_button(index).click()
        self.wait_for_streamlit()

    def move_step_down(self, index: int) -> None:
        """Move a pipeline step down.

        Args:
            index: Zero-based step index.
        """
        self.get_step_down_button(index).click()
        self.wait_for_streamlit()

    # ==================================================================
    #  ACTIONS — Column Selector shaper
    # ==================================================================

    def click_select_all_columns(self) -> None:
        """Click 'Select All' quick-action in Column Selector."""
        self.column_select_all_button.click()
        self.wait_for_streamlit()

    def click_clear_all_columns(self) -> None:
        """Click 'Clear All' quick-action in Column Selector."""
        self.column_clear_all_button.click()
        self.wait_for_streamlit()

    def click_numeric_only_columns(self) -> None:
        """Click 'Numeric Only' quick-action in Column Selector."""
        self.column_numeric_only_button.click()
        self.wait_for_streamlit()

    # ==================================================================
    #  ACTIONS — Visualization
    # ==================================================================

    def select_x_axis(self, column: str) -> None:
        """Select a column for the X-axis."""
        self._open_and_select(self.viz_x_axis_selectbox, column)

    def select_y_axis(self, column: str) -> None:
        """Select a column for the Y-axis."""
        self._open_and_select(self.viz_y_axis_selectbox, column)

    def select_y_bar(self, column: str) -> None:
        """Select the bars (left Y-axis) column for a dual-axis bar+dot plot."""
        self._open_and_select(self.viz_y_bar_selectbox, column)

    def select_y_dot(self, column: str) -> None:
        """Select the dots (right Y-axis) column for a dual-axis bar+dot plot."""
        self._open_and_select(self.viz_y_dot_selectbox, column)

    def select_color_by(self, column: str) -> None:
        """Select a column for 'Color by'."""
        self._open_and_select(self.viz_color_by_selectbox, column)

    def select_group_by(self, column: str) -> None:
        """Select a column for 'Group by' (Grouped Bar)."""
        self._open_and_select(self.viz_group_by_selectbox, column)

    def select_stack_by(self, column: str) -> None:
        """Select a column for 'Stack by' (Stacked Bar)."""
        self._open_and_select(self.viz_stack_by_selectbox, column)

    def refresh_plot(self) -> None:
        """Click 'Refresh Plot' and wait."""
        self.viz_refresh_button.click()
        self.wait_for_streamlit()

    def toggle_auto_refresh(self) -> None:
        """Toggle the auto-refresh switch."""
        self.viz_auto_refresh_toggle.click()
        self.wait_for_streamlit()

    def toggle_advanced_settings(self) -> None:
        """Toggle the 'Show advanced settings' switch."""
        self.viz_show_advanced_toggle.click()
        self.wait_for_streamlit()

    def select_engine(self, engine: str) -> None:
        """Select a rendering engine via pills (idempotent).

        Clicking an already-active segmented-control pill DESELECTS it, so we
        click only when the target engine isn't already active.

        Args:
            engine: ``"plotly"`` or ``"matplotlib"``.
        """
        pill = self.viz_engine_pills.get_by_role("button", name=engine)
        expect(pill).to_be_visible(timeout=self.RENDER_TIMEOUT)
        active = self.viz_engine_pills.locator("[data-testid='stBaseButton-pillsActive']")
        if active.count() and engine.lower() in (active.first.inner_text() or "").lower():
            return
        pill.click()
        self.wait_for_streamlit()

    # ==================================================================
    #  ASSERTIONS
    # ==================================================================

    def assert_page_header_visible(self) -> None:
        """Assert the manage plots heading is displayed."""
        expect(self.page_header).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_no_plots_warning(self) -> None:
        """Assert the 'no plots' warning is displayed."""
        expect(self.no_plots_warning).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_chart_visible(self, timeout: int | None = None) -> None:
        """Assert a Plotly chart is rendered.

        The custom component iframe starts with ``height="0"`` and
        is resized only after its internal JS sets the frame height.
        We wait for the element to exist, then poll until its height
        attribute is non-zero (i.e. the chart has loaded).
        """
        t = timeout or self.RENDER_TIMEOUT
        chart = self.plotly_chart.first
        # Wait for the iframe element to appear in the DOM
        expect(chart).to_be_attached(timeout=t)
        # Wait until the iframe height becomes non-zero
        chart.evaluate("""el => new Promise((resolve, reject) => {
                const deadline = Date.now() + %d;
                const check = () => {
                    const h = parseInt(el.getAttribute('height') || '0', 10);
                    if (h > 0) return resolve(true);
                    if (Date.now() > deadline) return reject(
                        new Error('Chart iframe height stayed 0'));
                    requestAnimationFrame(check);
                };
                check();
            })""" % t)

    def assert_matplotlib_chart_visible(self) -> None:
        """Assert a Matplotlib chart is rendered."""
        expect(self.matplotlib_chart.first).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_plot_pill_visible(self, plot_name: str) -> None:
        """Assert a plot pill with the given name is visible.

        Args:
            plot_name: Expected display name.
        """
        expect(self.get_plot_pill(plot_name)).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_plot_pill_not_visible(self, plot_name: str) -> None:
        """Assert a plot pill is gone (after delete).

        Args:
            plot_name: Display name that should be absent.
        """
        expect(self.get_plot_pill(plot_name)).not_to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_pipeline_step_count(self, expected: int) -> None:
        """Assert the number of pipeline step expanders.

        Args:
            expected: Expected number of steps.
        """
        expect(self.pipeline_steps).to_have_count(expected, timeout=self.RENDER_TIMEOUT)

    def assert_finalize_button_visible(self) -> None:
        """Assert the finalize button is visible."""
        expect(self.finalize_button).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_create_form_visible(self) -> None:
        """Assert the create-plot form elements are visible."""
        expect(self.plot_name_input).to_be_visible(timeout=self.RENDER_TIMEOUT)
        expect(self.create_plot_button).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_controls_visible(self) -> None:
        """Assert the controls row (rename, delete, etc.) is visible."""
        expect(self.rename_input).to_be_visible(timeout=self.RENDER_TIMEOUT)
        expect(self.delete_button).to_be_visible(timeout=self.RENDER_TIMEOUT)
        expect(self.duplicate_button).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_pipeline_editor_visible(self) -> None:
        """Assert the pipeline editor (add transformation UI) is shown.

        Note: the finalize button only appears after at least one step
        is added.  Use ``assert_finalize_button_visible`` separately.
        """
        expect(self.add_transformation_selectbox).to_be_visible(timeout=self.RENDER_TIMEOUT)
        expect(self.add_to_pipeline_button).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_visualization_section_visible(self) -> None:
        """Assert the visualization config section is shown."""
        expect(self.viz_plot_type_selectbox).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_no_processed_data_warning(self) -> None:
        """Assert the 'no processed data' warning is shown."""
        expect(self.no_processed_data_warning).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_success_message_visible(self) -> None:
        """Assert a success alert is visible somewhere on the page."""
        success = self.page.locator("[data-testid='stAlertContentSuccess']").first
        expect(success).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_error_message_visible(self) -> None:
        """Assert an error alert is visible somewhere on the page."""
        error = self.page.locator("[data-testid='stAlertContentError']").first
        expect(error).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def assert_warning_message_visible(self) -> None:
        """Assert a warning alert is visible somewhere on the page."""
        warning = self.page.locator("[data-testid='stAlertContentWarning']").first
        expect(warning).to_be_visible(timeout=self.RENDER_TIMEOUT)
