"""Tests for web.rendering.relayout — Plotly relayout-event decoding.

Decoding a Plotly client-side relayout payload into engine-agnostic config
updates is presentation logic (it understands Plotly's wire format), so it
lives in the web rendering layer rather than core.
"""

from src.web.rendering.relayout import update_config_from_relayout


class TestUpdateConfigFromRelayout:
    """Tests for relayout event processing."""

    def test_empty_relayout_returns_unchanged(self) -> None:
        config = {"range_x": [0, 10]}
        new_config, changed = update_config_from_relayout(config, {})
        assert changed is False
        assert new_config == config

    def test_none_relayout_returns_unchanged(self) -> None:
        config = {"range_x": None}
        new_config, changed = update_config_from_relayout(config, {})
        assert changed is False

    def test_xaxis_zoom_range_bracket(self) -> None:
        config = {"range_x": None}
        relayout = {"xaxis.range[0]": 0, "xaxis.range[1]": 10}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["range_x"] == [0, 10]

    def test_xaxis_zoom_range_direct(self) -> None:
        config = {"range_x": None}
        relayout = {"xaxis.range": [5, 15]}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["range_x"] == [5, 15]

    def test_yaxis_zoom_range_bracket(self) -> None:
        config = {"range_y": None}
        relayout = {"yaxis.range[0]": -5, "yaxis.range[1]": 5}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["range_y"] == [-5, 5]

    def test_autorange_resets_x(self) -> None:
        config = {"range_x": [0, 10], "range_y": [0, 5]}
        relayout = {"xaxis.autorange": True}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["range_x"] is None
        assert new_config["range_y"] == [0, 5]  # Unchanged

    def test_autorange_resets_y(self) -> None:
        config = {"range_y": [0, 5]}
        relayout = {"yaxis.autorange": True}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["range_y"] is None

    def test_autorange_no_change_when_already_none(self) -> None:
        config = {"range_x": None}
        relayout = {"xaxis.autorange": True}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is False

    def test_legend_drag_position(self) -> None:
        config: dict = {}
        relayout = {"legend.x": 0.5, "legend.y": 0.9}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["legend_x"] == 0.5
        assert new_config["legend_y"] == 0.9
        assert new_config["legend_xanchor"] == "left"
        assert new_config["legend_yanchor"] == "top"

    def test_legend2_drag_position(self) -> None:
        config: dict = {}
        relayout = {"legend2.x": 0.3, "legend2.y": 0.7}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["legend2_x"] == 0.3
        assert new_config["legend2_y"] == 0.7

    def test_legend_anchor(self) -> None:
        config: dict = {}
        relayout = {"legend.xanchor": "right"}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["legend_xanchor"] == "right"

    def test_legend_title_text(self) -> None:
        config = {"legend_title": "Old Title"}
        relayout = {"legend.title.text": "New Title"}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["legend_title"] == "New Title"

    def test_same_value_no_change(self) -> None:
        config = {"range_x": [0, 10]}
        relayout = {"xaxis.range[0]": 0, "xaxis.range[1]": 10}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is False

    def test_float_close_no_change(self) -> None:
        """Values within floating point tolerance should not trigger change."""
        config = {"range_x": [5.0, 10.0]}
        relayout = {
            "xaxis.range[0]": 5.0 + 5e-12,
            "xaxis.range[1]": 10.0 - 1e-11,
        }
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is False

    def test_does_not_mutate_original_config(self) -> None:
        config = {"range_x": None}
        relayout = {"xaxis.range[0]": 0, "xaxis.range[1]": 10}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert config["range_x"] is None  # Original unchanged
        assert new_config["range_x"] == [0, 10]

    def test_ignores_non_legend_keys(self) -> None:
        config: dict = {}
        relayout = {"some_other_key": 42}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is False

    def test_ignores_legend_key_without_dot(self) -> None:
        config: dict = {}
        relayout = {"legend": True}  # No dot-separated property
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is False

    def test_combined_zoom_and_legend(self) -> None:
        config = {"range_x": None, "legend_x": None}
        relayout = {
            "xaxis.range[0]": 1,
            "xaxis.range[1]": 5,
            "legend.x": 0.8,
        }
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["range_x"] == [1, 5]
        assert new_config["legend_x"] == 0.8
