"""Figure-theme registry, customization, and portable JSON tests."""

from __future__ import annotations

import json

import pytest

from src.core.models import FigureTheme
from src.core.services.visualization.accessibility_service import AccessibilityService
from src.core.services.visualization.figure_theme_service import FigureThemeService


def test_built_in_themes_cover_each_context_and_pass_accessibility_audit() -> None:
    # [test->req~ring5.figure.theme-presets~1]
    themes = FigureThemeService.available_themes()

    assert [theme.identifier for theme in themes] == [
        "paper",
        "presentation",
        "dashboard",
        "dark",
    ]
    assert {theme.context for theme in themes} == {
        "paper",
        "presentation",
        "dashboard",
        "dark",
    }
    for theme in themes:
        config = FigureThemeService.apply({}, theme, "line")
        report = AccessibilityService.audit(config, "line", series_count=2)
        assert report.passed, (theme.identifier, report.findings)
    assert FigureThemeService.get("dark").config["plot_bgcolor"] == "#202633"

    themes[0].config["width"] = 1
    assert FigureThemeService.get("paper").config["width"] == 700


def test_apply_changes_only_appearance_and_does_not_mutate_inputs() -> None:
    # [test->req~ring5.figure.theme-presets~1]
    source = {
        "x": "phase",
        "y": "ipc",
        "color": "variant",
        "x_filter": ["warmup"],
        "title_font_size": 9,
    }
    themed = FigureThemeService.apply(source, "presentation", "bar")

    assert source["title_font_size"] == 9
    assert themed["x"] == "phase"
    assert themed["y"] == "ipc"
    assert themed["color"] == "variant"
    assert themed["x_filter"] == ["warmup"]
    assert themed["title_font_size"] == 30
    assert themed["figure_theme_id"] == "presentation"
    assert themed["enable_stripes"] is True


def test_customize_accepts_appearance_overrides_and_rejects_data_keys() -> None:
    # [test->req~ring5.figure.theme-presets~1]
    custom = FigureThemeService.customize(
        "paper",
        {"title_font_size": 21, "height": 450},
        name="Lab Paper",
    )

    assert custom.identifier == "lab-paper"
    assert custom.context == "paper"
    assert custom.config["title_font_size"] == 21
    assert custom.config["height"] == 450
    assert FigureThemeService.get("paper").config["title_font_size"] == 18

    with pytest.raises(ValueError, match="cannot contain data"):
        FigureThemeService.customize("paper", {"x": "secret"}, name="Unsafe")
    with pytest.raises(ValueError, match="1 to 80"):
        FigureThemeService.customize("paper", {}, name="")


def test_theme_json_round_trip_is_deterministic_and_excludes_live_data_config() -> None:
    # [test->req~ring5.figure.theme-presets~1]
    theme = FigureThemeService.from_config(
        "Reviewed dashboard",
        {
            "x": "phase",
            "y": "ipc",
            "title_font_size": 20,
            "paper_bgcolor": "#ffffff",
            "series_styles": {"candidate": {"color": "#ff0000"}},
        },
        context="dashboard",
    )
    first = FigureThemeService.dumps(theme)
    second = FigureThemeService.dumps(theme)
    restored = FigureThemeService.loads(first)

    assert first == second
    assert restored == theme
    assert restored.config == {
        "title_font_size": 20,
        "paper_bgcolor": "#ffffff",
    }
    assert json.loads(first)["schema_version"] == 1


def test_theme_import_rejects_unbounded_invalid_or_unsafe_documents() -> None:
    # [test->req~ring5.figure.theme-presets~1]
    with pytest.raises(TypeError, match="text or bytes"):
        FigureThemeService.loads({})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="256 KiB"):
        FigureThemeService.loads(b"x" * (256 * 1024 + 1))
    with pytest.raises(ValueError, match="UTF-8 JSON"):
        FigureThemeService.loads(b"not-json")
    with pytest.raises(ValueError, match="one object"):
        FigureThemeService.loads("[]")

    document = json.loads(FigureThemeService.dumps(FigureThemeService.get("paper")))
    document["schema_version"] = 2
    with pytest.raises(ValueError, match="schema version"):
        FigureThemeService.loads(json.dumps(document))
    document["schema_version"] = 1
    document["config"]["x"] = "private-column"
    with pytest.raises(ValueError, match="cannot contain data"):
        FigureThemeService.loads(json.dumps(document))
    document["config"].pop("x")
    document["config"]["paper_bgcolor"] = "javascript:alert(1)"
    with pytest.raises(ValueError, match="CSS color"):
        FigureThemeService.loads(json.dumps(document))

    document["config"]["paper_bgcolor"] = "#ffffff"
    document["config"]["width"] = -1
    with pytest.raises(ValueError, match="must be positive"):
        FigureThemeService.loads(json.dumps(document))
    document["config"]["width"] = 700
    document["config"]["accessibility_mode"] = "yes"
    with pytest.raises(ValueError, match="true or false"):
        FigureThemeService.loads(json.dumps(document))

    invalid = FigureTheme("UPPER", "Bad", "paper", "", {})
    with pytest.raises(ValueError, match="lowercase portable"):
        FigureThemeService.validate(invalid)
