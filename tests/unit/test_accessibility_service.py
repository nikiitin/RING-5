"""Accessible defaults, contrast validation, and redundant mark encodings."""

import pytest

from src.core.models import AccessibilityFinding, AccessibilityReport
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
)
from src.core.services.visualization.accessibility_service import AccessibilityService


def test_accessible_defaults_are_explicit_and_do_not_mutate_input() -> None:
    # [test->req~ring5.figure.accessible-themes~1]
    source = {"accessibility_mode": True, "x": "phase", "y": "ipc"}
    accessible = AccessibilityService.apply_defaults(source, "line")

    assert source == {"accessibility_mode": True, "x": "phase", "y": "ipc"}
    assert accessible["color_palette"] == "ring5_accessible"
    assert accessible["show_markers"] is True
    assert accessible["marker_size"] == 7
    assert accessible["xaxis_tickfont_size"] == 12
    assert AccessibilityService.apply_defaults(source | {"accessibility_mode": False}, "line") == (
        source | {"accessibility_mode": False}
    )


def test_accessible_profile_passes_color_contrast_and_redundancy_audit() -> None:
    # [test->req~ring5.figure.accessible-themes~1]
    config = AccessibilityService.apply_defaults({"accessibility_mode": True}, "bar")
    report = AccessibilityService.audit(config, "bar", series_count=8)

    assert report.passed
    assert report.palette_colorblind_safe
    assert report.non_color_encodings
    assert report.minimum_contrast_ratio == pytest.approx(3.87)
    assert report.findings == ()
    assert report.to_frame().empty


def test_audit_exposes_unsafe_palette_contrast_text_and_encoding_issues() -> None:
    # [test->req~ring5.figure.accessible-themes~1]
    report = AccessibilityService.audit(
        {
            "color_palette": "Pastel",
            "plot_bgcolor": "#ffffff",
            "paper_bgcolor": "#ffffff",
            "axis_color": "#dddddd",
            "legend_font_color": "#dddddd",
            "xaxis_tickfont_size": 8,
            "yaxis_tickfont_size": 8,
        },
        "line",
        series_count=3,
    )

    assert not report.passed
    assert report.issue_count >= 5
    assert not report.palette_colorblind_safe
    assert not report.non_color_encodings
    assert {finding.component for finding in report.findings} >= {
        "palette",
        "axis and labels",
        "series encoding",
        "axis tick text",
    }
    assert len(report.to_frame()) == report.issue_count

    unsupported = AccessibilityService.audit(
        {"accessibility_mode": True},
        "box",
        series_count=2,
    )
    overcrowded = AccessibilityService.audit(
        {"accessibility_mode": True},
        "bar",
        series_count=9,
    )
    assert not unsupported.non_color_encodings
    assert "does not yet provide" in unsupported.findings[-1].message
    assert "no more than eight" in overcrowded.findings[-1].message


def test_non_color_encodings_are_engine_independent_and_non_mutating() -> None:
    # [test->req~ring5.figure.accessible-themes~1]
    source = TraceBuildResult(
        traces=[
            BarTraceConfig(name="bars"),
            LineTraceConfig(name="line", show_markers=False),
            ScatterTraceConfig(name="points"),
        ]
    )
    accessible = AccessibilityService.apply_non_color_encodings(
        source, {"accessibility_mode": True}
    )

    assert source.traces[0] == BarTraceConfig(name="bars")
    assert isinstance(accessible.traces[0], BarTraceConfig)
    assert accessible.traces[0].pattern == "/"
    assert accessible.traces[0].border_width == 1.0
    assert isinstance(accessible.traces[1], LineTraceConfig)
    assert accessible.traces[1].show_markers
    assert accessible.traces[1].marker_symbol == "square"
    assert isinstance(accessible.traces[2], ScatterTraceConfig)
    assert accessible.traces[2].marker_symbol == "diamond"
    assert accessible.traces[2].marker_line_width == 1.0
    assert (
        AccessibilityService.apply_non_color_encodings(source, {"accessibility_mode": False})
        is source
    )


def test_wcag_contrast_and_audit_input_validation() -> None:
    # [test->req~ring5.figure.accessible-themes~1]
    assert AccessibilityService.contrast_ratio("#000", "rgb(255, 255, 255)") == pytest.approx(21.0)
    assert AccessibilityService.contrast_ratio("rgba(0, 0, 0, 1)", "white") == pytest.approx(21.0)
    with pytest.raises(ValueError, match="opaque"):
        AccessibilityService.contrast_ratio("rgba(0, 0, 0, 0)", "white")
    with pytest.raises(TypeError, match="dictionary"):
        AccessibilityService.audit([], "line")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="plot type"):
        AccessibilityService.audit({}, "")
    with pytest.raises(ValueError, match="positive integer"):
        AccessibilityService.audit({}, "line", series_count=0)


def test_accessibility_report_counts_only_errors_and_warnings() -> None:
    report = AccessibilityReport(
        palette_name="custom",
        palette_colorblind_safe=False,
        non_color_encodings=False,
        minimum_contrast_ratio=2.0,
        findings=(
            AccessibilityFinding("error", "marks", "Increase contrast.", 2.0),
            AccessibilityFinding("warning", "text", "Increase text size."),
        ),
    )

    assert not report.passed
    assert report.issue_count == 2
    assert list(report.to_frame()["severity"]) == ["error", "warning"]
