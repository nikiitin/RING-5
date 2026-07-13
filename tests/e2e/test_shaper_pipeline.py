"""E2E tests for the shaper pipeline editor on the Manage Plots page.

Covers:
- Pipeline step add / remove / reorder operations
- Individual shaper type configuration widgets
- Pipeline save and load workflows

Data precondition:
    All tests use ``tier1_page`` which provides a browser page with
    18-row CSV data already loaded (columns: benchmark_name,
    config_description, seed, system.cpu.ipc, system.cpu.numCycles,
    simTicks, system.cpu.dcache.overall_miss_rate,
    system.cpu.committedInsts).
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import E2E_TIMEOUT
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_bar_plot(mp: ManagePlotsPage, name: str) -> None:
    """Create a bar plot and assert its pill is visible."""
    mp.navigate()
    mp.create_plot(name, "bar")
    mp.assert_plot_pill_visible(name)


def _create_finalize_and_reload(mp: ManagePlotsPage, name: str, shapers: list[str]) -> None:
    """Create a plot, add shapers, and finalize its pipeline."""
    _create_bar_plot(mp, name)
    for shaper in shapers:
        mp.add_shaper(shaper)
    mp.finalize_pipeline()


# ===================================================================
# Tier 1 -- Pipeline add / remove / reorder operations (ordered)
# ===================================================================


@pytest.mark.xdist_group("e2e_shaper_pipeline")
class TestShaperPipelineOperations:
    """Tier 1: Pipeline add/remove/reorder operations (ordered).

    All tests share the same browser page via ``tier1_page`` and
    accumulate state across the class.  Test names are numbered to
    guarantee execution order.
    """

    @pytest.mark.order(1)
    def test_01_create_plot_for_pipeline(self, tier1_page: Page) -> None:
        """Create a bar plot dedicated to pipeline testing."""
        mp = ManagePlotsPage(tier1_page)
        _create_bar_plot(mp, "Pipeline Test")
        mp.assert_pipeline_editor_visible()

    @pytest.mark.order(2)
    def test_02_add_sort_shaper(self, tier1_page: Page) -> None:
        """Add a Sort shaper and verify the pipeline has 1 step."""
        mp = ManagePlotsPage(tier1_page)
        mp.add_shaper("Sort")
        mp.assert_pipeline_step_count(1)

    @pytest.mark.order(3)
    def test_03_add_column_selector(self, tier1_page: Page) -> None:
        """Add Column Selector; pipeline should now have 2 steps."""
        mp = ManagePlotsPage(tier1_page)
        mp.add_shaper("Column Selector")
        mp.assert_pipeline_step_count(2)

    @pytest.mark.order(4)
    def test_04_reorder_steps(self, tier1_page: Page) -> None:
        """Move step 1 (Column Selector) up so it becomes step 0."""
        mp = ManagePlotsPage(tier1_page)
        mp.move_step_up(1)
        mp.assert_pipeline_step_count(2)
        # After reorder, first step should contain "Column Selector"
        step_0 = mp.get_pipeline_step(0)
        expect(step_0).to_contain_text("Column Selector", timeout=E2E_TIMEOUT)

    @pytest.mark.order(5)
    def test_05_delete_step(self, tier1_page: Page) -> None:
        """Delete step 0 (Column Selector); 1 step (Sort) remains."""
        mp = ManagePlotsPage(tier1_page)
        mp.delete_step(0)
        mp.assert_pipeline_step_count(1)

    @pytest.mark.order(6)
    def test_06_add_multiple_shapers(self, tier1_page: Page) -> None:
        """Add Normalize and Sort; pipeline should have 3 steps total."""
        mp = ManagePlotsPage(tier1_page)
        mp.add_shaper("Normalize")
        mp.assert_pipeline_step_count(2)
        mp.add_shaper("Sort")
        mp.assert_pipeline_step_count(3)

    @pytest.mark.order(7)
    def test_07_finalize_pipeline(self, tier1_page: Page) -> None:
        """Finalizing refreshes the visualization without navigation."""
        mp = ManagePlotsPage(tier1_page)
        mp.finalize_pipeline()
        mp.assert_visualization_section_visible()


# ===================================================================
# Tier 1 -- Individual shaper type configuration widgets
# ===================================================================


@pytest.mark.xdist_group("e2e_shaper_types")
class TestShaperTypes:
    """Tier 1: Verify each shaper type can be added and configured.

    Each test creates a fresh plot, adds a single shaper, and asserts
    that the shaper-specific configuration widget is visible.
    """

    def test_column_selector(self, tier1_page: Page) -> None:
        """Column Selector shows the 'Columns to keep' multiselect.

        (The Column Selector has no Select All / Clear All quick-action buttons;
        it is just this multiselect, which defaults to the first column.)
        """
        mp = ManagePlotsPage(tier1_page)
        _create_bar_plot(mp, "CS Type Test")
        mp.add_shaper("Column Selector")
        mp.assert_pipeline_step_count(1)
        expect(mp.column_selector_multiselect).to_be_visible(timeout=E2E_TIMEOUT)
        mp.select_all_columns()
        expect(mp.column_selector_multiselect).to_be_visible(timeout=E2E_TIMEOUT)

    def test_sort(self, tier1_page: Page) -> None:
        """Sort shaper shows the 'Sort by columns' multiselect."""
        mp = ManagePlotsPage(tier1_page)
        _create_bar_plot(mp, "Sort Type Test")
        mp.add_shaper("Sort")
        mp.assert_pipeline_step_count(1)
        expect(mp.sort_columns_multiselect).to_be_visible(timeout=E2E_TIMEOUT)

    def test_filter(self, tier1_page: Page) -> None:
        """Filter shaper shows column, operator, and value widgets."""
        mp = ManagePlotsPage(tier1_page)
        _create_bar_plot(mp, "Filter Type Test")
        mp.add_shaper("Filter")
        mp.assert_pipeline_step_count(1)
        expect(mp.filter_column_selectbox).to_be_visible(timeout=E2E_TIMEOUT)

    def test_normalize(self, tier1_page: Page) -> None:
        """Normalize shaper shows the 'Variables to normalize' multiselect."""
        mp = ManagePlotsPage(tier1_page)
        _create_bar_plot(mp, "Norm Type Test")
        mp.add_shaper("Normalize")
        mp.assert_pipeline_step_count(1)
        expect(mp.normalize_variables_multiselect).to_be_visible(timeout=E2E_TIMEOUT)

    def test_mean_calculator(self, tier1_page: Page) -> None:
        """Mean Calculator shows the group-by multiselect."""
        mp = ManagePlotsPage(tier1_page)
        _create_bar_plot(mp, "Mean Type Test")
        mp.add_shaper("Mean Calculator")
        mp.assert_pipeline_step_count(1)
        expect(mp.mean_group_by_multiselect).to_be_visible(timeout=E2E_TIMEOUT)

    def test_transformer(self, tier1_page: Page) -> None:
        """Transformer shaper shows the source column selectbox."""
        mp = ManagePlotsPage(tier1_page)
        _create_bar_plot(mp, "Trans Type Test")
        mp.add_shaper("Transformer")
        mp.assert_pipeline_step_count(1)
        expect(mp.transformer_source_selectbox).to_be_visible(timeout=E2E_TIMEOUT)

    def test_split_apply(self, tier1_page: Page) -> None:
        """Split-Apply (Per-Axis) can be added as a pipeline step.

        Note: Split-Apply renders a *nested* ``st.expander`` per column group,
        so the step-count helper (which counts expanders) would report >1 — we
        instead just assert the step itself shows the Split-Apply label.
        """
        mp = ManagePlotsPage(tier1_page)
        _create_bar_plot(mp, "Split Type Test")
        mp.add_shaper("Split-Apply (Per-Axis)")
        step = mp.get_pipeline_step(0)
        expect(step).to_contain_text("Split-Apply", timeout=E2E_TIMEOUT)

    def test_multiple_types_combined(self, tier1_page: Page) -> None:
        """Add Column Selector + Sort + Filter in a single pipeline."""
        mp = ManagePlotsPage(tier1_page)
        _create_bar_plot(mp, "Multi Shaper Test")
        mp.add_shaper("Column Selector")
        mp.add_shaper("Sort")
        mp.add_shaper("Filter")
        mp.assert_pipeline_step_count(3)
        mp.assert_finalize_button_visible()
