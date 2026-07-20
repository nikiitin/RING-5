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

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, expect

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

    # Helpers

    def _by_label(self, test_id: str, label_text: str) -> Locator:
        """Return a widget locator filtered by its visible label text.

        Streamlit can render multiple widgets with the same
        ``data-testid`` in different sections; filtering by label
        prevents ambiguity.
        """
        return self.page.locator(f"[data-testid='{test_id}']").filter(has_text=label_text)

    # Navigation

    def navigate(self) -> None:
        """Open the Manage Plots page via sidebar."""
        self.navigate_to(self.PAGE_NAME)

    #  1. Page-level locators

    @property
    def page_header(self) -> Locator:
        """The 'Manage Plots' heading (scoped to main content)."""
        return self.page.locator("[data-testid='stMainBlockContainer']").get_by_text("Manage Plots")

    #  2. Create Plot form

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

    #  3. Plot selector pills

    @property
    def plot_selector_pills(self) -> Locator:
        """The st.pills widget for selecting plots (key=plot_selector)."""
        return self.page.get_by_role("radiogroup", name="Select Plot")

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
        return self.plot_selector_pills.get_by_role("radio", name=plot_name, exact=True)

    #  4. Controls row (rename / save / load / delete / duplicate)

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

    @property
    def plot_transfer_expander(self) -> Locator:
        """Expander for copying settings or a pipeline into the active plot."""
        return self.page.locator("[data-testid='stExpander']").filter(
            has_text="Copy from another plot"
        )

    @property
    def plot_transfer_button(self) -> Locator:
        """Apply the selected source-to-current-plot transfer."""
        return self.page.get_by_role("button", name="Copy into current plot")

    #  5. Pipeline editor (st.fragment)

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
    # NOTE: the Column Selector has NO Select All / Clear All / Numeric Only
    # quick-action buttons — it's just a "Columns to keep" multiselect that
    # defaults to the first column.

    @property
    def column_selector_multiselect(self) -> Locator:
        """'Columns to keep' multiselect inside the Column Selector step."""
        return self._by_label("stMultiSelect", "Columns to keep")

    # -- Sort shaper widgets -------

    @property
    def sort_columns_multiselect(self) -> Locator:
        """'Sort by columns' multiselect (Sort shaper)."""
        return self._by_label("stMultiSelect", "Sort by columns")

    # -- Filter (conditionSelector) shaper widgets -------

    @property
    def filter_column_selectbox(self) -> Locator:
        """'Column to filter' selectbox in the Filter step."""
        return self._by_label("stSelectbox", "Column to filter")

    @property
    def filter_mode_selectbox(self) -> Locator:
        """'Filter mode' selectbox in the Filter step."""
        return self._by_label("stSelectbox", "Filter mode")

    # -- Normalize shaper widgets -------

    @property
    def normalize_column_selectbox(self) -> Locator:
        """'Normalizer column (baseline identifier)' selectbox (Normalize shaper)."""
        return self._by_label("stSelectbox", "Normalizer column")

    @property
    def normalize_variables_multiselect(self) -> Locator:
        """'Variables to normalize' multiselect (Normalize shaper)."""
        return self._by_label("stMultiSelect", "Variables to normalize")

    # -- Mean Calculator shaper widgets -------

    @property
    def mean_group_by_multiselect(self) -> Locator:
        """'Group by' multiselect in Mean Calculator."""
        return self._by_label("stMultiSelect", "Group by")

    @property
    def mean_variables_multiselect(self) -> Locator:
        """'Variables' multiselect in Mean Calculator."""
        return self._by_label("stMultiSelect", "Variables")

    # -- Transformer shaper widgets -------

    @property
    def transformer_source_selectbox(self) -> Locator:
        """'Select Variable to Transform' selectbox in Transformer."""
        return self._by_label("stSelectbox", "Select Variable to Transform")

    @property
    def transformer_convert_selectbox(self) -> Locator:
        """'Convert to:' selectbox in Transformer."""
        return self._by_label("stSelectbox", "Convert to")

    #  6. Visualization section (st.fragment)

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
    def stacked_statistics_multiselect(self) -> Locator:
        """'Statistics to Stack' multiselect (for Stacked Bar).

        Stacked bar has no 'Stack by'/Y-axis selectbox — it stacks multiple
        numeric statistics chosen here (defaults to the first numeric columns).
        """
        return self._by_label("stMultiSelect", "Statistics to Stack")

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
        """'X-label' text input (the plot-config axis-label field)."""
        return self._by_label("stTextInput", "X-label").locator("input")

    @property
    def viz_y_label_input(self) -> Locator:
        """'Y-label' text input (the plot-config axis-label field)."""
        return self._by_label("stTextInput", "Y-label").locator("input")

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
    def viz_drill_down_toggle(self) -> Locator:
        """Opt-in source-row exploration toggle."""
        return self.page.get_by_text("Explore source rows", exact=True)

    @property
    def drill_down_panel(self) -> Locator:
        """The source-row detail panel shown after a point click."""
        return self.page.get_by_text("Source rows", exact=True)

    @property
    def drill_down_back_button(self) -> Locator:
        """Button that closes the source-row detail panel."""
        return self.page.get_by_role("button", name="Back to full plot")

    @property
    def viz_settings_pills(self) -> Locator:
        """Settings navigation pills (key=settings_nav).

        The basic sections (Layout / Typography / Legends) are ALWAYS rendered
        whenever a plot's visualization section is shown — they are not gated by
        the 'Show advanced settings' toggle (only the advanced sections are).
        """
        return self.page.get_by_role("radiogroup", name="Settings")

    @property
    def viz_layout_section_pill(self) -> Locator:
        """The Layout settings pill containing dimensions and facet controls."""
        return self.viz_settings_pills.get_by_role("radio", name="Layout")

    @property
    def small_multiples_toggle(self) -> Locator:
        """Opt-in switch for splitting the active plot into panels."""
        return self.page.get_by_role("switch", name="Split this plot into comparable panels")

    @property
    def small_multiples_by(self) -> Locator:
        """Categorical columns used to form small-multiples panels."""
        return self._by_label("stMultiSelect", "Create one panel for each combination of")

    @property
    def viz_advanced_section_pill(self) -> Locator:
        """An advanced-only settings-section pill ('Colors').

        Advanced sections (Axes / Data Labels / Colors / Advanced) are shown
        only when 'Show advanced settings' is enabled — so this pill is the
        reliable signal of the toggle's effect (the basic pills never disappear).
        """
        return self.viz_settings_pills.get_by_role("radio", name="Colors")

    @property
    def viz_engine_pills(self) -> Locator:
        """Engine selector pills (plotly / matplotlib)."""
        return self.page.get_by_role("radiogroup", name="Engine")

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

    #  7. Download section

    @property
    def download_expander(self) -> Locator:
        """The download expander container."""
        return self.page.locator("[data-testid='stExpander']").filter(has_text="Download")

    @property
    def download_format_pills(self) -> Locator:
        """Format selector pills inside the download expander."""
        return self.download_expander.get_by_role("radiogroup", name="Format")

    @property
    def download_button(self) -> Locator:
        """Download button inside the download expander."""
        return self.download_expander.get_by_role("button", name="Download")

    #  8. Workspace management

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

    #  ACTIONS — Create Plot

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
        self.wait_for_streamlit(expect_rerun=True)
        expect(self.get_plot_pill(name).first).to_be_visible(timeout=self.RENDER_TIMEOUT)
        self.select_plot(name)

    def _open_and_select(self, selectbox: Locator, value: str) -> None:
        """Open a selectbox and choose *value*, retrying interrupted clicks."""
        expect(selectbox).to_be_visible(timeout=self.RENDER_TIMEOUT)
        option = self.page.get_by_role("option", name=value, exact=True).first
        for _ in range(3):
            selectbox.get_by_role("combobox").click()
            try:
                option.wait_for(state="visible", timeout=5_000)
                option.click(timeout=5_000)
            except PlaywrightTimeoutError:
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(250)
                continue
            self.wait_for_streamlit()
            return
        expect(option).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def select_plot_type(self, plot_type: str) -> None:
        """Select a plot type in the create-plot form selectbox, verifying it took.

        Args:
            plot_type: Exact factory key (e.g. "bar", "dual_axis_bar_dot").
        """
        self._open_and_select(self.plot_type_selectbox, plot_type)
        expect(self.plot_type_selectbox.get_by_role("combobox")).to_have_value(
            plot_type,
            timeout=self.RENDER_TIMEOUT,
        )

    #  ACTIONS — Plot Selector

    def select_plot(self, plot_name: str) -> None:
        """Select a plot by clicking its pill when it is not already selected.

        Args:
            plot_name: Display name of the plot.
        """
        pill = self.get_plot_pill(plot_name)
        expect(pill).to_be_visible(timeout=self.RENDER_TIMEOUT)
        if pill.is_checked():
            return
        pill.click()
        self.wait_for_streamlit(expect_rerun=True)
        expect(pill).to_be_checked(timeout=self.RENDER_TIMEOUT)

    #  ACTIONS — Controls row

    def rename_plot(self, new_name: str) -> None:
        """Rename the currently selected plot.

        Args:
            new_name: New plot name.
        """
        self.rename_input.fill(new_name)
        self.rename_input.press("Enter")
        self.wait_for_streamlit(expect_rerun=True)

    def delete_plot(self) -> None:
        """Delete the currently selected plot."""
        self.delete_button.click()
        self.wait_for_streamlit(expect_rerun=True)

    def duplicate_plot(self) -> None:
        """Duplicate the currently selected plot."""
        self.duplicate_button.click()
        self.wait_for_streamlit(expect_rerun=True)

    def copy_default_settings_from_other_plot(self) -> None:
        """Open the transfer panel and apply its default selected settings."""
        self.plot_transfer_expander.locator("summary").click()
        self.plot_transfer_button.click()
        self.wait_for_streamlit(expect_rerun=True)

    #  ACTIONS — Pipeline editor

    def add_shaper(self, shaper_name: str) -> None:
        """Select a shaper type and click 'Add to Pipeline'.

        Args:
            shaper_name: Exact display label (e.g. "Column Selector").
        """
        self._open_and_select(self.add_transformation_selectbox, shaper_name)
        self.add_to_pipeline_button.click()
        self.wait_for_streamlit(expect_rerun=True)

    def finalize_pipeline(self) -> None:
        """Click 'Finalize Pipeline for Plotting' and wait."""
        self.finalize_button.click()
        self.wait_for_streamlit(expect_rerun=True)

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

    #  ACTIONS — Column Selector shaper

    def select_all_columns(self) -> None:
        """Add every available column to the 'Columns to keep' multiselect.

        The Column Selector has no Select All button (it just defaults to the
        first column), so we open the multiselect and click each remaining
        option until only the empty "No options" state is left.
        """
        ms = self.column_selector_multiselect
        expect(ms).to_be_visible(timeout=self.RENDER_TIMEOUT)
        options = self.page.get_by_role("option").filter(has_not_text="No options")
        for _ in range(30):  # safety bound, >> number of columns
            ms.click()
            self.page.wait_for_timeout(250)  # let the option list render
            if options.count() == 0:
                break
            options.first.click()
            self.page.wait_for_timeout(250)  # let the multiselect commit
        self.page.keyboard.press("Escape")
        self.wait_for_streamlit()

    #  ACTIONS — Visualization

    def select_x_axis(self, column: str) -> None:
        """Select a column for the X-axis."""
        self._open_and_select(self.viz_x_axis_selectbox, column)

    def select_y_axis(self, column: str) -> None:
        """Select a column for the Y-axis."""
        self._open_and_select(self.viz_y_axis_selectbox, column)

    def open_layout_settings(self) -> None:
        """Open the Layout settings section when it is not already active."""
        if self.viz_layout_section_pill.is_checked():
            return
        self.viz_layout_section_pill.click()
        self.wait_for_streamlit(expect_rerun=True)

    def enable_small_multiples(self) -> None:
        """Enable small multiples and wait until its facet controls are committed."""
        if self.small_multiples_toggle.is_checked():
            return
        self.page.get_by_text("Split this plot into comparable panels", exact=True).click()
        self.wait_for_streamlit(expect_rerun=True)

    def add_small_multiples_column(self, column: str) -> None:
        """Add one categorical column to the small-multiples grouping."""
        self.small_multiples_by.click()
        self.page.get_by_role("option", name=column, exact=True).click()
        self.wait_for_streamlit(expect_rerun=True)

    def enable_drill_down(self) -> None:
        """Enable point-click source-row exploration and wait for the fragment rerun."""
        self.viz_drill_down_toggle.click()
        self.wait_for_streamlit(expect_rerun=True)
        self.page.wait_for_timeout(500)

    def click_first_plot_point(self) -> None:
        """Click the first rendered Plotly point inside the custom-component frame."""
        self.assert_chart_visible()
        frame = self.plotly_chart.first.content_frame
        frame.locator(".plotly .point").first.click(force=True)
        self.wait_for_streamlit(expect_rerun=True)
        self.page.wait_for_timeout(500)

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

    def refresh_plot(self) -> None:
        """Click 'Refresh Plot' and wait for the regeneration rerun.

        Refresh reruns to regenerate the figure; under -n 3 that can be slow, so
        we wait for the rerun (expect_rerun) with generous time before callers
        assert the chart — otherwise the regen races a tight assert_chart_visible.
        """
        self.viz_refresh_button.click()
        self.wait_for_streamlit(timeout=60_000, expect_rerun=True)

    def toggle_auto_refresh(self) -> None:
        """Toggle the auto-refresh switch."""
        self.viz_auto_refresh_toggle.click()
        self.wait_for_streamlit()

    def toggle_advanced_settings(self) -> None:
        """Toggle 'Show advanced settings', verifying the switch actually flipped.

        The toggle renders as a ``role=checkbox``; we read its state, click the
        label, then assert the checked state inverted so a missed click fails
        loudly. This toggle gates only the *advanced* settings-section pills
        (Axes / Data Labels / Colors / Advanced); the basic Layout / Typography
        / Legends pills are always visible.
        """
        checkbox = self.page.get_by_role("switch", name="Show advanced settings")
        expect(checkbox).to_be_attached(timeout=self.RENDER_TIMEOUT)
        was_checked = checkbox.is_checked()
        self.viz_show_advanced_toggle.click()
        self.wait_for_streamlit()
        if was_checked:
            expect(checkbox).not_to_be_checked(timeout=self.RENDER_TIMEOUT)
        else:
            expect(checkbox).to_be_checked(timeout=self.RENDER_TIMEOUT)

    def select_engine(self, engine: str) -> None:
        """Select a rendering engine and wait for figure regeneration.

        Args:
            engine: ``"plotly"`` or ``"matplotlib"``.
        """
        pill = self.viz_engine_pills.get_by_role("radio", name=engine)
        expect(pill).to_be_visible(timeout=self.RENDER_TIMEOUT)
        if pill.is_checked():
            return
        for _ in range(3):
            pill.click()
            try:
                expect(pill).to_be_checked(timeout=10_000)
            except AssertionError:
                self.page.wait_for_timeout(250)
                continue
            self.wait_for_streamlit(timeout=60_000, expect_rerun=True)
            expect(pill).to_be_checked(timeout=60_000)
            return
        expect(pill).to_be_checked(timeout=60_000)

    #  ASSERTIONS

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
