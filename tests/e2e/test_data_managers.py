"""E2E tests for the Data Managers page.

Covers page structure, Outlier Remover, Seeds Reducer, Mixer,
Preprocessor, and Operations History using the ``tier1_page`` fixture
(18 rows of CSV data pre-loaded: 3 benchmarks x 3 configs x 2 seeds).

Columns: benchmark_name, config_description, seed, system.cpu.ipc,
         system.cpu.numCycles, simTicks, system.cpu.dcache.overall_miss_rate,
         system.cpu.committedInsts
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, expect

from tests.visual.pages.data_managers_page import DataManagersPage

pytestmark = pytest.mark.requires_browser

_E2E_TIMEOUT: int = 30_000


# Helpers — Streamlit widget interaction


def _select_dropdown_option(page: Page, selectbox: Locator, text: str) -> None:
    """Open a Streamlit selectbox and choose *text*, retrying missed clicks."""
    option = page.get_by_role("option", name=text, exact=True).first
    for _ in range(3):
        selectbox.get_by_role("combobox").click()
        try:
            option.wait_for(state="visible", timeout=5_000)
            option.click(timeout=5_000)
        except PlaywrightTimeoutError:
            page.keyboard.press("Escape")
            page.wait_for_timeout(250)
            continue
        return
    expect(option).to_be_visible(timeout=_E2E_TIMEOUT)


def _add_multiselect_option(page: Page, multiselect: Locator, text: str) -> None:
    """Add *text* to a Streamlit multiselect via type-to-filter + click.

    Robust across repeated calls: a prior selection can leave the dropdown open,
    so a blind re-click would toggle it shut and the option click would time out.
    Instead we focus the box, type to filter the options to the wanted one, and
    wait for that option before clicking.
    """
    multiselect.click()
    multiselect.locator("input").fill(text)
    option = page.get_by_role("option", name=text, exact=True)
    expect(option.first).to_be_visible(timeout=_E2E_TIMEOUT)
    option.first.click()
    page.wait_for_timeout(200)


# Page structure


@pytest.mark.xdist_group("e2e_data_managers_structure")
class TestDataManagersPageStructure:
    """Tier 1: Verify page layout with data loaded."""

    def test_page_loads_with_header(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.assert_page_header_visible()

    def test_all_tabs_visible(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.assert_tabs_visible()

    def test_summary_tab_can_be_selected(self, tier1_page: Page) -> None:
        """The Summary tab can be restored after another tab was active."""
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Summary")
        dm.assert_tab_active("Summary")

    def test_summary_tab_shows_rows_metric(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Summary")
        dm.assert_summary_has_rows(expected=18)

    def test_summary_tab_shows_columns_metric(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Summary")
        dm.assert_summary_has_columns()

    def test_data_visualization_tab_shows_dataframe(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Data Visualization")
        dm.assert_dataframe_visible()

    def test_no_data_warning_absent(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        expect(dm.no_data_warning).not_to_be_visible()


# Outlier Remover


@pytest.mark.xdist_group("e2e_data_managers_outlier")
class TestOutlierRemover:
    """Tier 1: Outlier Remover workflow (ordered tests, state accumulates)."""

    @pytest.mark.order(1)
    def test_01_tab_loads(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Outlier Remover")
        dm.assert_tab_active("Outlier Remover")
        expect(dm.outlier_column_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(2)
    def test_02_select_column(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        _select_dropdown_option(tier1_page, dm.outlier_column_selectbox, "simTicks")
        dm.wait_for_streamlit()

    @pytest.mark.order(3)
    def test_03_apply_shows_metrics(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.apply_outlier_remover()
        dm.assert_outlier_shows_metrics()

    @pytest.mark.order(4)
    def test_04_confirm_applies_filter(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.confirm_outlier_remover()
        dm.assert_success_message_visible()


# Seeds Reducer


@pytest.mark.xdist_group("e2e_data_managers_seeds")
class TestSeedsReducer:
    """Tier 1: Seeds Reducer workflow."""

    @pytest.mark.order(1)
    def test_01_tab_loads(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Seeds Reducer")
        dm.assert_tab_active("Seeds Reducer")

    @pytest.mark.order(2)
    def test_02_reducer_widgets_visible(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.assert_reducer_ready()
        expect(dm.seeds_categorical_multiselect).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(3)
    def test_03_apply_reducer(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.apply_seeds_reducer()
        expect(dm.seeds_confirm_button).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(4)
    def test_04_confirm_reduces_rows(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.confirm_seeds_reducer()
        dm.assert_success_message_visible()


# Mixer


@pytest.mark.xdist_group("e2e_data_managers_mixer")
class TestMixer:
    """Tier 1: Column Mixer workflow."""

    @pytest.mark.order(1)
    def test_01_tab_loads(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Mixer")
        dm.assert_tab_active("Mixer")
        expect(dm.mixer_columns_multiselect).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(2)
    def test_02_widgets_visible(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        expect(dm.mixer_new_name_input).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(dm.mixer_preview_button).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(3)
    def test_03_preview_merge(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        _add_multiselect_option(tier1_page, dm.mixer_columns_multiselect, "system.cpu.ipc")
        _add_multiselect_option(tier1_page, dm.mixer_columns_multiselect, "simTicks")
        tier1_page.keyboard.press("Escape")
        dm.wait_for_streamlit()
        dm.mixer_new_name_input.fill("mixed_metric")
        dm.apply_mixer_preview()

    @pytest.mark.order(4)
    def test_04_confirm_merge(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.confirm_mixer()
        dm.assert_success_message_visible()


# Preprocessor


@pytest.mark.xdist_group("e2e_data_managers_preproc")
class TestPreprocessor:
    """Tier 1: Preprocessor workflow."""

    @pytest.mark.order(1)
    def test_01_tab_loads(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Preprocessor")
        dm.assert_tab_active("Preprocessor")
        expect(dm.preproc_src1_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(2)
    def test_02_widgets_visible(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        expect(dm.preproc_operation_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(dm.preproc_src2_selectbox).to_be_visible(timeout=_E2E_TIMEOUT)
        expect(dm.preproc_preview_button).to_be_visible(timeout=_E2E_TIMEOUT)

    @pytest.mark.order(3)
    def test_03_preview_result(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        _select_dropdown_option(tier1_page, dm.preproc_src1_selectbox, "simTicks")
        dm.wait_for_streamlit()
        _select_dropdown_option(tier1_page, dm.preproc_src2_selectbox, "system.cpu.committedInsts")
        dm.wait_for_streamlit()
        dm.preproc_name_input.fill("ticks_per_inst")
        dm.apply_preprocessor_preview()

    @pytest.mark.order(4)
    def test_04_confirm_add_column(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.confirm_preprocessor()
        dm.assert_success_message_visible()


# Operations History


@pytest.mark.xdist_group("e2e_data_managers_history")
class TestOperationsHistory:
    """Tier 1: Operations History after data management."""

    def test_history_tab_loads(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.navigate()
        dm.select_tab("Operations History")
        dm.assert_tab_active("Operations History")

    def test_history_initially_empty(self, tier1_page: Page) -> None:
        dm = DataManagersPage(tier1_page)
        dm.select_tab("Operations History")
        dm.assert_history_empty()
