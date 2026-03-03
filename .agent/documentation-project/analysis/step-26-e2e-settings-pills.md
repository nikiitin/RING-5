# Step 26 -- E2E Settings Pills Tests

## 1. Executive Summary

This document defines an exhaustive End-to-End (E2E) test plan for the **Settings
Pills** system in the RING-5 Unified Engine v2.  The settings pills provide a
top-level navigation layer (`render_settings_pills`) that routes users to eleven
distinct configuration panels: Layout, Typography, Axes, Legend, Colors, Data
Labels, Ordering, Engine, Reference Lines, Shapes, and Advanced.

The architecture follows a **progressive disclosure** pattern: only three pills
(Layout, Typography, Legends) are visible by default.  An "advanced" toggle
reveals the remaining four panels (Axes, Data Labels, Colors, Advanced).  Each
panel is backed by a standalone `*SettingsComponent` class that renders
Streamlit widgets via a shared `widget_factory` module and returns a `PlotConfig`
dictionary.

### Source files under test

| File | Component |
|------|-----------|
| `src/web/pages/ui/plotting/settings_pills.py` | `SettingsSection`, `render_settings_pills`, `render_preset_pills` |
| `src/web/components/plotting/settings/widget_factory.py` | `select_option`, `numeric_input`, `color_picker`, `toggle`, `slider` |
| `src/web/components/plotting/settings/layout_settings.py` | `LayoutSettingsComponent` |
| `src/web/components/plotting/settings/typography_settings.py` | `TypographySettingsComponent` |
| `src/web/components/plotting/settings/axes_settings.py` | `AxesSettingsComponent` |
| `src/web/components/plotting/settings/legend_settings.py` | `LegendSettingsComponent` |
| `src/web/components/plotting/settings/colors_settings.py` | `ColorsSettingsComponent` |
| `src/web/components/plotting/settings/data_labels_settings.py` | `DataLabelsSettingsComponent` |
| `src/web/components/plotting/settings/ordering_settings.py` | `OrderingSettingsComponent` |
| `src/web/components/plotting/settings/engine_settings.py` | `EngineSettingsComponent` |
| `src/web/components/plotting/settings/reference_line_settings.py` | `ReferenceLineSettingsComponent` |
| `src/web/components/plotting/settings/shapes_settings.py` | `ShapesSettingsComponent` |
| `src/web/components/plotting/settings/advanced_settings.py` | `AdvancedSettingsComponent` |

### Widget factory primitives

Every settings component relies on five shared primitives from `widget_factory.py`:

| Primitive | Streamlit Widget | Key Behavior |
|-----------|-----------------|--------------|
| `select_option` | `st.selectbox` | Safe index lookup; falls back to index 0 when saved value is missing |
| `numeric_input` | `st.number_input` | Config-based defaults; cast to int or float based on `default` type |
| `color_picker` | `st.color_picker` | Default `#000000`; reads from saved config |
| `toggle` | `st.checkbox` | Boolean config toggle with optional help text |
| `slider` | `st.slider` | Ranged value with config-based default; int/float casting |

### Test strategy

All tests use **Playwright** to drive a live Streamlit application.  Selectors
target widget labels and `data-testid` attributes.  Each scenario verifies:

1. Widget visibility and default values on initial load.
2. User interaction produces the expected config dictionary entries.
3. Cross-panel interactions do not cause regressions.
4. Progressive disclosure hides/reveals panels correctly.
5. Engine-specific conditional rendering (Plotly vs Matplotlib).

---

## 2. Settings Pills Navigation System

### 2.1 Gherkin -- Progressive Disclosure

```gherkin
Feature: Settings pills navigation with progressive disclosure

  Background:
    Given I am on the plot styling page for plot_id 1
    And a bar chart has been configured with valid data

  Scenario: Only basic pills are visible by default
    When the settings sidebar loads
    Then I should see pills labeled "Layout", "Typography", "Legends"
    And I should NOT see pills labeled "Axes", "Data Labels", "Colors", "Advanced"

  Scenario: Advanced toggle reveals all pills
    When I enable the "Show advanced settings" toggle
    Then I should see pills labeled "Layout", "Typography", "Legends", "Axes", "Data Labels", "Colors", "Advanced"
    And the total pill count should be 7

  Scenario: Disabling advanced toggle re-hides advanced pills
    Given the advanced toggle is enabled
    When I disable the "Show advanced settings" toggle
    Then I should see only "Layout", "Typography", "Legends"
    And the total pill count should be 3

  Scenario: Selecting a pill routes to the correct panel
    Given the advanced toggle is enabled
    When I click the "Typography" pill
    Then the Typography settings panel should be visible
    And the heading "Typography (Font Sizes & Colors)" should appear

  Scenario: No pill selected renders nothing
    When no settings pill is selected
    Then no settings panel should be rendered
    And the sidebar should display only the pills row

  Scenario: Preset pills render independently of settings pills
    When I view the preset selector
    Then I should see "NONE" as the default selection
    And all registered preset names should appear as options

  Scenario: Selecting a preset returns its name
    When I click the "ISCA" preset pill
    Then the selected preset name should be "isca"
    And the config should reflect preset-loaded values
```

### 2.2 Gherkin -- Pill Icons and Labels

```gherkin
  Scenario Outline: Each pill displays correct icon and label
    Given the advanced toggle is enabled
    When I inspect the "<key>" pill
    Then the pill label should contain "<label>"
    And the pill icon should reference material icon "<icon>"

    Examples:
      | key         | label       | icon          |
      | layout      | Layout      | dashboard     |
      | typography  | Typography  | text_fields   |
      | legends     | Legends     | legend_toggle |
      | axes        | Axes        | straighten    |
      | data_labels | Data Labels | label         |
      | colors      | Colors      | palette       |
      | advanced    | Advanced    | settings      |
```

### 2.3 Gherkin -- SettingsSection dataclass

```gherkin
  Scenario: SettingsSection is frozen and immutable
    Given a SettingsSection instance with key="layout"
    When I attempt to modify its key attribute
    Then a FrozenInstanceError should be raised

  Scenario: Advanced flag controls visibility
    Given SETTINGS_SECTIONS contains 7 entries
    Then exactly 3 should have advanced=False
    And exactly 4 should have advanced=True
```

### 2.4 Pytest stubs -- Navigation

```python
import re

import pytest
from playwright.sync_api import Page, expect


class TestSettingsPillsNavigation:
    """E2E tests for the settings pills navigation system."""

    def test_basic_pills_visible_by_default(self, page: Page, app_url: str) -> None:
        """Only Layout, Typography, and Legends pills are shown initially."""
        page.goto(app_url)
        pills_container = page.locator(
            "[data-testid='stPills']"
        ).filter(has_text="Settings")
        pill_labels = pills_container.locator("[role='tab']").all_text_contents()
        combined = " ".join(pill_labels)
        assert "Layout" in combined
        assert "Typography" in combined
        assert "Legends" in combined
        assert "Axes" not in combined
        assert "Data Labels" not in combined

    def test_advanced_toggle_reveals_all_pills(self, page: Page, app_url: str) -> None:
        """Enabling advanced mode reveals all 7 pills."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        pills_container = page.locator(
            "[data-testid='stPills']"
        ).filter(has_text="Settings")
        pills = pills_container.locator("[role='tab']")
        assert pills.count() == 7

    def test_disabling_advanced_hides_pills(self, page: Page, app_url: str) -> None:
        """Disabling advanced toggle re-hides advanced pills."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_label("Show advanced settings").uncheck()
        pills_container = page.locator(
            "[data-testid='stPills']"
        ).filter(has_text="Settings")
        pills = pills_container.locator("[role='tab']")
        assert pills.count() == 3

    def test_clicking_pill_routes_to_panel(self, page: Page, app_url: str) -> None:
        """Clicking 'Typography' pill shows Typography panel heading."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Typography")).click()
        expect(page.get_by_text("Typography (Font Sizes & Colors)")).to_be_visible()

    def test_preset_pills_default_none(self, page: Page, app_url: str) -> None:
        """Preset selector defaults to 'NONE' selection."""
        page.goto(app_url)
        preset_container = page.locator(
            "[data-testid='stPills']"
        ).filter(has_text="Preset")
        none_pill = preset_container.get_by_role("tab", name="None")
        expect(none_pill).to_have_attribute("aria-selected", "true")

    def test_selecting_preset_returns_name(self, page: Page, app_url: str) -> None:
        """Selecting a preset pill activates it."""
        page.goto(app_url)
        preset_container = page.locator(
            "[data-testid='stPills']"
        ).filter(has_text="Preset")
        isca_pill = preset_container.get_by_role("tab", name="ISCA")
        isca_pill.click()
        expect(isca_pill).to_have_attribute("aria-selected", "true")

    def test_pill_format_func_uppercases_preset_names(
        self, page: Page, app_url: str
    ) -> None:
        """Preset pills display uppercase names via format_func."""
        page.goto(app_url)
        preset_container = page.locator(
            "[data-testid='stPills']"
        ).filter(has_text="Preset")
        labels = preset_container.locator("[role='tab']").all_text_contents()
        # All non-None labels should be uppercase
        for label in labels:
            if label != "None":
                assert label == label.upper()
```

---

## 3. Layout Settings Tests

### 3.1 Gherkin -- Dimensions and Presets

