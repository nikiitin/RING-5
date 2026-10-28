"""Configure every built-in shaper through the UI and verify its published data."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

import pytest
from playwright.sync_api import Locator, Page, expect

from tests.e2e.conftest import E2E_TIMEOUT
from tests.helpers.browser_plot_data import download_processed_csv, read_native_plotly
from tests.visual.pages.data_managers_page import DataManagersPage
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = [pytest.mark.requires_browser, pytest.mark.xdist_group("e2e_shaper_semantics")]

_RESHAPE = (
    "workload,configuration,a,b,note\n"
    "beta,candidate,4,40,keep source intact\n"
    "beta,base,3,30,keep source intact\n"
    "alpha,candidate,2,20,keep source intact\n"
    "alpha,base,1,10,keep source intact\n"
)
_GROUPS = (
    "workload,configuration,seed,a,b\n"
    "alpha,base,s0,2,10\n"
    "alpha,candidate,s0,4,20\n"
    "beta,base,s0,0,30\n"
    "beta,candidate,s0,6,40\n"
    "gamma,base,s0,3,50\n"
)
_REPEATED = (
    "workload,configuration,seed,a,b\n"
    "alpha,base,0,2,10\n"
    "alpha,base,1,4,20\n"
    "alpha,candidate,0,6,30\n"
    "alpha,candidate,1,8,40\n"
)


def _widget(scope: Locator, kind: str, label: str) -> Locator:
    return scope.get_by_test_id(kind).filter(has=scope.page.get_by_text(label, exact=True))


def _select(manager: ManagePlotsPage, scope: Locator, label: str, value: str) -> None:
    manager._open_and_select(_widget(scope, "stSelectbox", label), value)


def _multi(manager: ManagePlotsPage, scope: Locator, label: str, values: list[str]) -> None:
    manager.set_multiselect_values(_widget(scope, "stMultiSelect", label), values)


def _text(manager: ManagePlotsPage, scope: Locator, label: str, value: str) -> None:
    field = scope.get_by_role("textbox", name=label, exact=True)
    if field.input_value() != value:
        field.fill(value)
        field.press("Enter")
    expect(field).to_have_value(value, timeout=E2E_TIMEOUT)


def _number(manager: ManagePlotsPage, scope: Locator, label: str, value: float) -> None:
    field = scope.get_by_role("spinbutton", name=label, exact=True)
    if float(field.input_value()) != value:
        field.fill(str(value))
        field.press("Enter")
    assert float(field.input_value()) == pytest.approx(value)


def _start(page: Page, tmp_path: Path, content: str, name: str) -> ManagePlotsPage:
    path = tmp_path / "measurements.csv"
    path.write_text(content, encoding="utf-8")
    source = DataSourcePage(page)
    source.navigate()
    source.upload_csv(path)
    manager = ManagePlotsPage(page)
    manager.navigate()
    manager.create_plot(name, "bar")
    return manager


def _add(manager: ManagePlotsPage, label: str, index: int) -> Locator:
    manager.add_shaper(label)
    return manager.open_pipeline_step(index)


def _publish(
    manager: ManagePlotsPage, *, x: str, y: str, title: str, color: str | None = None
) -> None:
    manager.finalize_pipeline()
    manager.select_x_axis(x)
    manager.select_y_axis(y)
    if color is not None:
        manager.select_color_by(color)
    manager.viz_title_input.fill(title)
    manager.viz_title_input.press("Enter")
    manager.wait_for_streamlit(expect_rerun=True)
    manager.refresh_plot()
    expect(manager.page.get_by_test_id("stException")).to_have_count(0)
    expect(manager.page.get_by_test_id("stAlertContentError")).to_have_count(0)


def _assert_workspace_unchanged(page: Page, original_csv: str) -> None:
    manager = DataManagersPage(page)
    manager.navigate()
    transfer = manager.download_current_view()
    actual = list(csv.DictReader(StringIO(transfer.path().read_text(encoding="utf-8-sig"))))
    expected = list(csv.DictReader(StringIO(original_csv)))
    assert len(actual) == len(expected)
    for observed, wanted in zip(actual, expected, strict=True):
        assert observed.keys() == wanted.keys()
        for key, value in wanted.items():
            try:
                expected_number = float(value)
            except ValueError:
                assert observed[key] == value
            else:
                assert float(observed[key]) == pytest.approx(expected_number)


class TestReshapingEditors:
    """Select columns, melt, filter, pivot, and sort the published measurements."""

    def test_reshape_filter_and_order_publish_exact_csv(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.shaping.column-selector~1]
        # [test->req~ring5.shaping.pivot-longer~1]
        # [test->req~ring5.shaping.condition-selector~1]
        # [test->req~ring5.shaping.pivot-wider~1]
        # [test->req~ring5.shaping.sort~1]
        manager = _start(tier0_page, tmp_path, _RESHAPE, "Reshape contract")
        step = _add(manager, "Column Selector", 0)
        _multi(manager, step, "Columns to keep", ["workload", "configuration", "a", "b"])

        step = _add(manager, "Pivot Longer (Melt)", 1)
        _multi(manager, step, "Identifier Columns (keep as-is)", ["workload", "configuration"])
        _multi(manager, step, "Value Columns (to unpivot)", ["a", "b"])
        _text(manager, step, "New 'Name' Column", "metric")
        _text(manager, step, "New 'Value' Column", "measurement")

        step = _add(manager, "Filter", 2)
        _select(manager, step, "Column to filter", "measurement")
        _select(manager, step, "Filter mode", "less_or_equal")
        _number(manager, step, "Threshold", 30)

        step = _add(manager, "Pivot Wider", 3)
        _multi(manager, step, "Index Columns", ["workload", "configuration"])
        _select(manager, step, "Columns from", "metric")
        _select(manager, step, "Values from", "measurement")

        step = _add(manager, "Sort", 4)
        _multi(manager, step, "Sort by columns", ["workload", "configuration"])
        # The editor's explicit alphabetical orders must override the reverse
        # encounter order in the source CSV, including the partially missing B.
        _publish(manager, x="workload", y="a", color="configuration", title="Reshaped measurements")
        native = read_native_plotly(tier0_page, "Reshaped measurements", expected_trace_count=2)
        by_name = {trace["name"]: trace["y"] for trace in native["traces"]}
        assert by_name["base"] == pytest.approx([1, 3])
        assert by_name["candidate"] == pytest.approx([2, 4])

        columns, rows = download_processed_csv(manager)
        assert columns == ["workload", "configuration", "a", "b"]
        assert [(row["workload"], row["configuration"]) for row in rows] == [
            ("alpha", "base"),
            ("alpha", "candidate"),
            ("beta", "base"),
            ("beta", "candidate"),
        ]
        assert [float(row["a"]) for row in rows] == pytest.approx([1, 2, 3, 4])
        assert [float(row["b"]) for row in rows[:3]] == pytest.approx([10, 20, 30])
        assert rows[-1]["b"] == ""
        _assert_workspace_unchanged(tier0_page, _RESHAPE)


class TestGroupAndDerivedEditors:
    """Reject incomplete groups, derive ratios, normalize, and retain exact items."""

    def test_group_filters_derive_normalize_and_select_exact_rows(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.shaping.group-cardinality-selector~1]
        # [test->req~ring5.shaping.group-predicate-selector~1]
        # [test->req~ring5.shaping.derive-column~1]
        # [test->req~ring5.shaping.normalize~1]
        # [test->req~ring5.shaping.item-selector~1]
        manager = _start(tier0_page, tmp_path, _GROUPS, "Group contract")
        step = _add(manager, "Group Cardinality Filter", 0)
        _multi(manager, step, "Group by", ["workload"])
        _select(manager, step, "Count distinct values of", "configuration")
        _number(manager, step, "Count", 2)
        _select(manager, step, "Comparison", "eq")

        step = _add(manager, "Group Predicate Filter", 1)
        _multi(manager, step, "Group by", ["workload"])
        _select(manager, step, "Baseline column", "configuration")
        _select(manager, step, "Baseline value", "base")
        _select(manager, step, "Predicate column (tested on the baseline row)", "a")
        _select(manager, step, "Flag group when baseline value is", "zero")
        _select(manager, step, "Action on flagged groups", "drop")

        step = _add(manager, "Derive Column", 2)
        _select(manager, step, "Operation", "scalar")
        _text(manager, step, "New column name", "scaled")
        _select(manager, step, "Source column", "a")
        _select(manager, step, "Operator", "*")
        _number(manager, step, "Value", 10)

        step = _add(manager, "Normalize", 3)
        _multi(manager, step, "Normalizer variables (will be summed)", ["scaled"])
        _multi(manager, step, "Variables to normalize", ["scaled"])
        _select(manager, step, "Normalizer column (baseline identifier)", "configuration")
        _select(manager, step, "Baseline value", "base")
        _multi(manager, step, "Group by", ["workload"])

        step = _add(manager, "Item Selector", 4)
        _select(manager, step, "Column to match", "configuration")
        _select(manager, step, "Match mode", "exact")
        _multi(manager, step, "Values to keep", ["candidate"])
        _publish(manager, x="workload", y="scaled", title="Candidate normalized result")
        native = read_native_plotly(
            tier0_page, "Candidate normalized result", expected_trace_count=1
        )
        assert native["traces"][0]["y"] == pytest.approx([2])
        columns, rows = download_processed_csv(manager)
        assert columns == ["workload", "configuration", "seed", "a", "b", "scaled"]
        assert len(rows) == 1
        row = rows[0]
        assert (row["workload"], row["configuration"], row["seed"]) == ("alpha", "candidate", "s0")
        assert [float(row[column]) for column in ["a", "b", "scaled"]] == pytest.approx([4, 20, 2])
        _assert_workspace_unchanged(tier0_page, _GROUPS)


class TestIndependentColumnGroups:
    """Append real means and normalize one SplitApply group without altering the other."""

    def test_transform_mean_and_split_apply_preserve_independent_measurements(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.shaping.transformer~1]
        # [test->req~ring5.shaping.mean~1]
        # [test->req~ring5.shaping.split-apply~1]
        manager = _start(tier0_page, tmp_path, _REPEATED, "Independent axes contract")
        step = _add(manager, "Transformer", 0)
        _select(manager, step, "Select Variable to Transform", "seed")
        factor = step.get_by_role("radio", name="Factor (String/Categorical)", exact=True)
        if not factor.is_checked():
            factor.click()
            manager.wait_for_streamlit(expect_rerun=True)
        expect(factor).to_be_checked()

        step = _add(manager, "Mean Calculator", 1)
        _select(manager, step, "Mean type", "arithmean")
        _multi(manager, step, "Variables", ["a", "b"])
        _multi(manager, step, "Group by", ["workload", "configuration"])
        _select(manager, step, "Replacing column", "seed")

        step = _add(manager, "Split-Apply (Per-Axis)", 2)
        _multi(
            manager,
            step,
            "Join columns (shared categorical columns)",
            ["workload", "configuration", "seed"],
        )
        group_a = step.get_by_test_id("stExpander").filter(
            has=manager.page.get_by_text("Group A", exact=True)
        )
        group_b = step.get_by_test_id("stExpander").filter(
            has=manager.page.get_by_text("Group B", exact=True)
        )
        _multi(manager, group_a, "Numeric columns", ["a"])
        _multi(manager, group_b, "Numeric columns", ["b"])
        group_a.get_by_role("button", name="+ Add step", exact=True).click()
        manager.wait_for_streamlit(expect_rerun=True)
        _select(manager, group_a, "Transformation", "Normalize")
        _multi(manager, group_a, "Normalizer variables (will be summed)", ["a"])
        _multi(manager, group_a, "Variables to normalize", ["a"])
        _select(manager, group_a, "Normalizer column (baseline identifier)", "configuration")
        _select(manager, group_a, "Baseline value", "base")
        _multi(manager, group_a, "Group by", ["workload", "seed"])
        _publish(
            manager, x="seed", y="a", color="configuration", title="Independent normalized means"
        )

        native = read_native_plotly(
            tier0_page, "Independent normalized means", expected_trace_count=2
        )
        by_name = {trace["name"]: trace["y"] for trace in native["traces"]}
        assert by_name["base"] == pytest.approx([1, 1, 1])
        assert sorted(by_name["candidate"]) == pytest.approx([2, 7 / 3, 3])
        columns, rows = download_processed_csv(manager)
        assert columns == ["workload", "configuration", "seed", "a", "b"]
        assert len(rows) == 6
        actual = {
            (row["configuration"], row["seed"]): (float(row["a"]), float(row["b"])) for row in rows
        }
        expected = {
            ("base", "0"): (1, 10),
            ("base", "1"): (1, 20),
            ("candidate", "0"): (3, 30),
            ("candidate", "1"): (2, 40),
            ("base", "arithmean"): (1, 15),
            ("candidate", "arithmean"): (7 / 3, 35),
        }
        assert actual.keys() == expected.keys()
        for key, values in expected.items():
            assert actual[key] == pytest.approx(values)
        assert {row["workload"] for row in rows} == {"alpha"}
        _assert_workspace_unchanged(tier0_page, _REPEATED)
