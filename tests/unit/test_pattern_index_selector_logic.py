"""Concrete source selector keeps numeric labels separate from selected identities."""

from unittest.mock import patch

from src.web.components.data_source.pattern_index_selector import PatternIndexSelector


def test_selection_uses_source_names_and_never_reconstructs_numeric_coordinates():
    # [test->req~ring5.ingestion.pattern-index-selection~1]
    instances = [
        {"source_name": "cpu012.ipc", "indices": ["012"]},
        {"source_name": "cpu2.ipc", "indices": ["2"]},
    ]
    with (
        patch("src.web.components.data_source.pattern_index_selector.st") as st,
        patch(
            "src.web.components.data_source.pattern_index_selector.filtered_multiselect",
            return_value=["cpu012.ipc"],
        ) as select,
    ):
        st.checkbox.return_value = True
        assert PatternIndexSelector.render_selector(
            r"cpu\d+.ipc", instances, "v", ["cpu012.ipc"]
        ) == (True, ["cpu012.ipc"])
        assert select.call_args.kwargs["options"] == ["cpu012.ipc", "cpu2.ipc"]
        formatter = select.call_args.kwargs["format_func"]
        assert "012" in formatter("cpu012.ipc")
        assert "cpu012.ipc" in formatter("cpu012.ipc")


def test_unknown_saved_source_is_visibly_preserved():
    with patch("src.web.components.data_source.pattern_index_selector.st") as st:
        st.checkbox.return_value = True
        assert PatternIndexSelector.render_selector(r"cpu\d+", [], "v", ["cpu9"]) == (
            True,
            ["cpu9"],
        )
        st.error.assert_called_once()