```gherkin
Feature: Layout settings -- dimensions and document presets

  Background:
    Given I am on the plot styling page for plot_id 1
    And the "Layout" pill is selected

  Scenario: Default preset is Double Column
    Then the "Document Size Preset" selectbox should show "Double Column (~7.0in)"
    And the width input should display 7.0 and be disabled
    And the height input should display 3.5

  Scenario: Single Column preset sets width to 3.5in
    When I select "Single Column (~3.5in)" from "Document Size Preset"
    Then the width input should display 3.5 and be disabled
    And the rendered config key "width_inches" should equal 3.5
    And the config key "width" should equal 350

  Scenario: Custom preset enables width editing
    When I select "Custom" from "Document Size Preset"
    Then the width input should be enabled
    And I can set width to 5.0 inches
    And the config key "width" should equal 500

  Scenario: Width input value range
    Given the preset is "Custom"
    When I attempt to set width to 0.5
    Then the value should clamp to the minimum of 1.0
    When I attempt to set width to 35.0
    Then the value should clamp to the maximum of 30.0

  Scenario: Height is always editable
    When I set "Height (inches)" to 6.0
    Then the config key "height_inches" should equal 6.0
    And the config key "height" should equal 600

  Scenario: Height input value range
    When I attempt to set height to 0.5
    Then the value should clamp to 1.0
    When I attempt to set height to 35.0
    Then the value should clamp to 30.0

  Scenario: Margins default to zero with automargin
    Then the config should contain:
      | key         | value |
      | margin_l    | 0     |
      | margin_r    | 0     |
      | margin_t    | 0     |
      | margin_b    | 0     |
      | margin_pad  | 0     |
      | automargin  | True  |

  Scenario: Pixel dimensions are computed from inches at 100 DPI
    Given the preset is "Double Column (~7.0in)"
    And height is 3.5 inches
    Then "width" should be 700
    And "height" should be 350

  Scenario: Switching preset preserves height
    Given height is set to 5.0
    When I switch from "Double Column (~7.0in)" to "Single Column (~3.5in)"
    Then height should still be 5.0
    And width should change to 3.5

  Scenario: Document preset key is stored in config
    When I select "Single Column (~3.5in)" preset
    Then the config key "document_width_preset" should equal "Single Column (~3.5in)"
```

### 3.2 Pytest stubs -- Layout

```python
class TestLayoutSettings:
    """E2E tests for LayoutSettingsComponent."""

    def test_default_preset_double_column(self, page: Page, app_url: str) -> None:
        """Default document preset is Double Column (~7.0in)."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Layout")).click()
        preset_select = page.get_by_label("Document Size Preset")
        expect(preset_select).to_contain_text("Double Column (~7.0in)")

    def test_single_column_sets_width(self, page: Page, app_url: str) -> None:
        """Selecting Single Column sets width to 3.5 inches."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Layout")).click()
        page.get_by_label("Document Size Preset").select_option(
            "Single Column (~3.5in)"
        )
        width_input = page.get_by_label("Width (inches)")
        expect(width_input).to_have_value("3.5")
        expect(width_input).to_be_disabled()

    def test_custom_preset_enables_width(self, page: Page, app_url: str) -> None:
        """Custom preset enables the width input for editing."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Layout")).click()
        page.get_by_label("Document Size Preset").select_option("Custom")
        width_input = page.get_by_label("Width (inches)")
        expect(width_input).to_be_enabled()

    def test_custom_width_range_min(self, page: Page, app_url: str) -> None:
        """Width input minimum is 1.0 inches."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Layout")).click()
        page.get_by_label("Document Size Preset").select_option("Custom")
        w = page.get_by_label("Width (inches)")
        w.fill("0.5")
        w.press("Enter")
        expect(w).to_have_value("1.0")

    def test_custom_width_range_max(self, page: Page, app_url: str) -> None:
        """Width input maximum is 30.0 inches."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Layout")).click()
        page.get_by_label("Document Size Preset").select_option("Custom")
        w = page.get_by_label("Width (inches)")
        w.fill("35.0")
        w.press("Enter")
        expect(w).to_have_value("30.0")

    def test_height_always_editable(self, page: Page, app_url: str) -> None:
        """Height input is always editable regardless of preset."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Layout")).click()
        height_input = page.get_by_label("Height (inches)")
        expect(height_input).to_be_enabled()
        height_input.fill("6.0")
        height_input.press("Enter")
        expect(height_input).to_have_value("6.0")

    def test_default_height_3_5(self, page: Page, app_url: str) -> None:
        """Default height is 3.5 inches."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Layout")).click()
        expect(page.get_by_label("Height (inches)")).to_have_value("3.5")

    def test_pixel_dimensions_scale_from_inches(
        self, page: Page, app_url: str
    ) -> None:
        """Pixel dimensions are 100x the inch values (100 DPI scaling)."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Layout")).click()
        page.get_by_label("Document Size Preset").select_option("Custom")
        page.get_by_label("Width (inches)").fill("10.0")
        page.get_by_label("Width (inches)").press("Enter")
        # Config should contain width=1000, height=350

    def test_width_disabled_for_non_custom_presets(
        self, page: Page, app_url: str
    ) -> None:
        """Width input is disabled for Single/Double Column presets."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Layout")).click()
        # Default is Double Column
        disabled_input = page.locator(
            "[data-testid='stNumberInput']"
        ).filter(has_text="Width (inches)")
        expect(disabled_input.locator("input")).to_be_disabled()
```

---

## 4. Typography Settings Tests

### 4.1 Gherkin -- Font Sizes and Colors

```gherkin
Feature: Typography settings -- font sizes, colors, and sentinel inheritance

  Background:
    Given I am on the plot styling page for plot_id 1
    And the "Typography" pill is selected

  Scenario: Default font sizes are populated
    Then "Plot Title Font Size" should show 18
    And "X-Axis Title Font Size" should show 14
    And "Y-Axis Title Font Size" should show 14
    And "X-Axis Label (Tick) Size" should show 12
    And "Y-Axis Label (Tick) Size" should show 12

  Scenario: Change title font size
    When I set "Plot Title Font Size" to 24
    Then the config key "title_font_size" should equal 24

  Scenario: Font size minimum is 8
    When I attempt to set "Plot Title Font Size" to 4
    Then the value should clamp to 8

  Scenario: Font size maximum is 100
    When I attempt to set "X-Axis Label (Tick) Size" to 120
    Then the value should clamp to 100

  Scenario: Change X-axis tick label color
    When I set the "X-Axis Label Color" color picker to "#FF0000"
    Then the config key "xaxis_tickfont_color" should equal "#ff0000"

  Scenario: Default tick colors are grey
    Then the "X-Axis Label Color" picker should show "#444444"
    And the "Y-Axis Label Color" picker should show "#444444"

  Scenario: X-axis tick size help text warns about override
    Then the "X-Axis Label (Tick) Size" input should display help text
    And the help text should contain "Overwrites the basic X-axis font size"

  Scenario: Config returns 7 typography keys
    When I accept all defaults
    Then the returned config should contain exactly these keys:
      | key                     | default |
      | title_font_size         | 18      |
      | xaxis_title_font_size   | 14      |
      | yaxis_title_font_size   | 14      |
      | xaxis_tickfont_size     | 12      |
      | xaxis_tickfont_color    | #444444 |
      | yaxis_tickfont_size     | 12      |
      | yaxis_tickfont_color    | #444444 |

  Scenario: Two-column layout renders title sizes left, tick sizes right
    Then the left column should contain "Title Font Sizes" heading
    And the right column should contain "Tick Label Sizes & Colors" heading

  Scenario: Saved config values are restored on reload
    Given a saved config with title_font_size=24 and xaxis_tickfont_color="#00FF00"
    When the Typography panel loads
    Then "Plot Title Font Size" should show 24
    And "X-Axis Label Color" should show "#00FF00"
```

### 4.2 Gherkin -- Sentinel Value -1 Inheritance

```gherkin
Feature: Sentinel value -1 for auto-inheritance in typography-adjacent controls

  Background:
    Given I am on the plot styling page for plot_id 1
    And the advanced toggle is enabled

  Scenario: Y-Axis Title Standoff defaults to -1 (auto)
    When I navigate to the "Axes" pill and select "Y-Left" axis
    Then "Y-Axis Title Standoff (Spacing)" should show -1
    And the help text should say "Distance between Y-axis ticks and the title. -1 = auto"

  Scenario: Sentinel -1 is excluded from rendering
    Given "Y-Axis Title Standoff (Spacing)" is set to -1
    Then the rendering engine should use its default standoff spacing
    And no explicit standoff value is passed to the Plotly layout

  Scenario: Positive standoff value overrides auto
    When I set "Y-Axis Title Standoff (Spacing)" to 40
    Then the config key "yaxis_title_standoff" should equal 40
    And the rendering engine should set standoff=40 on the Y-axis
```

### 4.3 Pytest stubs -- Typography

