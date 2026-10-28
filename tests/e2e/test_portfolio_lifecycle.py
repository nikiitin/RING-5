"""Transfer, authenticate, replay, and publish work created through the browser."""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
from io import StringIO
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from playwright.sync_api import Locator, Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.helpers.browser_plot_data import read_native_plotly
from tests.helpers.html_assertions import assert_plotly_document
from tests.visual.pages.data_managers_page import DataManagersPage
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage
from tests.visual.pages.portfolio_page import PortfolioPage

pytestmark = pytest.mark.requires_browser

_SOURCE = "benchmark,ipc\nalpha,1.25\nbeta,2.5\n"
_REPLACEMENT = "benchmark,ipc\nreplacement,99\n"
_PLOT = "Portable IPC"
_TITLE = "Exact portable IPC observations"
_SECRET = "browser-test-shared-secret-keep-out-of-portfolios"


def _rows(page: Page) -> list[dict[str, str]]:
    manager = DataManagersPage(page)
    manager.navigate()
    download = manager.download_current_view()
    assert download.failure() is None
    return list(csv.DictReader(StringIO(download.path().read_text(encoding="utf-8-sig"))))


def _assert_rows(actual: list[dict[str, str]], source: str) -> None:
    expected = list(csv.DictReader(StringIO(source)))
    assert len(actual) == len(expected)
    for row, wanted in zip(actual, expected, strict=True):
        assert row.keys() == wanted.keys()
        assert row["benchmark"] == wanted["benchmark"]
        assert float(row["ipc"]) == pytest.approx(float(wanted["ipc"]))


def _prepare_plot(page: Page, directory: Path) -> tuple[ManagePlotsPage, Path]:
    """Create the complete current writer input through upload and plotting controls."""
    source_path = directory / "measurements.csv"
    source_path.write_text(_SOURCE, encoding="utf-8")
    source = DataSourcePage(page)
    source.navigate()
    source.upload_csv(source_path)
    plots = ManagePlotsPage(page)
    plots.navigate()
    plots.create_plot(_PLOT, "bar")
    plots.add_shaper("Sort")
    plots.finalize_pipeline()
    plots.select_x_axis("benchmark")
    plots.select_y_axis("ipc")
    plots.viz_title_input.fill(_TITLE)
    plots.viz_title_input.press("Enter")
    plots.wait_for_streamlit(expect_rerun=True)
    plots.refresh_plot()
    _assert_native(page)
    return plots, source_path


def _assert_native(page: Page) -> None:
    plots = ManagePlotsPage(page)
    plots.navigate()
    plots.select_plot(_PLOT)
    plots.select_engine("plotly")
    native = read_native_plotly(page, _TITLE, expected_trace_count=1)
    assert native["traces"][0]["type"] == "bar"
    assert native["traces"][0]["y"] == pytest.approx([1.25, 2.5])
    expect(plots.plot_selector_pills.get_by_role("radio")).to_have_count(1)


def _replace_workspace(page: Page, directory: Path) -> None:
    source = DataSourcePage(page)
    source.reset_all()
    source.navigate()
    replacement = directory / "replacement.csv"
    replacement.write_text(_REPLACEMENT, encoding="utf-8")
    source.upload_csv(replacement)
    _assert_rows(_rows(page), _REPLACEMENT)


def _radio(owner: PortfolioPage, scope: Locator, label: str, option: str) -> None:
    control = scope.get_by_role("radiogroup", name=label, exact=True).get_by_role(
        "radio", name=option, exact=True
    )
    if not control.is_checked():
        with owner.expect_script_rerun():
            control.press("Space")
    expect(control).to_be_checked(timeout=E2E_TIMEOUT)


