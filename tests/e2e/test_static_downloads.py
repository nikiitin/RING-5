"""Exercise real figure-download bytes through each supported browser exporter."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image, ImageStat
from playwright.sync_api import Page, expect
import pytest

from tests.e2e.conftest import EXPORT_TIMEOUT
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = [pytest.mark.requires_browser, pytest.mark.serial]


@pytest.mark.xdist_group("e2e_static_downloads")
class TestStaticDownloads:
    """Keep Chrome and TeX ownership serial while testing actual UI downloads."""

    @pytest.mark.parametrize(
        ("engine", "file_format"),
        [
            ("plotly", "pdf"),
            ("plotly", "svg"),
            ("plotly", "png"),
            ("matplotlib", "pdf"),
            ("matplotlib", "svg"),
            ("matplotlib", "png"),
            ("matplotlib", "pgf"),
        ],
    )
    def test_selected_exporter_produces_a_real_artifact(
        self, tier2_page: Page, tmp_path: Path, engine: str, file_format: str
    ) -> None:
        manager = ManagePlotsPage(tier2_page)
        manager.navigate()
        manager.select_plot("E2E Bar")
        manager.select_engine(engine)
        manager.open_download_expander(engine, timeout=EXPORT_TIMEOUT)
        option = manager.download_format_pills.get_by_role("radio", name=file_format, exact=True)
        if not option.is_checked():
            option.click()
            manager.wait_for_streamlit(timeout=EXPORT_TIMEOUT, expect_rerun=True)
            manager.open_download_expander(engine, timeout=EXPORT_TIMEOUT)
        expect(option).to_be_checked(timeout=EXPORT_TIMEOUT)
        expect(manager.download_button).to_be_enabled(timeout=EXPORT_TIMEOUT)
        with tier2_page.expect_download(timeout=EXPORT_TIMEOUT) as transfer:
            manager.download_button.click()
        download = transfer.value
        assert download.failure() is None
        assert Path(download.suggested_filename).suffix == f".{file_format}"
        output = tmp_path / download.suggested_filename
        download.save_as(output)
        payload = output.read_bytes()
        assert len(payload) > 1000
        if file_format == "pdf":
            assert payload.startswith(b"%PDF-") and payload.rstrip().endswith(b"%%EOF")
            assert re.search(rb"/Type\s*/Page\b", payload)
        elif file_format == "svg":
            root = ET.fromstring(payload)
            assert root.tag == "{http://www.w3.org/2000/svg}svg"
            assert root.get("viewBox")
            assert root.findall(".//{http://www.w3.org/2000/svg}path")
        elif file_format == "png":
            assert payload.startswith(b"\x89PNG\r\n\x1a\n")
            with Image.open(BytesIO(payload)) as image:
                image.load()
                assert image.width > 100 and image.height > 100
                assert max(ImageStat.Stat(image.convert("RGB")).var) > 1
        else:
            document = payload.decode("utf-8")
            assert "\\begin{pgfpicture}" in document
            assert "\\end{pgfpicture}" in document
            assert "\\pgfpath" in document
        expect(tier2_page.get_by_test_id("stException")).to_have_count(0)
        expect(tier2_page.get_by_test_id("stAlertContentError")).to_have_count(0)