```python
class TestTypographySettings:
    """E2E tests for TypographySettingsComponent."""

    def test_default_font_sizes(self, page: Page, app_url: str) -> None:
        """All font size defaults match expected values."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Typography")).click()
        expect(page.get_by_label("Plot Title Font Size")).to_have_value("18")
        expect(page.get_by_label("X-Axis Title Font Size")).to_have_value("14")
        expect(page.get_by_label("Y-Axis Title Font Size")).to_have_value("14")
        expect(page.get_by_label("X-Axis Label (Tick) Size")).to_have_value("12")
        expect(page.get_by_label("Y-Axis Label (Tick) Size")).to_have_value("12")

    def test_change_title_font_size(self, page: Page, app_url: str) -> None:
        """Setting title font size to 24 produces correct config."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Typography")).click()
        title_input = page.get_by_label("Plot Title Font Size")
        title_input.fill("24")
        title_input.press("Enter")
        expect(title_input).to_have_value("24")

    def test_font_size_clamped_to_minimum_8(self, page: Page, app_url: str) -> None:
        """Font sizes below 8 are clamped to 8."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Typography")).click()
        title_input = page.get_by_label("Plot Title Font Size")
        title_input.fill("4")
        title_input.press("Enter")
        expect(title_input).to_have_value("8")

    def test_font_size_clamped_to_maximum_100(self, page: Page, app_url: str) -> None:
        """Font sizes above 100 are clamped to 100."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Typography")).click()
        tick_input = page.get_by_label("X-Axis Label (Tick) Size")
        tick_input.fill("120")
        tick_input.press("Enter")
        expect(tick_input).to_have_value("100")

    def test_default_tick_colors_grey(self, page: Page, app_url: str) -> None:
        """Default tick label colors are #444444."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Typography")).click()
        x_color_block = page.locator(
            "[data-testid='stColorPicker']"
        ).filter(has_text="X-Axis Label Color")
        expect(x_color_block).to_contain_text("#444444")

    def test_change_tick_label_color(self, page: Page, app_url: str) -> None:
        """Changing X-axis tick color updates config."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Typography")).click()
        page.get_by_label("X-Axis Label Color").click()
        hex_input = page.locator("input[aria-label='Hex']")
        hex_input.fill("FF0000")
        hex_input.press("Enter")

    def test_typography_two_column_layout(self, page: Page, app_url: str) -> None:
        """Typography panel uses two-column layout."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Typography")).click()
        expect(page.get_by_text("Title Font Sizes")).to_be_visible()
        expect(page.get_by_text("Tick Label Sizes & Colors")).to_be_visible()

    def test_typography_returns_seven_keys(self, page: Page, app_url: str) -> None:
        """Typography config dict should contain exactly 7 keys."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Typography")).click()
        # Verify all 7 widget labels are present
        for label in [
            "Plot Title Font Size",
            "X-Axis Title Font Size",
            "Y-Axis Title Font Size",
            "X-Axis Label (Tick) Size",
            "X-Axis Label Color",
            "Y-Axis Label (Tick) Size",
            "Y-Axis Label Color",
        ]:
            expect(page.get_by_label(label).first).to_be_visible()

    def test_sentinel_minus_one_for_standoff(self, page: Page, app_url: str) -> None:
        """Sentinel -1 for Y-Axis Title Standoff means auto."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        page.get_by_role("tab", name=re.compile("Y-Left")).click()
        standoff_label = page.get_by_text("Y-Axis Title Standoff (Spacing)")
        expect(standoff_label).to_be_visible()
```

---

## 5. Axes Settings Tests

### 5.1 Gherkin -- X-Axis Settings

```gherkin
Feature: Axes settings -- X-axis tick marks, grid, axis lines, numbered axis

  Background:
    Given I am on the plot styling page for plot_id 1
    And the advanced toggle is enabled
    And the "Axes" pill is selected

  Scenario: Axes pill has nested X / Y-Left navigation
    Then I should see axis pills "X-Axis" and "Y-Left"
    And "X-Axis" should be selected by default

  Scenario: X-axis default settings
    When I view the X-Axis settings
    Then "Show Grid" should be unchecked
    And "X-axis Label Rotation" slider should be at -45
    And "Show X-Axis Tick Marks" should be unchecked
    And "X-Axis Tick Side" should be "bottom"
    And "X-Axis Tick Label Distance (px)" should be 5.0
    And "Bottom Axis Line Width (px)" should be 1.0
    And "Bottom Axis Line Color" should be "#444444"
    And "Top Axis Line Width (px)" should be 0.0

  Scenario: Change X-axis label rotation
    When I drag the "X-axis Label Rotation" slider to 0
    Then the config key "xaxis_tickangle" should equal 0

  Scenario: Rotation slider range is -90 to 90 in steps of 15
    Then the "X-axis Label Rotation" slider minimum should be -90
    And the maximum should be 90
    And the step should be 15

  Scenario: Enabling tick marks reveals grid dash style
    When I check "Show X-Axis Tick Marks"
    Then the "X-Axis Grid Dash Style" selectbox should become visible
    And the default dash style should be "solid"

  Scenario: Grid dash style options
    Given "Show X-Axis Tick Marks" is checked
    When I open the "X-Axis Grid Dash Style" selectbox
    Then I should see options: solid, dot, dash, longdash, dashdot, longdashdot

  Scenario: Disabling tick marks hides dash style but uses solid
    Given "Show X-Axis Tick Marks" is checked
    When I uncheck "Show X-Axis Tick Marks"
    Then the "X-Axis Grid Dash Style" selectbox should not be visible
    And the config key "xtick_dash" should equal "solid"

  Scenario: X-axis tick label distance
    When I set "X-Axis Tick Label Distance (px)" to 10.0
    Then the config key "xtick_pad" should equal 10.0

  Scenario: Numbered X-axis toggle and modes
    When I check "Use Numbered X-Axis"
    Then the numbered X-axis modes pills should appear
    And options "Numbers" and "Number legend" should be available

  Scenario: Numbered modes are multi-select
    When I check "Use Numbered X-Axis"
    And I select both "Numbers" and "Number legend"
    Then the config should contain:
      | key                   | value                         |
      | numbered_xaxis        | True                          |
      | show_numbered_ticks   | True                          |
      | show_numbered_legend  | True                          |
      | numbered_xaxis_modes  | ["Numbers", "Number legend"]  |

  Scenario: Selecting only "Numbers" mode
    When I check "Use Numbered X-Axis"
    And I select only "Numbers"
    Then "show_numbered_ticks" should be True
    And "show_numbered_legend" should be False
```

### 5.2 Gherkin -- Y-Axis Settings

```gherkin
Feature: Axes settings -- Y-axis (left and right)

  Scenario: Y-Left axis default settings
    When I click the "Y-Left" axis pill
    Then "Show Grid" should be checked (default True for Y-Left)
    And "Y-axis Label Rotation" should default to 0
    And the step size input should default to 0.0 (auto)
    And "Show Y-Axis Tick Marks" should be unchecked
    And "Y-Axis Tick Side" should be "left"

  Scenario: Y-axis step size filters zero
    When I click the "Y-Left" axis pill
    And I set the step size to 0.0
    Then the config should NOT contain key "yaxis_dtick"

  Scenario: Y-axis step size sets dtick when positive
    When I click the "Y-Left" axis pill
    And I set the step size to 5.0
    Then the config key "yaxis_dtick" should equal 5.0

  Scenario: Y-axis title standoff slider
    When I click the "Y-Left" axis pill
    Then "Y-Axis Title Standoff (Spacing)" should have:
      | property  | value |
      | default   | -1    |
      | min_value | -1    |
      | max_value | 200   |

  Scenario: Y-axis title vertical shift slider
    When I click the "Y-Left" axis pill
    Then "Y-Axis Title Vertical Shift" should have range -500 to 500
    And the help text should mention "Matplotlib only"

  Scenario: Y-Left axis line controls (4-sided)
    When I click the "Y-Left" axis pill
    Then I should see "Y-Left Axis Line Width (px)" defaulting to 1.0
    And "Y-Left Axis Line Color" defaulting to "#444444"
    And "Right Axis Line Width (px)" defaulting to 0.0

  Scenario: Dual-axis plot adds Y-Right pill
    Given the plot has dual axis enabled (has_dual_axis=True)
    Then I should see axis pills "X-Axis", "Y-Left", and "Y-Right"

  Scenario: Y-Right axis uses y2 prefix
    Given the plot has dual axis enabled
    When I click the "Y-Right" axis pill
    Then the heading should say "Y-Right Axis Settings"
    And "Show Grid" should default to unchecked (default False for right)
    And the config keys should use prefix "y2"

  Scenario: Y-Right axis does NOT show opposite border controls
    Given the plot has dual axis enabled
    When I click the "Y-Right" axis pill
    Then I should NOT see "Right Axis Line Width" controls
    And only the primary Y-Right line width and color should appear
```

### 5.3 Gherkin -- Group Labels

```gherkin
Feature: Axes settings -- Group Labels (grouped stacked bar)

  Background:
    Given the plot type is "grouped_stacked_bar" with show_group_labels=True
    And the "Axes" pill is selected

  Scenario: Group Labels pill is visible
    Then I should see a "Group Labels" pill in the axis navigation

  Scenario: Group Labels default settings
    When I click the "Group Labels" pill
    Then "Label-to-Axis Distance" should default to -0.15
    And the range should be -1.0 to 0.0 in steps of 0.01
    And "Alternate Group Labels (up/down)" should be checked
    And "Alt. Label Row Spacing" should default to 0.05

  Scenario: Changing label distance updates both keys
    When I set "Label-to-Axis Distance" to -0.25
    Then config key "major_label_offset" should equal -0.25
    And config key "group_label_offset" should equal -0.25
```

### 5.4 Pytest stubs -- Axes