def _capture_recipe(portfolio: PortfolioPage, name: str) -> dict[str, Any]:
    portfolio.open_analysis_recipes()
    scope = portfolio.analysis_recipes_expander
    scope.get_by_role("tab", name="Save current", exact=True).click()
    portfolio.set_checkbox(scope, "Download each current plot when the recipe runs", True)
    engine = scope.get_by_test_id("stSelectbox").filter(
        has=portfolio.page.get_by_text("Download engine", exact=True)
    )
    portfolio._open_and_select(engine, "plotly")
    file_format = scope.get_by_test_id("stSelectbox").filter(
        has=portfolio.page.get_by_text("File format", exact=True)
    )
    portfolio._open_and_select(file_format, "html")
    portfolio.save_current_as_recipe(name)
    portfolio.select_saved_recipe(name)
    download = portfolio.download_recipe_artifact("json")
    document = json.loads(download.path().read_text(encoding="utf-8"))
    assert document["format"] == "ring5.analysis-recipe"
    assert document["source"]["path"] == "{{source_path}}"
    assert {item["name"]: item["type"] for item in document["parameters"]} == {
        "source_path": "path",
        "output_dir": "path",
    }
    assert len(document["plots"]) == len(document["exports"]) == 1
    assert document["exports"][0]["engine"] == "plotly"
    assert document["exports"][0]["format"] == "html"
    return document


@pytest.mark.xdist_group("e2e_portable_bundle_lifecycle")
class TestPortableBundleLifecycle:
    """Validated bundles remain read-only until an explicit restore succeeds."""

    def test_bundle_review_tamper_rejection_and_exact_restore(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.portfolio.portable-bundles~1]
        page = tier0_page
        _prepare_plot(page, tmp_path)
        portfolio = PortfolioPage(page)
        portfolio.navigate()
        portfolio.save_portfolio("Browser portable roundtrip")
        bundle_path = tmp_path / "portable.ring5-bundle"
        portfolio.download_portable_bundle(bundle_path)
        with ZipFile(bundle_path) as archive:
            contents = {name: archive.read(name) for name in archive.namelist()}
        manifest = json.loads(contents["manifest.json"])
        assert manifest["format"] == "ring5.portfolio-bundle"
        assert "portfolio/portfolio.json" in contents
        assert len(manifest["members"]) >= 4

        _replace_workspace(page, tmp_path)
        source = DataSourcePage(page)
        source.navigate()
        unsupported = tmp_path / "unsupported.txt"
        unsupported.write_text(_SOURCE, encoding="utf-8")
        source.select_csv_mode()
        source.browser_upload_input.set_input_files(str(unsupported))
        expect(source.upload_validation_error).to_contain_text(
            "Upload filename must end in .csv, .json, .xlsx, or .ring5-bundle.",
            timeout=E2E_TIMEOUT,
        )
        _assert_rows(_rows(page), _REPLACEMENT)

        source.navigate()
        source.upload_for_review(bundle_path)
        expect(
            page.get_by_role("heading", name="Review portable bundle restoration", exact=True)
        ).to_be_visible()
        expect(
            page.get_by_role("button", name=re.compile(r"(?:^|\s)Restore portable bundle$"))
        ).to_be_enabled()
        _assert_rows(_rows(page), _REPLACEMENT)

        # Alter only one declared checksum; preserve every carried byte so the
        # rejection specifically exercises the bundle manifest's trust boundary.
        manifest["members"][0]["sha256"] = "0" * 64
        contents["manifest.json"] = json.dumps(manifest).encode("utf-8")
        modified = tmp_path / "modified.ring5-bundle"
        with ZipFile(modified, "w", ZIP_DEFLATED) as archive:
            for name, payload in contents.items():
                archive.writestr(name, payload)
        source.navigate()
        source.select_csv_mode()
        source.browser_upload_input.set_input_files(str(modified))
        expect(source.upload_validation_error).to_be_visible(timeout=E2E_TIMEOUT)
        expect(
            page.get_by_role("button", name=re.compile(r"(?:^|\s)Restore portable bundle$"))
        ).to_have_count(0)
        _assert_rows(_rows(page), _REPLACEMENT)

        source.navigate()
        source.upload_for_review(bundle_path)
        page.get_by_role("button", name=re.compile(r"(?:^|\s)Restore portable bundle$")).click()
        source.wait_for_streamlit(expect_rerun=True)
        _assert_rows(_rows(page), _SOURCE)
        _assert_native(page)
        expect(page.get_by_test_id("stException")).to_have_count(0)


