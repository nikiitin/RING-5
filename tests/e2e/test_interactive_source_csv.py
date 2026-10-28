"""Real offline CSV download preserves the full source table beyond its display view."""

from __future__ import annotations

import csv
from io import StringIO

import pandas as pd
import pytest
from playwright.sync_api import Page, expect

from src.web.rendering.interactive_html_export import (
    interactive_source_data_assets,
    interactive_source_data_section,
)

pytestmark = pytest.mark.requires_browser


def test_offline_source_csv_retains_missing_values_precision_and_original_rows(page: Page) -> None:
    source = pd.DataFrame(
        {
            "measurement": [0.12345678901234566, 1e-30, -0.0],
            "identifier": [2**63 - 1, 2**53 + 1, 2**53 + 3],
            "optional": [None, "—", "ordinary"],
            "recorded": pd.to_datetime(
                [
                    "2026-10-28T12:34:56.123456789Z",
                    "2026-10-28T12:34:56.000000001Z",
                    "2026-10-28T12:34:56.999999999Z",
                ]
            ),
            "description": ['</script><img src=x> & "quoted",\r\nsecond line', "middle", "last"],
        }
    )
    style, script = interactive_source_data_assets()
    section = interactive_source_data_section(source)
    page.route("**/*", lambda route: route.abort())
    page.set_content(
        f"<html><head><style>{style}</style></head><body>{section}"
        f"<script>{script}</script></body></html>"
    )
    table = page.get_by_role("region", name="Interactive source dataframe")
    expect(table.locator("tbody tr")).to_have_count(3)
    expect(table.locator("tbody tr").first.locator("td").nth(2)).to_have_text("—")
    expect(page.locator("img")).to_have_count(0)
    page.get_by_role("searchbox", name="Filter rows").fill("ordinary")
    expect(table.locator("tbody tr")).to_have_count(1)
    page.get_by_role("button", name="measurement", exact=True).click()
    with page.expect_download() as transfer:
        page.get_by_role("button", name="Download source data as CSV", exact=True).click()
    downloaded = transfer.value
    assert downloaded.failure() is None
    reader = csv.DictReader(StringIO(downloaded.path().read_bytes().decode("utf-8"), newline=""))
    rows = list(reader)
    assert reader.fieldnames == source.columns.tolist()
    assert len(rows) == 3
    assert [row["measurement"] for row in rows] == ["0.12345678901234566", "1e-30", "-0.0"]
    assert [row["identifier"] for row in rows] == [str(2**63 - 1), str(2**53 + 1), str(2**53 + 3)]
    assert [row["optional"] for row in rows] == ["", "—", "ordinary"]
    assert [row["recorded"] for row in rows] == [str(value) for value in source["recorded"]]
    assert [row["description"] for row in rows] == source["description"].tolist()