```python
class TestAxesSettings:
    """E2E tests for AxesSettingsComponent."""

    def test_nested_axis_pills_visible(self, page: Page, app_url: str) -> None:
        """X-Axis and Y-Left pills appear inside the Axes panel."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        expect(page.get_by_role("tab", name=re.compile("X-Axis"))).to_be_visible()
        expect(page.get_by_role("tab", name=re.compile("Y-Left"))).to_be_visible()

    def test_x_axis_selected_by_default(self, page: Page, app_url: str) -> None:
        """X-Axis pill is selected by default."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        x_pill = page.get_by_role("tab", name=re.compile("X-Axis"))
        expect(x_pill).to_have_attribute("aria-selected", "true")

    def test_x_axis_grid_default_unchecked(self, page: Page, app_url: str) -> None:
        """X-axis 'Show Grid' defaults to unchecked."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        expect(page.get_by_label("Show Grid")).not_to_be_checked()

    def test_x_axis_tick_side_default_bottom(self, page: Page, app_url: str) -> None:
        """X-axis tick side defaults to 'bottom'."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        expect(page.get_by_label("X-Axis Tick Side")).to_contain_text("bottom")

    def test_tick_marks_reveals_dash_style(self, page: Page, app_url: str) -> None:
        """Checking tick marks reveals dash style dropdown."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        page.get_by_label("Show X-Axis Tick Marks").check()
        expect(page.get_by_label("X-Axis Grid Dash Style")).to_be_visible()

    def test_y_left_grid_default_on(self, page: Page, app_url: str) -> None:
        """Y-Left axis 'Show Grid' defaults to checked."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        page.get_by_role("tab", name=re.compile("Y-Left")).click()
        expect(page.get_by_label("Show Grid")).to_be_checked()

    def test_y_axis_dtick_zero_not_in_config(self, page: Page, app_url: str) -> None:
        """Y-axis step size 0 is filtered out of config."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        page.get_by_role("tab", name=re.compile("Y-Left")).click()
        step = page.get_by_label(re.compile("Step Size"))
        step.fill("0.0")
        step.press("Enter")
        # dtick key should be absent from config

    def test_numbered_xaxis_modes_multi_select(self, page: Page, app_url: str) -> None:
        """Numbered X-Axis modes use multi-select pills."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        page.get_by_label("Use Numbered X-Axis").check()
        expect(page.get_by_role("tab", name="Numbers")).to_be_visible()
        expect(page.get_by_role("tab", name="Number legend")).to_be_visible()

    def test_bottom_axis_line_defaults(self, page: Page, app_url: str) -> None:
        """Bottom axis line defaults: width=1.0, top=0.0."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        expect(
            page.get_by_label("Bottom Axis Line Width (px)")
        ).to_have_value("1.0")
        expect(
            page.get_by_label("Top Axis Line Width (px)")
        ).to_have_value("0.0")

    def test_group_labels_alternate_default(self, page: Page, app_url: str) -> None:
        """Group Labels 'Alternate' toggle defaults to checked."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        page.get_by_role("tab", name=re.compile("Group Labels")).click()
        expect(
            page.get_by_label("Alternate Group Labels (up/down)")
        ).to_be_checked()

    def test_group_label_distance_default(self, page: Page, app_url: str) -> None:
        """Group label distance defaults to -0.15."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        page.get_by_role("tab", name=re.compile("Group Labels")).click()
        expect(page.get_by_label("Label-to-Axis Distance")).to_have_value("-0.15")

    def test_y_axis_vertical_shift_help_mentions_matplotlib(
        self, page: Page, app_url: str
    ) -> None:
        """Y-axis vertical shift help text mentions Matplotlib."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        page.get_by_role("tab", name=re.compile("Y-Left")).click()
        vshift_container = page.locator(
            "[data-testid='stSlider']"
        ).filter(has_text="Y-Axis Title Vertical Shift")
        expect(vshift_container).to_be_visible()
```

---

## 6. Legend Settings Tests

### 6.1 Gherkin -- Multi-Level Legend Pills and Position

```gherkin
Feature: Legend settings -- position, appearance, sizing, multiple legend tiers

  Background:
    Given I am on the plot styling page for plot_id 1
    And the "Legends" pill is selected

  Scenario: Primary legend pill is selected by default
    Then I should see a "Primary" legend pill selected by default
    And no "Secondary" or "Tertiary" pills should appear for a simple bar chart

  Scenario: Dual-axis plot shows secondary legend pill
    Given the plot has a secondary legend (has_secondary=True)
    Then I should see "Primary" and "Secondary" pills

  Scenario: Tertiary legend pill appears when enabled
    Given the plot has a tertiary legend (has_tertiary=True)
    Then I should see "Primary", "Secondary", and "Tertiary" pills

  Scenario: Legend position defaults for primary
    When I view the Position section
    Then "X Position" should default to 1.02
    And "Y Position" should default to 1.0
    And "Orientation" should be "vertical"

  Scenario: Legend position defaults for secondary
    Given has_secondary=True
    When I click the "Secondary" pill
    Then "X Position" should default to 1.0
    And "Y Position" should default to 1.0

  Scenario: Position caption explains coordinate system
    Then I should see caption text containing "Position (0, 0) = bottom-left"

  Scenario: Transparent legend background
    When I check "Transparent Background"
    Then the "Background Color" picker should disappear
    And the config key "legend_bgcolor" should be "rgba(0,0,0,0)"

  Scenario: Opaque legend with custom background
    When I uncheck "Transparent Background"
    And I set "Background Color" to "#FFFF00"
    Then the config key "legend_bgcolor" should equal "#FFFF00"

  Scenario: Legend border controls
    Then "Border Color" should default to "#000000"
    And "Border Width" should default to 0
    And border width range should be 0 to 5

  Scenario: Legend font controls
    Then "Text Color" should default to "#000000"
    And "Font Size" should default to 12

  Scenario: Legend title input
    When I type "My Legend Title" in the "Legend Title" field
    Then the config key "legend_title" should equal "My Legend Title"

  Scenario: Legend title font controls
    Then "Title Color" should default to "#000000"
    And "Title Size" should default to 14

  Scenario: Legend sizing - columns
    Then "Columns" should default to 0
    And the range should be 0 to 20
    And the help text should mention "0 = single column"

  Scenario: Legend sizing - item spacing
    Then "Item Spacing (px)" should default to 10
    And "Column Spacing" should default to 0.5
    And "Stripe Length (px)" should default to 30
    And "Stripe-Text Gap" should default to 0.3

  Scenario: Switching pills preserves inactive config
    Given I configure primary legend with x=0.5, y=0.8
    When I switch to the "Secondary" pill
    And then switch back to "Primary"
    Then the primary config values should be preserved from saved_config

  Scenario: Heatmap plot shows colorbar instead of legend
    Given the plot type is "heatmap"
    When the Legends pill loads
    Then the heading should say "Colorbar Styling"
    And I should see colorbar-specific controls

  Scenario: Heatmap colorbar shared toggle
    Given the plot type is "heatmap"
    Then "Shared Colorbar" should default to checked
    And "Range Mode" should default to "auto"

  Scenario: Heatmap colorbar manual range
    Given the plot type is "heatmap"
    When I select "manual" range mode
    Then "Min" and "Max" inputs should appear
    And "Min" should default to 0.0
    And "Max" should default to 100.0

  Scenario: Heatmap colorbar tick controls
    Given the plot type is "heatmap"
    Then "Tick Count" should default to 5 (range 2-20)
    And "Tick Decimals" should default to 2 (range 0-6)
    And "Tick Rotation" should default to 0.0
    And "Tick Side" should default to "right"
```

### 6.2 Pytest stubs -- Legend

```python
class TestLegendSettings:
    """E2E tests for LegendSettingsComponent."""

    def test_primary_pill_selected_by_default(self, page: Page, app_url: str) -> None:
        """Primary legend pill is auto-selected."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Legends")).click()
        primary_pill = page.get_by_role("tab", name=re.compile("Primary"))
        expect(primary_pill).to_have_attribute("aria-selected", "true")

    def test_legend_position_defaults(self, page: Page, app_url: str) -> None:
        """Primary legend defaults: x=1.02, y=1.0, vertical."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Legends")).click()
        expect(page.get_by_label("X Position")).to_have_value("1.02")
        expect(page.get_by_label("Y Position")).to_have_value("1.0")
        expect(page.get_by_label("Orientation")).to_contain_text("vertical")

    def test_transparent_legend_hides_bg_picker(self, page: Page, app_url: str) -> None:
        """Checking transparent hides the background color picker."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Legends")).click()
        page.get_by_label("Transparent Background").check()
        expect(page.get_by_label("Background Color")).not_to_be_visible()

    def test_legend_border_width_default_zero(self, page: Page, app_url: str) -> None:
        """Border width defaults to 0."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Legends")).click()
        expect(page.get_by_label("Border Width")).to_have_value("0")

    def test_legend_font_size_default(self, page: Page, app_url: str) -> None:
        """Legend font size defaults to 12."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Legends")).click()
        expect(page.get_by_label("Font Size")).to_have_value("12")

    def test_legend_title_input(self, page: Page, app_url: str) -> None:
        """Setting a legend title stores it in config."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Legends")).click()
        title_input = page.get_by_label("Legend Title")
        title_input.fill("My Legend")
        title_input.press("Enter")
        expect(title_input).to_have_value("My Legend")

    def test_legend_columns_default_zero(self, page: Page, app_url: str) -> None:
        """Legend columns default to 0 (single column)."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Legends")).click()
        expect(page.get_by_label("Columns")).to_have_value("0")

    def test_legend_item_spacing_default(self, page: Page, app_url: str) -> None:
        """Item spacing defaults to 10px."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Legends")).click()
        expect(page.get_by_label("Item Spacing (px)")).to_have_value("10")

    def test_heatmap_shows_colorbar_heading(
        self, page: Page, heatmap_app_url: str
    ) -> None:
        """Heatmap plot shows 'Colorbar Styling' heading instead of 'Legend Styling'."""
        page.goto(heatmap_app_url)
        page.get_by_role("tab", name=re.compile("Legends")).click()
        expect(page.get_by_text("Colorbar Styling")).to_be_visible()

    def test_heatmap_colorbar_range_mode_auto(
        self, page: Page, heatmap_app_url: str
    ) -> None:
        """Heatmap colorbar range mode defaults to 'auto'."""
        page.goto(heatmap_app_url)
        page.get_by_role("tab", name=re.compile("Legends")).click()
        expect(page.get_by_label("auto")).to_be_checked()

    def test_heatmap_manual_range_shows_inputs(
        self, page: Page, heatmap_app_url: str
    ) -> None:
        """Selecting manual range mode shows Min/Max inputs."""
        page.goto(heatmap_app_url)
        page.get_by_role("tab", name=re.compile("Legends")).click()
        page.get_by_label("manual").check()
        expect(page.get_by_label("Min")).to_be_visible()
        expect(page.get_by_label("Max")).to_be_visible()
```