@pytest.mark.xdist_group("e2e_signed_portfolio_lifecycle")
class TestSignedPortfolioLifecycle:
    """Only the matching shared secret may authenticate the browser-generated document."""

    def test_signed_save_wrong_secret_rejection_then_exact_authenticated_restore(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.portfolio.signed-manifests~1]
        page = tier0_page
        _prepare_plot(page, tmp_path)
        portfolio = PortfolioPage(page)
        portfolio.navigate()
        portfolio.save_portfolio("Browser signed roundtrip", signing_secret=_SECRET)
        bundle_path = tmp_path / "signed.ring5-bundle"
        portfolio.download_portable_bundle(bundle_path)
        with ZipFile(bundle_path) as archive:
            signed_bytes = archive.read("portfolio/portfolio.json")
        assert _SECRET.encode("utf-8") not in signed_bytes
        assert json.loads(signed_bytes)["integrity_manifest"]["signature"]
        signed_path = tmp_path / "signed-portfolio.json"
        signed_path.write_bytes(signed_bytes)
        _replace_workspace(page, tmp_path)

        source = DataSourcePage(page)
        source.navigate()
        source.upload_for_review(signed_path, interpretation="RING-5 portfolio")
        restore = page.get_by_role(
            "button", name=re.compile(r"(?:^|\s)Restore uploaded portfolio$")
        )
        expect(restore).to_be_disabled()
        secret = page.get_by_role("textbox", name="Portfolio signing secret", exact=True)
        secret.fill("incorrect-browser-test-secret")
        with source.expect_script_rerun():
            secret.press("Enter")
        expect(restore).to_be_enabled(timeout=E2E_TIMEOUT)
        with source.expect_script_rerun():
            restore.click()
        expect(
            page.get_by_test_id("stAlertContentError").filter(
                has_text="Portfolio restoration failed:"
            )
        ).to_be_visible(timeout=E2E_TIMEOUT)
        _assert_rows(_rows(page), _REPLACEMENT)

        source.navigate()
        source.upload_for_review(signed_path, interpretation="RING-5 portfolio")
        secret.fill(_SECRET)
        with source.expect_script_rerun():
            secret.press("Enter")
        expect(restore).to_be_enabled(timeout=E2E_TIMEOUT)
        with source.expect_script_rerun():
            restore.click()
        _assert_rows(_rows(page), _SOURCE)
        _assert_native(page)
        expect(page.get_by_test_id("stException")).to_have_count(0)


