"""Interactive HTML exports keep scientific CSV values separate from display formatting."""

from __future__ import annotations

import csv
from io import StringIO
import json

import pandas as pd

from src.web.rendering.interactive_html_export import _json_payload


def test_embedded_csv_preserves_source_precision_missing_cells_and_safe_text() -> None:
    source = pd.DataFrame(
        {
            "measurement": [0.12345678901234566, 1e-30, -0.0],
            "identifier": [2**63 - 1, 2**53 + 1, 2**53 + 3],
            "optional": [None, "—", ""],
            "recorded": pd.to_datetime(
                [
                    "2026-10-28T12:34:56.123456789Z",
                    "2026-10-28T12:34:56.000000001Z",
                    "2026-10-28T12:34:56.999999999Z",
                ]
            ),
            "description": [
                '</script><img src=x> & "quoted",\r\nsecond line',
                "ordinary",
                "\u2028\u2029",
            ],
        }
    )
    before = source.copy(deep=True)
    encoded = _json_payload(source)
    assert "</script>" not in encoded and "<img" not in encoded and "&" not in encoded
    assert "\u2028" not in encoded and "\u2029" not in encoded
    payload = json.loads(encoded)
    reader = csv.DictReader(StringIO(payload["csv"], newline=""))
    rows = list(reader)
    assert reader.fieldnames == source.columns.tolist()
    assert [row["measurement"] for row in rows] == ["0.12345678901234566", "1e-30", "-0.0"]
    assert [row["identifier"] for row in rows] == [str(2**63 - 1), str(2**53 + 1), str(2**53 + 3)]
    assert [row["optional"] for row in rows] == ["", "—", ""]
    assert [row["recorded"] for row in rows] == [str(value) for value in source["recorded"]]
    assert [row["description"] for row in rows] == source["description"].tolist()
    pd.testing.assert_frame_equal(source, before)