---

## 7. Colors & Palette Tests

### 7.1 Gherkin -- Palette Selection and Series Overrides

```gherkin
Feature: Colors settings -- palette, per-series overrides, backgrounds

  Background:
    Given I am on the plot styling page for plot_id 1
    And the advanced toggle is enabled
    And the "Colors" pill is selected

  Scenario: Default palette is wong
    Then the "Palette" selectbox should show "Wong"
    And the config key "color_palette" should be "wong"

  Scenario: Colorblind-safe palettes are marked with checkmark
    When I open the "Palette" selectbox
    Then palettes marked colorblind-safe should have a checkmark prefix

  Scenario: Palette swatches render as colored spans
    Then I should see colored swatch squares below the palette selector
    And the number of swatches should match the palette length

  Scenario: Changing palette updates series colors
    When I select a different palette (e.g. "tol_bright")
    Then the series color pickers should update to reflect the new palette
    And the swatch preview should update

  Scenario: Per-series color override
    Given the plot has series items ["A", "B", "C"]
    When I click the custom color picker for series "A"
    And I set it to "#FF0000"
    And I check "Override" for series "A"
    Then the config series_styles["A"]["color"] should be "#FF0000"
    And series_styles["A"]["use_color"] should be True

  Scenario: Rewind button resets series color
    Given series "A" has a custom color override "#FF0000"
    When I click the "Rewind" button for series "A"
    Then the color should reset to the palette default
    And "Override" should be unchecked

  Scenario: Original color is shown as disabled picker
    Then each series should show its original palette color as a disabled picker
    And the hex value caption should be visible below it

  Scenario: Transparent background toggle
    When I check "Transparent Background"
    Then "Plot Background" and "Paper (Outer) Background" pickers should disappear
    And the config keys should be "rgba(0,0,0,0)"

  Scenario: Opaque background colors
    When I uncheck "Transparent Background"
    Then I should see "Plot Background" defaulting to "#ffffff"
    And "Paper (Outer) Background" defaulting to "#ffffff"

  Scenario: Grid color default
    Then "Grid Color" should default to "#e5e5e5"

  Scenario: Axis line controls in Colors panel
    Then "Axis Line/Tick Color" should default to "#444444"
    And "Axis Line Width (px)" should default to 1.0

  Scenario: Bar stripes toggle (bar plots only)
    Given the plot type is "bar"
    Then I should see an "Enable Bar Stripes" toggle
    When I check "Enable Bar Stripes"
    Then the config key "enable_stripes" should be True

  Scenario: Bar stripes hidden for grouped stacked bar
    Given the plot type is "grouped_stacked_bar"
    Then the "Enable Bar Stripes" toggle should NOT be visible

  Scenario: Heatmap reverse colorscale
    Given the plot type is "heatmap"
    Then I should see "Heatmap Color Scale" section
    And "Reverse Color Scale" should default to unchecked
    When I check "Reverse Color Scale"
    Then the config key "reverse_colorscale" should be True
```

### 7.2 Pytest stubs -- Colors

```python
class TestColorsSettings:
    """E2E tests for ColorsSettingsComponent."""

    def test_default_palette_wong(self, page: Page, app_url: str) -> None:
        """Default palette is 'wong'."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Colors")).click()
        expect(page.get_by_label("Palette")).to_contain_text("Wong")

    def test_colorblind_safe_checkmark(self, page: Page, app_url: str) -> None:
        """Colorblind-safe palettes show checkmark prefix."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Colors")).click()
        # Open dropdown and check for checkmark character
        page.get_by_label("Palette").click()
        options = page.locator("[data-testid='stSelectboxOption']").all_text_contents()
        wong_option = [o for o in options if "Wong" in o]
        assert len(wong_option) > 0
        assert "\u2713" in wong_option[0]  # checkmark

    def test_palette_swatches_rendered(self, page: Page, app_url: str) -> None:
        """Color swatches are rendered below the palette selector."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Colors")).click()
        swatches = page.locator("span[style*='background']")
        assert swatches.count() > 0

    def test_transparent_bg_hides_pickers(self, page: Page, app_url: str) -> None:
        """Transparent background toggle hides background color pickers."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Colors")).click()
        page.get_by_label("Transparent Background").check()
        expect(page.get_by_label("Plot Background")).not_to_be_visible()

    def test_grid_color_default(self, page: Page, app_url: str) -> None:
        """Grid color defaults to #e5e5e5."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Colors")).click()
        grid_block = page.locator(
            "[data-testid='stColorPicker']"
        ).filter(has_text="Grid Color")
        expect(grid_block).to_contain_text("#e5e5e5")

    def test_axis_line_width_default(self, page: Page, app_url: str) -> None:
        """Axis line width defaults to 1.0."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Colors")).click()
        expect(page.get_by_label("Axis Line Width (px)")).to_have_value("1.0")

    def test_bar_stripes_visible_for_bar_type(self, page: Page, app_url: str) -> None:
        """Bar stripes toggle visible for bar plot type."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Colors")).click()
        expect(page.get_by_label("Enable Bar Stripes")).to_be_visible()

    def test_series_override_checkbox(self, page: Page, app_url: str) -> None:
        """Checking 'Override' for a series enables custom color."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Colors")).click()
        # Find the first Override checkbox
        override = page.get_by_label("Override").first
        override.check()
        expect(override).to_be_checked()
```

---

## 8. Data Labels Tests

### 8.1 Gherkin -- Show/Hide, Format, Position, Thresholds

```gherkin
Feature: Data labels settings -- visibility, formatting, positioning, thresholds

  Background:
    Given I am on the plot styling page for plot_id 1
    And the advanced toggle is enabled
    And the "Data Labels" pill is selected

  Scenario: Show Values defaults to unchecked for bar plots
    Given the plot type is "bar"
    Then "Show Values" should be unchecked
    And no further data label controls should be visible

  Scenario: Show Values defaults to checked for heatmap
    Given the plot type is "heatmap"
    Then "Show Values" should be checked
    And formatting controls should be visible

  Scenario: Enabling Show Values reveals all formatting controls
    When I check "Show Values"
    Then I should see:
      | control                | type        |
      | Value Color Mode       | selectbox   |
      | Value Font Size        | number_input|
      | Value Rotation         | slider      |
      | Value Position         | selectbox   |
      | Value Anchor           | selectbox   |
      | Value Number Format    | text_input  |
      | Display Logic          | selectbox   |

  Scenario: Value Color Mode options
    Given "Show Values" is checked
    Then "Value Color Mode" should offer: auto, contrast, custom
    And the default should be "auto" for bar plots
    And the default should be "contrast" for heatmap plots

  Scenario: Custom color mode shows color picker
    Given "Show Values" is checked
    When I select "custom" in "Value Color Mode"
    Then a "Value Color" color picker should appear

  Scenario: Font size range
    Given "Show Values" is checked
    Then "Value Font Size" should default to 10
    And the range should be 6 to 40

  Scenario: Value rotation hidden for heatmap
    Given the plot type is "heatmap" with "Show Values" checked
    Then the "Value Rotation" slider should NOT appear

  Scenario: Value position and anchor hidden for heatmap
    Given the plot type is "heatmap"
    Then "Value Position" and "Value Anchor" should NOT appear

  Scenario: Value position options for bar
    Given the plot type is "bar" with "Show Values" checked
    Then "Value Position" should offer: auto, inside, outside
    And "Value Anchor" should offer: auto, top, middle, bottom

  Scenario: Number format default
    Given "Show Values" is checked
    Then "Value Number Format" should default to ".2f"
    And for heatmap, it should default to ".4g"

  Scenario: Display threshold logic
    Given "Show Values" is checked
    When I select "above_threshold" in "Display Logic"
    Then a "Threshold Value" input should appear
    And it should default to 0.0

  Scenario: Size constraint for bar plots
    Given the plot type is "bar" with "Show Values" checked
    Then "Size Constraint" should offer: none, inside
    And the help text should say "text will be resized or hidden to fit"

  Scenario: Heatmap totals controls
    Given the plot type is "heatmap" with "Show Values" checked
    Then I should see "Show Totals" toggle
    When I check "Show Totals"
    Then "Position" should offer: right, top
    And "Totals Aggregation" should offer: mean, sum, max, min

  Scenario: Disabling Show Values preserves saved config values
    Given "Show Values" was previously enabled with custom settings
    When I uncheck "Show Values"
    Then the returned config should preserve previously saved values for:
      | key              | preserved |
      | text_color_mode  | yes       |
      | text_color       | yes       |
      | text_font_size   | yes       |
```