@pytest.mark.xdist_group("e2e_recipe_exchange_lifecycle")
class TestAnalysisRecipeExchange:
    """Imported current recipes obey explicit conflict, version, replacement, and deletion rules."""

    def test_recipe_download_import_conflict_replace_version_rejection_and_delete(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.portfolio.analysis-recipes~1]
        page = tier0_page
        _prepare_plot(page, tmp_path)
        portfolio = PortfolioPage(page)
        portfolio.navigate()
        document = _capture_recipe(portfolio, "Browser original recipe")
        document["name"] = "Browser imported recipe"
        document["description"] = "Imported through the actual recipe uploader"
        imported = tmp_path / "imported.ring5-recipe.json"
        imported.write_text(json.dumps(document), encoding="utf-8")
        portfolio.import_recipe(imported)
        expect(
            page.get_by_test_id("stAlertContentSuccess").filter(has_text="Imported analysis recipe")
        ).to_be_visible()
        portfolio.select_saved_recipe(document["name"])
        assert json.loads(portfolio.download_recipe_artifact("json").path().read_text()) == document

        changed = {**document, "description": "Explicitly replaced description"}
        collision = tmp_path / "collision.ring5-recipe.json"
        collision.write_text(json.dumps(changed), encoding="utf-8")
        portfolio.import_recipe(collision)
        expect(
            page.get_by_test_id("stAlertContentError").filter(has_text="already exists")
        ).to_be_visible()
        portfolio.select_saved_recipe(document["name"])
        assert json.loads(portfolio.download_recipe_artifact("json").path().read_text()) == document
        portfolio.import_recipe(collision, overwrite=True)
        portfolio.select_saved_recipe(document["name"])
        assert json.loads(portfolio.download_recipe_artifact("json").path().read_text()) == changed

        unsupported = {
            **changed,
            "schema_version": document["schema_version"] + 1,
            "name": "Unsupported browser recipe",
        }
        invalid = tmp_path / "unsupported.ring5-recipe.json"
        invalid.write_text(json.dumps(unsupported), encoding="utf-8")
        portfolio.import_recipe(invalid)
        expect(
            page.get_by_test_id("stAlertContentError").filter(
                has_text="Unsupported analysis recipe schema version"
            )
        ).to_be_visible()
        portfolio.select_saved_recipe(document["name"])
        assert json.loads(portfolio.download_recipe_artifact("json").path().read_text()) == changed
        portfolio.recipe_delete_button.click()
        portfolio.wait_for_streamlit(expect_rerun=True)
        portfolio.select_saved_recipe("Browser original recipe")
        assert (
            json.loads(portfolio.download_recipe_artifact("json").path().read_text())["name"]
            == "Browser original recipe"
        )
        portfolio.open_analysis_recipes()
        control = portfolio.saved_recipe_selectbox.get_by_role("combobox")
        control.press("ArrowDown")
        expect(
            page.get_by_role("option", name="Browser original recipe", exact=True)
        ).to_be_visible()
        expect(
            page.get_by_role("option", name="Browser imported recipe", exact=True)
        ).to_have_count(0)
        expect(
            page.get_by_role("option", name="Unsupported browser recipe", exact=True)
        ).to_have_count(0)
        control.press("Escape")
        _assert_rows(_rows(page), _SOURCE)
        _assert_native(page)


