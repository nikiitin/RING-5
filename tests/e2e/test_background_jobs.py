"""Browser coverage for the session-owned background-job center."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.base_page import BasePage
from tests.visual.pages.data_source_page import DataSourcePage

pytestmark = [pytest.mark.requires_browser, pytest.mark.xdist_group("e2e_background_jobs")]


class TestBackgroundJobCenter:
    """A real scan appears as a human-readable terminal job and can be cleared."""

    def test_scan_job_progress_and_cleanup(self, tier0_page: Page) -> None:
        # [test->req~ring5.workspace.background-jobs~1]
        base = BasePage(tier0_page)
        base.open_background_jobs()
        expect(base.background_jobs_content).to_contain_text("No background jobs in this session.")

        source = Path(__file__).parent / "fixtures" / "background_job_stats"
        assert (source / "run" / "stats.txt").is_file(), "tracked scan fixture is missing"
        data_source = DataSourcePage(tier0_page)
        data_source.navigate()
        data_source.ensure_parse_mode()
        data_source.stats_path_input.fill(str(source))
        data_source.stats_path_input.press("Tab")
        data_source.wait_for_streamlit()
        data_source.scan_and_wait()

        base.open_background_jobs()
        expect(base.background_jobs_content).to_contain_text("Scan: background_job_stats")
        expect(base.background_jobs_content).to_contain_text("Scan · Completed · 1/1 · attempt 1")
        expect(base.background_jobs_content.get_by_role("button", name="Cancel")).to_be_disabled()
        expect(base.background_jobs_content.get_by_role("button", name="Retry")).to_be_disabled()

        base.background_jobs_content.get_by_role("button", name="Clear finished").click()
        base.wait_for_streamlit(expect_rerun=True)
        base.open_background_jobs()
        expect(base.background_jobs_content).to_contain_text("No background jobs in this session.")


class TestBackgroundParseJob:
    """A real parse is consumed automatically and remains available in Recent."""

    def test_parse_loads_without_a_blocking_dialog(self, tier0_page: Page) -> None:
        """Verify submit, automatic consumption, data loading, and Recent publication."""
        # [test->req~ring5.ingestion.session-background-parse~1]
        source = Path(__file__).parent / "fixtures" / "background_job_stats"
        assert (source / "run" / "stats.txt").is_file(), "tracked parse fixture is missing"

        data_source = DataSourcePage(tier0_page)
        data_source.navigate()
        data_source.ensure_parse_mode()
        data_source.fill_stats_path(str(source))
        data_source.fill_stats_pattern("stats.txt")
        data_source.parse_and_wait()
        data_source.assert_data_loaded(row_count=1)

        data_source.select_recent_mode()
        expect(data_source.pool_file_count_info).to_be_visible()