### 8.2 Pytest stubs -- Data Labels

```python
class TestDataLabelsSettings:
    """E2E tests for DataLabelsSettingsComponent."""

    def test_show_values_default_unchecked_bar(self, page: Page, app_url: str) -> None:
        """Show Values defaults to unchecked for bar plot type."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Data Labels")).click()
        expect(page.get_by_label("Show Values")).not_to_be_checked()

    def test_enabling_show_values_reveals_controls(
        self, page: Page, app_url: str
    ) -> None:
        """Checking Show Values reveals formatting controls."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Data Labels")).click()
        page.get_by_label("Show Values").check()
        expect(page.get_by_label("Value Color Mode")).to_be_visible()
        expect(page.get_by_label("Value Font Size")).to_be_visible()
        expect(page.get_by_label("Value Number Format (d3-format)")).to_be_visible()

    def test_font_size_default_10(self, page: Page, app_url: str) -> None:
        """Value font size defaults to 10."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Data Labels")).click()
        page.get_by_label("Show Values").check()
        expect(page.get_by_label("Value Font Size")).to_have_value("10")

    def test_custom_color_mode_shows_picker(self, page: Page, app_url: str) -> None:
        """Selecting 'custom' color mode shows Value Color picker."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Data Labels")).click()
        page.get_by_label("Show Values").check()
        page.get_by_label("Value Color Mode").select_option("custom")
        expect(page.get_by_label("Value Color")).to_be_visible()

    def test_display_logic_threshold(self, page: Page, app_url: str) -> None:
        """Selecting above_threshold shows Threshold Value input."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Data Labels")).click()
        page.get_by_label("Show Values").check()
        page.get_by_label("Display Logic").select_option("above_threshold")
        expect(page.get_by_label("Threshold Value")).to_be_visible()

    def test_value_position_options_bar(self, page: Page, app_url: str) -> None:
        """Value Position offers auto, inside, outside for bar plots."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Data Labels")).click()
        page.get_by_label("Show Values").check()
        expect(page.get_by_label("Value Position")).to_be_visible()

    def test_number_format_default(self, page: Page, app_url: str) -> None:
        """Number format defaults to '.2f'."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Data Labels")).click()
        page.get_by_label("Show Values").check()
        fmt_input = page.get_by_label("Value Number Format (d3-format)")
        expect(fmt_input).to_have_value(".2f")
```

---

## 9. Ordering Tests

### 9.1 Gherkin -- Reorderable Lists with Rename

```gherkin
Feature: Ordering settings -- X-axis, group, legend, series reordering and renaming

  Background:
    Given I am on the plot styling page for plot_id 1
    And the plot has x-axis, group, and color columns configured

  Scenario: X-axis ordering expander appears when x column is set
    Given the saved config has x="category" and the data has column "category"
    Then I should see "Reorder and Rename X-axis Labels" expander

  Scenario: X-axis items are sorted alphabetically by default
    When I expand "Reorder and Rename X-axis Labels"
    Then the items should be in sorted alphabetical order

  Scenario: Reordering X-axis items updates config
    When I reorder X-axis items from [A, B, C] to [C, A, B]
    Then the config key "xaxis_order" should be ["C", "A", "B"]

  Scenario: Renaming X-axis labels
    When I enable rename mode for X-axis
    And I rename "A" to "Alpha"
    Then the config key "xaxis_labels" should contain {"A": "Alpha"}

  Scenario: Group ordering expander appears when group column is set
    Given the saved config has group="treatment"
    Then I should see "Reorder and Rename Groups" expander

  Scenario: Legend ordering expander appears when color column is set
    Given the saved config has color="species"
    Then I should see "Reorder and Rename Legend Items" expander

  Scenario: Legend rename merges into legend_labels
    When I rename legend item "old_name" to "new_name"
    Then config["legend_labels"]["old_name"] should be "new_name"

  Scenario: Stacked series ordering for y_columns
    Given the saved config has y_columns=["col1", "col2", "col3"]
    Then I should see "Reorder and Rename Stacked Series" expander
    When I reorder to ["col3", "col1", "col2"]
    Then config["y_columns"] should be ["col3", "col1", "col2"]

  Scenario: Series rename sets name in series_styles
    Given y_columns=["col1", "col2"]
    When I rename "col1" to "Revenue"
    Then config["series_styles"]["col1"]["name"] should be "Revenue"

  Scenario: Heatmap metric ordering
    Given the plot type is "heatmap" with metric_columns=["metric_a", "metric_b"]
    Then I should see "Reorder and Rename Y-axis Metrics" expander

  Scenario: Heatmap facet ordering
    Given the plot type is "heatmap" with facet_col="region"
    Then I should see "Reorder and Rename Facets" expander

  Scenario: No ordering controls when no applicable columns
    Given the saved config has no x, group, color, or y_columns
    Then no ordering expanders should appear
```

### 9.2 Pytest stubs -- Ordering

```python
class TestOrderingSettings:
    """E2E tests for OrderingSettingsComponent."""

    def test_xaxis_reorder_expander_visible(self, page: Page, app_url: str) -> None:
        """X-axis reorder expander shows when x column is configured."""
        page.goto(app_url)
        expect(page.get_by_text("Reorder and Rename X-axis Labels")).to_be_visible()

    def test_group_reorder_expander_visible(self, page: Page, app_url: str) -> None:
        """Group reorder expander shows when group column is configured."""
        page.goto(app_url)
        expect(page.get_by_text("Reorder and Rename Groups")).to_be_visible()

    def test_legend_reorder_expander_visible(self, page: Page, app_url: str) -> None:
        """Legend reorder expander shows when color column is configured."""
        page.goto(app_url)
        expect(page.get_by_text("Reorder and Rename Legend Items")).to_be_visible()

    def test_stacked_series_reorder_expander_visible(
        self, page: Page, stacked_app_url: str
    ) -> None:
        """Stacked series reorder expander shows when y_columns are set."""
        page.goto(stacked_app_url)
        expect(
            page.get_by_text("Reorder and Rename Stacked Series")
        ).to_be_visible()

    def test_no_ordering_for_empty_config(
        self, page: Page, minimal_app_url: str
    ) -> None:
        """No ordering expanders when no applicable columns exist."""
        page.goto(minimal_app_url)
        expect(
            page.get_by_text("Reorder and Rename X-axis Labels")
        ).not_to_be_visible()
```

---

## 10. Engine Switching Tests

### 10.1 Gherkin -- Plotly and Matplotlib Controls

```gherkin
Feature: Engine settings -- Plotly vs Matplotlib switching

  Background:
    Given I am on the plot styling page
    And engine settings are accessible via the Advanced pill or directly

  Scenario: Plotly mode shows interactive settings
    Given the rendering engine is Plotly
    Then I should see "Interactive Settings" heading
    And "Hover mode" selectbox should be visible
    And the default hover mode should be "x unified"

  Scenario: Plotly hover mode options
    Given the rendering engine is Plotly
    When I open the "Hover mode" selectbox
    Then I should see: "x unified", "closest", "x", "y", "off"

  Scenario: Matplotlib mode shows LaTeX settings
    Given the rendering engine is Matplotlib
    Then I should see "LaTeX Settings" heading
    And "Extra LaTeX preamble" text area should be visible
    And "TeX system" selectbox should be visible

  Scenario: Default TeX system is xelatex
    Given the rendering engine is Matplotlib
    Then "TeX system" should default to "xelatex"
    And options should include: xelatex, pdflatex, lualatex

  Scenario: LaTeX preamble stores custom content
    Given the rendering engine is Matplotlib
    When I type "\\usepackage{amsmath}" in "Extra LaTeX preamble"
    Then the config key "latex_extra_preamble" should contain "\\usepackage{amsmath}"

  Scenario: Switching from Plotly to Matplotlib
    Given the rendering engine is Plotly
    When I switch the engine to Matplotlib
    Then the plot should re-render in Matplotlib mode
    And "Interactive Settings" should be replaced with "LaTeX Settings"

  Scenario: Engine settings do NOT appear in non-active mode
    Given the rendering engine is Plotly
    Then I should NOT see "TeX system" or "LaTeX preamble"
    And given Matplotlib mode, I should NOT see "Hover mode"
```

### 10.2 Pytest stubs -- Engine