@pytest.mark.serial
@pytest.mark.xdist_group("e2e_downloaded_recipe_execution")
class TestDownloadedRecipeExecution:
    """Execute the browser's own script in a separate bounded process and working directory."""

    def test_downloaded_python_runs_typed_source_and_output_arguments(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.automation.script-notebook-export~1]
        page = tier0_page
        _, source_path = _prepare_plot(page, tmp_path)
        portfolio = PortfolioPage(page)
        portfolio.navigate()
        document = _capture_recipe(portfolio, "Browser executable recipe")
        transfer = portfolio.download_recipe_artifact("python")
        outside = tmp_path / "outside-checkout"
        outside.mkdir()
        script_path = outside / transfer.suggested_filename
        transfer.save_as(str(script_path))
        script = script_path.read_text(encoding="utf-8")
        assert "from src." not in script and "import ring5" in script
        output = outside / "figures"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
        environment["RING5_DATA_DIR"] = str(outside / "private-workspace")
        completed = subprocess.run(  # noqa: S603
            [
                sys.executable,
                str(script_path),
                "--source-path",
                str(source_path),
                "--output-dir",
                str(output),
            ],
            cwd=outside,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        summary = json.loads(completed.stdout)
        assert summary["recipe"] == document["name"]
        assert summary["rows"] == 2 and summary["columns"] == ["benchmark", "ipc"]
        assert summary["plots"] == [_PLOT]
        assert summary["parameters"] == {"source_path": str(source_path), "output_dir": str(output)}
        assert len(summary["exports"]) == 1
        written = Path(summary["exports"][0])
        assert written.is_relative_to(output) and written.suffix == ".html"
        assert_plotly_document(written.read_bytes())
        offline = page.context.new_page()
        try:
            offline.goto(written.as_uri(), wait_until="load")
            native = read_native_plotly(offline, _TITLE, expected_trace_count=1)
            assert native["traces"][0]["y"] == pytest.approx([1.25, 2.5])
        finally:
            offline.close()
        _assert_rows(_rows(page), _SOURCE)


@pytest.mark.xdist_group("e2e_publication_report_artifacts")
class TestPublicationReportArtifacts:
    """Download real interactive, publication HTML, and PDF reports from the same workspace."""

    def test_report_modes_have_real_content_and_changed_settings_hide_stale_downloads(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.export.batch-reports~1]
        # [test->req~ring5.export.interactive-gallery~1]
        page = tier0_page
        _prepare_plot(page, tmp_path)
        portfolio = PortfolioPage(page)
        portfolio.navigate()
        portfolio.open_report_composer()
        portfolio.report_title_input.fill("Browser publication report")
        portfolio.report_narrative_input.fill("Measured IPC: alpha 1.25; beta 2.5.")
        portfolio.build_report_button.click()
        expect(portfolio.download_html_gallery_button).to_be_visible(timeout=CHART_TIMEOUT)
        with page.expect_download(timeout=E2E_TIMEOUT) as pending:
            portfolio.download_html_gallery_button.click()
        gallery = page.context.new_page()
        try:
            gallery.set_content(pending.value.path().read_text(encoding="utf-8"), wait_until="load")
            native = read_native_plotly(gallery, _TITLE, expected_trace_count=1)
            assert native["traces"][0]["y"] == pytest.approx([1.25, 2.5])
            expect(gallery.locator("[data-ring5-gallery-item]")).to_have_count(1)
            with gallery.expect_download(timeout=E2E_TIMEOUT) as source_transfer:
                gallery.get_by_role(
                    "button", name="Download source data as CSV", exact=True
                ).click()
            _assert_rows(
                list(
                    csv.DictReader(
                        StringIO(source_transfer.value.path().read_text(encoding="utf-8-sig"))
                    )
                ),
                _SOURCE,
            )
        finally:
            gallery.close()

        portfolio.report_title_input.fill("Revised browser publication report")
        portfolio.report_title_input.press("Tab")
        portfolio.wait_for_streamlit(expect_rerun=True)
        expect(portfolio.download_html_gallery_button).to_have_count(0)
        expect(
            page.get_by_text("Report settings changed. Build again before downloading.", exact=True)
        ).to_be_visible()
        _radio(portfolio, portfolio.report_expander, "HTML experience", "Publication document")
        portfolio.build_report_button.click()
        expect(portfolio.download_html_report_button).to_be_visible(timeout=CHART_TIMEOUT)
        with page.expect_download(timeout=E2E_TIMEOUT) as document_transfer:
            portfolio.download_html_report_button.click()
        publication = page.context.new_page()
        try:
            publication.set_content(
                document_transfer.value.path().read_text(encoding="utf-8"), wait_until="load"
            )
            expect(
                publication.get_by_role(
                    "heading", name="Revised browser publication report", exact=True
                )
            ).to_be_visible()
            expect(
                publication.get_by_text("Measured IPC: alpha 1.25; beta 2.5.", exact=True)
            ).to_be_visible()
            images = publication.locator("figure img")
            expect(images).to_have_count(1)
            expect(images.first).to_have_js_property("complete", True)
            assert images.first.evaluate(
                "image => image.naturalWidth > 100 && image.naturalHeight > 100"
            )
            expect(
                publication.get_by_role("heading", name="Data provenance", exact=True)
            ).to_be_visible()
            expect(
                publication.get_by_role("heading", name="Execution environment", exact=True)
            ).to_be_visible()
        finally:
            publication.close()

        _radio(portfolio, portfolio.report_expander, "Report format", "PDF")
        expect(portfolio.download_html_report_button).to_have_count(0)
        portfolio.build_report_button.click()
        pdf_button = page.get_by_role("button", name="Download PDF report", exact=True)
        expect(pdf_button).to_be_visible(timeout=CHART_TIMEOUT)
        with page.expect_download(timeout=E2E_TIMEOUT) as pdf_transfer:
            pdf_button.click()
        payload = pdf_transfer.value.path().read_bytes()
        assert payload.startswith(b"%PDF-") and payload.rstrip().endswith(b"%%EOF")
        assert len(re.findall(rb"/Type\s*/Page\b", payload)) >= 5
        assert b"/Title (Revised browser publication report)" in payload
        _assert_rows(_rows(page), _SOURCE)
        expect(page.get_by_test_id("stException")).to_have_count(0)
