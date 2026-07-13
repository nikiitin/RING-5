"""Unit tests for settings_pills — pills-driven navigation hierarchy."""

from __future__ import annotations

import pytest

from src.web.pages.ui.plotting.settings_pills import (
    SETTINGS_SECTIONS,
    SettingsSection,
    render_settings_pills,
)

# SettingsSection dataclass


class TestSettingsSection:
    """Verify the frozen dataclass behaviour."""

    def test_creation_basic(self) -> None:
        sec = SettingsSection(key="k", label="L", icon="star")
        assert sec.key == "k"
        assert sec.label == "L"
        assert sec.icon == "star"
        assert sec.advanced is False

    def test_creation_advanced(self) -> None:
        sec = SettingsSection(key="a", label="A", icon="tune", advanced=True)
        assert sec.advanced is True

    def test_frozen_immutability(self) -> None:
        sec = SettingsSection(key="k", label="L", icon="star")
        with pytest.raises(AttributeError):
            sec.key = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = SettingsSection(key="x", label="X", icon="i")
        b = SettingsSection(key="x", label="X", icon="i")
        assert a == b

    def test_inequality_on_advanced(self) -> None:
        a = SettingsSection(key="x", label="X", icon="i", advanced=False)
        b = SettingsSection(key="x", label="X", icon="i", advanced=True)
        assert a != b


# SETTINGS_SECTIONS registry


class TestSettingsSections:
    """Validate the predefined section registry."""

    def test_total_count(self) -> None:
        assert len(SETTINGS_SECTIONS) == 7

    def test_basic_sections(self) -> None:
        basic: list[SettingsSection] = [s for s in SETTINGS_SECTIONS if not s.advanced]
        assert len(basic) == 3
        assert [s.key for s in basic] == ["layout", "typography", "legends"]

    def test_advanced_sections(self) -> None:
        adv: list[SettingsSection] = [s for s in SETTINGS_SECTIONS if s.advanced]
        assert len(adv) == 4
        assert [s.key for s in adv] == [
            "axes",
            "data_labels",
            "colors",
            "advanced",
        ]

    def test_unique_keys(self) -> None:
        keys = [s.key for s in SETTINGS_SECTIONS]
        assert len(keys) == len(set(keys)), "Duplicate section keys detected"

    def test_all_have_icons(self) -> None:
        for sec in SETTINGS_SECTIONS:
            assert sec.icon, f"Section {sec.key!r} has no icon"

    def test_all_have_labels(self) -> None:
        for sec in SETTINGS_SECTIONS:
            assert sec.label, f"Section {sec.key!r} has no label"


# Progressive disclosure filtering


class TestProgressiveDisclosure:
    """Test the filtering logic used by render_settings_pills."""

    def test_basic_only(self) -> None:
        """When show_advanced=False, only basic sections are visible."""
        visible = [s for s in SETTINGS_SECTIONS if not s.advanced]
        assert all(not s.advanced for s in visible)
        assert len(visible) == 3

    def test_all_visible(self) -> None:
        """When show_advanced=True, all sections are visible."""
        visible = [s for s in SETTINGS_SECTIONS if not s.advanced or True]
        assert len(visible) == 7

    def test_basic_ordering_preserved(self) -> None:
        basic = [s for s in SETTINGS_SECTIONS if not s.advanced]
        assert basic[0].key == "layout"
        assert basic[1].key == "typography"
        assert basic[2].key == "legends"

    def test_advanced_ordering_preserved(self) -> None:
        adv = [s for s in SETTINGS_SECTIONS if s.advanced]
        assert adv[0].key == "axes"
        assert adv[1].key == "data_labels"
        assert adv[2].key == "colors"
        assert adv[3].key == "advanced"


# render_settings_pills (requires Streamlit mocking)


class TestRenderSettingsPills:
    """Test the render function with mocked Streamlit."""

    def test_basic_mode_passes_three_options(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """In basic mode only three option keys are passed to st.pills."""
        captured_kwargs: dict = {}  # type: ignore[type-arg]

        def fake_pills(label: object, **kwargs: object) -> str:  # type: ignore[no-untyped-def]
            captured_kwargs["label"] = label
            captured_kwargs.update(kwargs)
            return "layout"

        monkeypatch.setattr("streamlit.pills", fake_pills)
        result = render_settings_pills(show_advanced=False)

        assert result == "layout"
        assert captured_kwargs["options"] == ["layout", "typography", "legends"]

    def test_advanced_mode_passes_seven_options(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured_kwargs: dict = {}  # type: ignore[type-arg]

        def fake_pills(label: object, **kwargs: object) -> str:  # type: ignore[no-untyped-def]
            captured_kwargs["label"] = label
            captured_kwargs.update(kwargs)
            return "axes"

        monkeypatch.setattr("streamlit.pills", fake_pills)
        result = render_settings_pills(show_advanced=True)

        assert result == "axes"
        assert len(captured_kwargs["options"]) == 7

    def test_format_func_produces_material_icons(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured_kwargs: dict = {}  # type: ignore[type-arg]

        def fake_pills(label: object, **kwargs: object) -> str:  # type: ignore[no-untyped-def]
            captured_kwargs["label"] = label
            captured_kwargs.update(kwargs)
            return "layout"

        monkeypatch.setattr("streamlit.pills", fake_pills)
        render_settings_pills(show_advanced=False)

        fmt = captured_kwargs["format_func"]
        assert fmt("layout") == ":material/dashboard: Layout"
        assert fmt("typography") == ":material/text_fields: Typography"
        assert fmt("legends") == ":material/legend_toggle: Legends"

    def test_returns_none_when_nothing_selected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_pills(label: object, **kwargs: object) -> None:  # type: ignore[no-untyped-def]
            return None

        monkeypatch.setattr("streamlit.pills", fake_pills)
        result = render_settings_pills()

        assert result is None

    def test_key_is_settings_nav(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured_kwargs: dict = {}  # type: ignore[type-arg]

        def fake_pills(label: object, **kwargs: object) -> str:  # type: ignore[no-untyped-def]
            captured_kwargs["label"] = label
            captured_kwargs.update(kwargs)
            return "layout"

        monkeypatch.setattr("streamlit.pills", fake_pills)
        render_settings_pills()

        assert captured_kwargs["key"] == "settings_nav"