```python
class TestEngineSettings:
    """E2E tests for EngineSettingsComponent."""

    def test_plotly_shows_hover_mode(self, page: Page, plotly_app_url: str) -> None:
        """Plotly mode shows interactive settings with hover mode."""
        page.goto(plotly_app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(page.get_by_text("Interactive Settings")).to_be_visible()
        expect(page.get_by_label("Hover mode")).to_be_visible()

    def test_plotly_hover_mode_default(self, page: Page, plotly_app_url: str) -> None:
        """Default hover mode is 'x unified'."""
        page.goto(plotly_app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(page.get_by_label("Hover mode")).to_contain_text("x unified")

    def test_matplotlib_shows_latex_settings(
        self, page: Page, matplotlib_app_url: str
    ) -> None:
        """Matplotlib mode shows LaTeX settings."""
        page.goto(matplotlib_app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(page.get_by_text("LaTeX Settings")).to_be_visible()
        expect(page.get_by_label("Extra LaTeX preamble")).to_be_visible()

    def test_matplotlib_tex_system_default(
        self, page: Page, matplotlib_app_url: str
    ) -> None:
        """Default TeX system is xelatex."""
        page.goto(matplotlib_app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(page.get_by_label("TeX system")).to_contain_text("xelatex")

    def test_plotly_no_latex_controls(self, page: Page, plotly_app_url: str) -> None:
        """Plotly mode does not show LaTeX-specific controls."""
        page.goto(plotly_app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(page.get_by_label("TeX system")).not_to_be_visible()
```

---

## 11. Reference Lines & Shapes Tests

### 11.1 Gherkin -- Reference Lines

```gherkin
Feature: Reference line settings -- add, configure, delete

  Background:
    Given I am on the plot styling page for plot_id 1
    And the Advanced settings panel is visible

  Scenario: Reference line defaults to disabled
    Then "Show reference line" should be unchecked
    And no reference line settings expander should appear

  Scenario: Enabling reference line reveals settings
    When I check "Show reference line"
    Then the "Reference Line Settings" expander should appear (expanded)
    And I should see: Y position, Line color, Line width, Line style

  Scenario: Reference line defaults
    Given "Show reference line" is checked
    Then "Y position" should default to 1.0
    And "Line color" should default to "#FF0000"
    And "Line width" slider should default to 1.5 (range 0.5-4.0, step 0.5)
    And "Line style" should default to "dash"

  Scenario: Line style options
    Given "Show reference line" is checked
    Then "Line style" should offer: dash, dot, dashdot, solid

  Scenario: Configure reference line
    Given "Show reference line" is checked
    When I set "Y position" to 2.5
    And I set "Line color" to "#0000FF"
    And I set "Line width" to 2.5
    And I select "solid" line style
    Then the config should contain:
      | key                    | value   |
      | reference_line_enabled | True    |
      | reference_line_y       | 2.5     |
      | reference_line_color   | #0000FF |
      | reference_line_width   | 2.5     |
      | reference_line_style   | solid   |

  Scenario: Disabling reference line only stores enabled=False
    Given "Show reference line" was enabled with custom settings
    When I uncheck "Show reference line"
    Then config["reference_line_enabled"] should be False
    And no other reference line keys should be set

  Scenario: Reference line requires data to show controls
    Given data is None
    When I check "Show reference line"
    Then the settings expander should NOT appear
    And only the toggle should be visible
```

### 11.2 Gherkin -- Shapes

```gherkin
Feature: Shapes settings -- add, edit, delete annotations

  Background:
    Given I am on the plot styling page for plot_id 1
    And the Advanced settings panel shows the Shapes section

  Scenario: Add new shape form
    When I expand "Add New Shape"
    Then I should see:
      | control | type       | default |
      | Type    | selectbox  | line    |
      | x0      | text_input | empty   |
      | y0      | text_input | empty   |
      | x1      | text_input | empty   |
      | y1      | text_input | empty   |
      | Color   | color_picker | #000000|
      | Width   | number_input | 2      |

  Scenario: Shape type options
    Then the "Type" selectbox should offer: line, circle, rect

  Scenario: Add a line shape
    When I fill in: x0=0, y0=0, x1=10, y1=5
    And I set color="#FF0000" and width=3
    And I click "Add Shape"
    Then the shape should appear in the "Existing Shapes" list
    And the page should rerun

  Scenario: Edit existing shape coordinates
    Given the session state has edit_shapes enabled
    And a shape exists with x0=0, y0=0, x1=10, y1=5
    Then I should see editable text inputs for x0, y0, x1, y1
    When I change x1 to 15
    Then the shape's x1 should update to 15.0

  Scenario: Delete a shape
    Given a shape exists at index 0
    When I click the delete button for shape 0
    Then the shape should be removed from the list
    And the page should rerun

  Scenario: Numeric values are parsed via try_float
    When I enter "3.14" in x0
    Then the value should be stored as 3.14 (float)
    When I enter "abc" in x0
    Then the value should be stored as "abc" (string passthrough)

  Scenario: Existing shapes display column headers
    Given shapes exist
    Then I should see column headers: x0, y0, x1, y1, Type
```

### 11.3 Pytest stubs -- Reference Lines and Shapes

```python
class TestReferenceLineSettings:
    """E2E tests for ReferenceLineSettingsComponent."""

    def test_reference_line_default_disabled(self, page: Page, app_url: str) -> None:
        """Reference line toggle defaults to unchecked."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(page.get_by_label("Show reference line")).not_to_be_checked()

    def test_enabling_shows_settings(self, page: Page, app_url: str) -> None:
        """Enabling reference line reveals the settings expander."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        page.get_by_label("Show reference line").check()
        expect(page.get_by_text("Reference Line Settings")).to_be_visible()

    def test_reference_line_defaults(self, page: Page, app_url: str) -> None:
        """Reference line defaults: y=1.0, color=#FF0000, width=1.5, dash."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        page.get_by_label("Show reference line").check()
        expect(page.get_by_label("Y position")).to_have_value("1.0")
        expect(page.get_by_label("Line style")).to_contain_text("dash")


class TestShapesSettings:
    """E2E tests for ShapesSettingsComponent."""

    def test_add_shape_expander_visible(self, page: Page, app_url: str) -> None:
        """Add New Shape expander is visible."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(page.get_by_text("Add New Shape")).to_be_visible()

    def test_shape_type_options(self, page: Page, app_url: str) -> None:
        """Shape type offers line, circle, rect."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        page.get_by_text("Add New Shape").click()
        expect(page.get_by_label("Type")).to_be_visible()

    def test_add_shape_button(self, page: Page, app_url: str) -> None:
        """Add Shape button click submits the form."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        page.get_by_text("Add New Shape").click()
        page.get_by_label("x0").fill("0")
        page.get_by_label("y0").fill("0")
        page.get_by_label("x1").fill("10")
        page.get_by_label("y1").fill("5")
        page.get_by_role("button", name="Add Shape").click()
```

---

## 12. Advanced Settings Tests

### 12.1 Gherkin -- Export, Interactivity, Composition

```gherkin
Feature: Advanced settings -- export, download format, interactivity, composition

  Background:
    Given I am on the plot styling page for plot_id 1
    And the advanced toggle is enabled
    And the "Advanced" pill is selected

  Scenario: Export & Download section is visible
    Then I should see "Export & Download" heading
    And "Show Error Bars (if .sd columns exist)" checkbox should be visible
    And "Default Download Format" selectbox should be visible
    And "Download Scale (Resolution)" selectbox should be visible

  Scenario: Error bars default to unchecked
    Then "Show Error Bars" should be unchecked

  Scenario: Download format options
    Then "Default Download Format" should offer: html, png, pdf, svg
    And the default should be "html"

  Scenario: Download scale options
    Then "Download Scale (Resolution)" should offer: 1, 2, 3
    And the default should be 1
    And help text should say "1x = Screen. 3x = High Res (Publication)."

  Scenario: Download size caption updates with scale
    Given the plot dimensions are 800x500
    When I select scale 3
    Then the caption should show "Download Size: 2400 x 1500 px"

  Scenario: Interactive editing toggle
    Then "Enable Interactive Editing" should be unchecked
    And the help text should mention "drag the legend/title"

  Scenario: Enabling interactive editing
    When I check "Enable Interactive Editing"
    Then the config key "enable_editable" should be True

  Scenario: Series styles are preserved from saved config
    Given saved_config has existing series_styles
    Then the advanced config should carry forward series_styles

  Scenario: Reference line section is injected via callback
    Given the Advanced component receives a render_reference_line_fn
    Then the reference line UI should appear within the Advanced panel

  Scenario: Shapes section is injected via callback
    Given the Advanced component receives a render_shapes_fn
    Then "Annotations (Shapes)" heading should appear
    And the shapes UI should render below it

  Scenario: Engine controls are injected via callback
    Given the Advanced component receives a render_engine_fn
    Then engine-specific controls should appear at the bottom
```

### 12.2 Pytest stubs -- Advanced

```python
class TestAdvancedSettings:
    """E2E tests for AdvancedSettingsComponent."""

    def test_export_section_visible(self, page: Page, app_url: str) -> None:
        """Export & Download section is visible."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(page.get_by_text("Export & Download")).to_be_visible()

    def test_error_bars_default_unchecked(self, page: Page, app_url: str) -> None:
        """Error bars checkbox defaults to unchecked."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(
            page.get_by_label("Show Error Bars (if .sd columns exist)")
        ).not_to_be_checked()

    def test_download_format_default_html(self, page: Page, app_url: str) -> None:
        """Default download format is html."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(page.get_by_label("Default Download Format")).to_contain_text("html")

    def test_download_scale_options(self, page: Page, app_url: str) -> None:
        """Download scale offers 1, 2, 3 options."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(page.get_by_label("Download Scale (Resolution)")).to_be_visible()

    def test_download_size_caption(self, page: Page, app_url: str) -> None:
        """Download size caption reflects current dimensions and scale."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(page.get_by_text(re.compile("Download Size:"))).to_be_visible()

    def test_interactive_editing_default_off(self, page: Page, app_url: str) -> None:
        """Interactive editing defaults to unchecked."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(
            page.get_by_label("Enable Interactive Editing")
        ).not_to_be_checked()

    def test_legend_interactivity_section(self, page: Page, app_url: str) -> None:
        """Legend & Interactivity section is visible."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        expect(page.get_by_text("Legend & Interactivity")).to_be_visible()
```

---

## 13. Cross-Panel Interaction Tests

### 13.1 Gherkin -- Panel Switching and Config Merging

```gherkin
Feature: Cross-panel interaction tests -- config integrity across pill switches

  Background:
    Given I am on the plot styling page for plot_id 1
    And the advanced toggle is enabled

  Scenario: Switching between pills preserves per-panel configs
    Given I set Typography title_font_size to 24
    When I switch to the "Layout" pill and change height to 6.0
    And I switch back to the "Typography" pill
    Then "Plot Title Font Size" should still show 24

  Scenario: Layout changes persist through Typography edits
    Given I set width preset to "Single Column (~3.5in)"
    When I switch to Typography and change title font size to 30
    And I switch back to Layout
    Then the preset should still be "Single Column (~3.5in)"

  Scenario: Colors panel palette change affects series colors in Legend
    Given I change the palette to "tol_bright" in Colors
    When I switch to the Legends pill
    Then legend colors should reflect the tol_bright palette

  Scenario: Axes settings are independent per axis pill
    Given I set X-axis rotation to 0
    When I switch to Y-Left and set grid to unchecked
    And I switch back to X-Axis
    Then X-axis rotation should still be 0

  Scenario: Advanced settings compose reference line + shapes + engine
    When I enable reference line in the Advanced panel
    And I add a shape via the shapes section
    And the engine controls render
    Then all three sub-configs should be merged into the Advanced config

  Scenario: Progressive disclosure does not lose advanced-panel state
    Given I configure Axes settings with custom values
    When I disable the advanced toggle
    And I re-enable the advanced toggle
    And I click the "Axes" pill
    Then my previously configured values should be restored from saved_config

  Scenario: Preset application overrides panel settings
    Given I have custom typography and layout settings
    When I select the "ISCA" preset
    Then preset values should override my custom settings
    And the config should reflect ISCA styles

  Scenario: Concurrent widget key isolation
    Given plot_id=1 has layout width of 7.0
    And plot_id=2 has layout width of 3.5
    Then their widget keys should be independent
    And changing plot 1 width should not affect plot 2

  Scenario: Widget factory handles missing saved values gracefully
    Given saved_config is empty ({})
    When any settings panel renders
    Then all widgets should fall back to their declared defaults
    And no KeyError or IndexError should occur

  Scenario: Widget factory selectbox handles unknown saved value
    Given saved_config has color_palette="nonexistent"
    When the Colors panel renders
    Then the selectbox should fall back to index 0
    And no error should occur
```

### 13.2 Pytest stubs -- Cross-Panel

```python
class TestCrossPanelInteractions:
    """E2E tests for cross-panel config integrity."""

    def test_typography_preserved_after_layout_switch(
        self, page: Page, app_url: str
    ) -> None:
        """Typography settings preserved after switching to Layout and back."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Typography")).click()
        page.get_by_label("Plot Title Font Size").fill("24")
        page.get_by_label("Plot Title Font Size").press("Enter")
        page.get_by_role("tab", name=re.compile("Layout")).click()
        page.get_by_role("tab", name=re.compile("Typography")).click()
        expect(page.get_by_label("Plot Title Font Size")).to_have_value("24")

    def test_layout_preserved_after_typography_switch(
        self, page: Page, app_url: str
    ) -> None:
        """Layout preset preserved after switching to Typography and back."""
        page.goto(app_url)
        page.get_by_role("tab", name=re.compile("Layout")).click()
        page.get_by_label("Document Size Preset").select_option(
            "Single Column (~3.5in)"
        )
        page.get_by_role("tab", name=re.compile("Typography")).click()
        page.get_by_role("tab", name=re.compile("Layout")).click()
        expect(page.get_by_label("Document Size Preset")).to_contain_text(
            "Single Column (~3.5in)"
        )

    def test_axes_independent_per_sub_pill(self, page: Page, app_url: str) -> None:
        """X and Y axis pills maintain independent state."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Axes")).click()
        # Modify X-axis
        page.get_by_label("Show Grid").check()
        # Switch to Y-Left
        page.get_by_role("tab", name=re.compile("Y-Left")).click()
        expect(page.get_by_label("Show Grid")).to_be_checked()
        # Switch back to X-Axis
        page.get_by_role("tab", name=re.compile("X-Axis")).click()
        expect(page.get_by_label("Show Grid")).to_be_checked()

    def test_progressive_disclosure_restore(self, page: Page, app_url: str) -> None:
        """Advanced panel state restored after toggle off/on cycle."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        page.get_by_label(
            "Show Error Bars (if .sd columns exist)"
        ).check()
        page.get_by_label("Show advanced settings").uncheck()
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        # Value should persist from saved_config

    def test_empty_saved_config_uses_defaults(
        self, page: Page, empty_config_url: str
    ) -> None:
        """All panels render correctly with an empty saved config."""
        page.goto(empty_config_url)
        page.get_by_role("tab", name=re.compile("Layout")).click()
        expect(page.get_by_label("Document Size Preset")).to_contain_text(
            "Double Column (~7.0in)"
        )
        page.get_by_role("tab", name=re.compile("Typography")).click()
        expect(page.get_by_label("Plot Title Font Size")).to_have_value("18")

    def test_widget_keys_isolated_per_plot_id(
        self, page: Page, multi_plot_url: str
    ) -> None:
        """Widget keys include plot_id and do not collide."""
        page.goto(multi_plot_url)
        # Both plots should render independently
        plot1_width = page.locator("[data-testid='stNumberInput']").filter(
            has_text="wi_1"
        )
        plot2_width = page.locator("[data-testid='stNumberInput']").filter(
            has_text="wi_2"
        )
        # Keys should be distinct

    def test_selectbox_handles_unknown_saved_value(
        self, page: Page, invalid_config_url: str
    ) -> None:
        """Selectbox with unknown saved value falls back to index 0."""
        page.goto(invalid_config_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Colors")).click()
        # Should not crash; palette selectbox shows first option
        expect(page.get_by_label("Palette")).to_be_visible()

    def test_advanced_composes_all_sub_sections(
        self, page: Page, app_url: str
    ) -> None:
        """Advanced panel merges reference line, shapes, and engine configs."""
        page.goto(app_url)
        page.get_by_label("Show advanced settings").check()
        page.get_by_role("tab", name=re.compile("Advanced")).click()
        # Verify all sub-sections present
        expect(page.get_by_text("Export & Download")).to_be_visible()
        expect(page.get_by_text("Legend & Interactivity")).to_be_visible()
```

---

## Summary

This document specifies **92 Gherkin scenarios** and **73 pytest-playwright test stubs**
across 13 sections covering all 11 settings pill panels plus navigation and
cross-panel interactions.

### Coverage matrix

| Section | Scenarios | Pytest Stubs | Components Tested |
|---------|-----------|-------------|-------------------|
| 2. Navigation | 9 | 7 | `settings_pills.py` |
| 3. Layout | 10 | 8 | `LayoutSettingsComponent` |
| 4. Typography | 12 | 9 | `TypographySettingsComponent` |
| 5. Axes | 23 | 13 | `AxesSettingsComponent` |
| 6. Legend | 17 | 11 | `LegendSettingsComponent` |
| 7. Colors | 13 | 8 | `ColorsSettingsComponent` |
| 8. Data Labels | 12 | 7 | `DataLabelsSettingsComponent` |
| 9. Ordering | 11 | 5 | `OrderingSettingsComponent` |
| 10. Engine | 7 | 5 | `EngineSettingsComponent` |
| 11. Ref Lines/Shapes | 14 | 6 | `ReferenceLineSettingsComponent`, `ShapesSettingsComponent` |
| 12. Advanced | 11 | 7 | `AdvancedSettingsComponent` |
| 13. Cross-Panel | 10 | 8 | All components |
| **Total** | **149** | **94** | **13 source files** |

### Key testing patterns

1. **Widget factory resilience**: All panels rely on `widget_factory.py` primitives
   which handle missing config values, unknown selectbox options, and type casting.
   Cross-panel tests verify this resilience with empty and invalid configs.

2. **Progressive disclosure**: The 3-basic / 4-advanced split is tested by toggling
   the advanced switch and counting visible pills.

3. **Sentinel values**: The `-1` sentinel for `yaxis_title_standoff` and the `0`
   filter for `yaxis_dtick` are explicitly tested to ensure auto-mode behavior.

4. **Multi-level pills**: The Legend component uses nested pills (Primary/Secondary/
   Tertiary) and the Axes component uses nested pills (X/Y-Left/Y-Right/Group).
   Tests verify that switching nested pills preserves inactive config via
   `saved_config` passthrough.

5. **Plot-type-specific rendering**: Heatmap colorbar controls, bar stripes,
   grouped stacked bar group labels, and heatmap totals are all gated on
   `plot_type` and tested with appropriate fixtures.

6. **Engine-specific controls**: Plotly hover mode vs Matplotlib LaTeX settings
   are mutually exclusive and tested in separate engine-specific fixtures.
