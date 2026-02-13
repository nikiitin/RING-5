"""Tests for SplitApplyConfig shaper UI component — coverage."""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pandas as pd

# ── Helpers ───────────────────────────────────────────────────────


def _ctx_mgr() -> MagicMock:
    """Return a MagicMock usable as a context manager."""
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=m)
    m.__exit__ = MagicMock(return_value=False)
    return m


def _sample_data() -> pd.DataFrame:
    """DataFrame with 2 categorical + 2 numeric columns."""
    return pd.DataFrame(
        {
            "benchmark": ["mcf", "mcf", "omnet", "omnet"],
            "config": ["base", "opt", "base", "opt"],
            "ipc": [1.2, 1.5, 1.4, 1.6],
            "cycles": [3210, 2890, 7890, 7120],
        }
    )


# ── TestSplitApplyConfigRender ────────────────────────────────────


_MOD = "src.web.pages.ui.components.shapers.split_apply_config"


class TestSplitApplyConfigRender:
    """Test the top-level render() with 0 sub-pipeline steps."""

    @patch(f"{_MOD}.st")
    def test_render_basic_no_steps(self, mock_st: MagicMock) -> None:
        """render() with 0 steps returns joinColumns + 2 empty groups."""
        from src.web.pages.ui.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()

        # st.multiselect calls:
        #   1: join columns  →  ["benchmark", "config"]
        #   2: group A numeric cols  →  ["ipc"]
        #   3: group B numeric cols  →  ["cycles"]
        mock_st.multiselect.side_effect = [
            ["benchmark", "config"],
            ["ipc"],
            ["cycles"],
        ]

        # st.columns(2) is called 3 times:
        #   1: [col_a, col_b]  (groups layout)
        #   2: [bc1, bc2]       (sub-pipeline buttons group A)
        #   3: [bc1, bc2]       (sub-pipeline buttons group B)
        mock_st.columns.side_effect = [
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
        ]

        # session_state as dict — step counts start at 0
        mock_st.session_state = {}

        # buttons return False (no add / remove)
        mock_st.button.return_value = False

        result: Dict[str, Any] = SplitApplyConfig.render(
            data=data,
            existing_config={},
            key_prefix="p_",
            shaper_id="x",
        )

        assert result["joinColumns"] == ["benchmark", "config"]
        assert len(result["groups"]) == 2
        assert result["groups"][0]["columns"] == ["ipc"]
        assert result["groups"][0]["pipeline"] == []
        assert result["groups"][1]["columns"] == ["cycles"]
        assert result["groups"][1]["pipeline"] == []

    @patch(f"{_MOD}.st")
    def test_render_restores_existing_join(self, mock_st: MagicMock) -> None:
        """render() passes existing joinColumns as defaults."""
        from src.web.pages.ui.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()

        mock_st.multiselect.side_effect = [
            ["benchmark"],  # user only kept benchmark
            [],
            [],
        ]
        mock_st.columns.side_effect = [
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
        ]
        mock_st.session_state = {}
        mock_st.button.return_value = False

        result: Dict[str, Any] = SplitApplyConfig.render(
            data=data,
            existing_config={"joinColumns": ["benchmark"]},
            key_prefix="p_",
            shaper_id="x",
        )

        assert result["joinColumns"] == ["benchmark"]


class TestSplitApplyConfigMeanStep:
    """Test render path with a Mean sub-step in group A."""

    @patch(f"{_MOD}.st")
    def test_one_mean_step(self, mock_st: MagicMock) -> None:
        """A group with 1 Mean step returns proper config."""
        from src.web.pages.ui.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()

        # multiselect calls:
        #   1: join cols
        #   2: group A numeric cols
        #   3: mean step groupingColumns
        #   4: group B numeric cols
        mock_st.multiselect.side_effect = [
            ["benchmark", "config"],  # join
            ["ipc"],  # group A columns
            ["config"],  # mean groupingColumns
            ["cycles"],  # group B columns
        ]

        # selectbox calls (only for mean step in group A):
        #   1: Transformation → "Mean Calculator"
        #   2: Mean type → "arithmean"
        #   3: Replacing column → "benchmark"
        mock_st.selectbox.side_effect = [
            "Mean Calculator",
            "arithmean",
            "benchmark",
        ]

        # columns: groups, groupA buttons, groupB buttons
        mock_st.columns.side_effect = [
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
        ]

        # session_state: group A has 1 step, group B has 0
        mock_st.session_state = {
            "p_sa_g0_x_step_count": 1,
        }
        mock_st.button.return_value = False

        result: Dict[str, Any] = SplitApplyConfig.render(
            data=data,
            existing_config={},
            key_prefix="p_",
            shaper_id="x",
        )

        grp_a: Dict[str, Any] = result["groups"][0]
        assert len(grp_a["pipeline"]) == 1
        step: Dict[str, Any] = grp_a["pipeline"][0]
        assert step["type"] == "mean"
        assert step["meanAlgorithm"] == "arithmean"
        assert step["meanVars"] == ["ipc"]
        assert step["groupingColumns"] == ["config"]
        assert step["replacingColumn"] == "benchmark"


class TestSplitApplyConfigNormalizeStep:
    """Test render path with a Normalize sub-step."""

    @patch(f"{_MOD}.st")
    def test_one_normalize_step(self, mock_st: MagicMock) -> None:
        """A group with 1 Normalize step returns proper config."""
        from src.web.pages.ui.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()

        # multiselect:
        #   1: join cols
        #   2: group A numeric cols
        #   3: normalize groupBy
        #   4: group B numeric cols
        mock_st.multiselect.side_effect = [
            ["benchmark", "config"],
            ["ipc"],
            ["config"],  # norm groupBy
            ["cycles"],
        ]

        # selectbox:
        #   1: Transformation → "Normalize"
        #   2: normalizerColumn → "config"
        #   3: normalizerValue (baseline) → "base"
        mock_st.selectbox.side_effect = [
            "Normalize",
            "config",
            "base",
        ]

        mock_st.columns.side_effect = [
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
        ]

        mock_st.session_state = {
            "p_sa_g0_x_step_count": 1,
        }
        mock_st.button.return_value = False

        result: Dict[str, Any] = SplitApplyConfig.render(
            data=data,
            existing_config={},
            key_prefix="p_",
            shaper_id="x",
        )

        grp_a: Dict[str, Any] = result["groups"][0]
        assert len(grp_a["pipeline"]) == 1
        step: Dict[str, Any] = grp_a["pipeline"][0]
        assert step["type"] == "normalize"
        assert step["normalizeVars"] == ["ipc"]
        assert step["normalizerVars"] == ["ipc"]
        assert step["normalizerColumn"] == "config"
        assert step["normalizerValue"] == "base"
        assert step["groupBy"] == ["config"]


class TestSplitApplyConfigSortStep:
    """Test render path delegated to SortConfig."""

    @patch(
        f"{_MOD}.SplitApplyConfig._render_sub_step",
        return_value={"type": "sort", "order_dict": {"config": ["opt", "base"]}},
    )
    @patch(f"{_MOD}.st")
    def test_sort_step_dispatches(self, mock_st: MagicMock, _mock_sub: MagicMock) -> None:
        """Sort delegation produces correct config."""
        from src.web.pages.ui.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()

        mock_st.multiselect.side_effect = [
            ["benchmark", "config"],
            ["ipc"],
            ["cycles"],
        ]
        mock_st.columns.side_effect = [
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
        ]
        mock_st.session_state = {"p_sa_g0_x_step_count": 1}
        mock_st.button.return_value = False

        result: Dict[str, Any] = SplitApplyConfig.render(
            data=data,
            existing_config={},
            key_prefix="p_",
            shaper_id="x",
        )
        # _render_sub_step was mocked to return sort config
        assert result["groups"][0]["pipeline"][0]["type"] == "sort"


class TestSplitApplyConfigExistingPipeline:
    """Test that existing pipeline config is passed through."""

    @patch(f"{_MOD}.st")
    def test_existing_config_mean_step(self, mock_st: MagicMock) -> None:
        """Existing mean step config is used for default values."""
        from src.web.pages.ui.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()

        existing: Dict[str, Any] = {
            "joinColumns": ["benchmark", "config"],
            "groups": [
                {
                    "columns": ["ipc"],
                    "pipeline": [
                        {
                            "type": "mean",
                            "meanAlgorithm": "geomean",
                            "meanVars": ["ipc"],
                            "groupingColumns": ["config"],
                            "replacingColumn": "benchmark",
                        }
                    ],
                },
                {"columns": ["cycles"], "pipeline": []},
            ],
        }

        # multiselect:
        #   1: join cols  →  ["benchmark", "config"]
        #   2: group A numeric cols  →  ["ipc"]
        #   3: mean groupingColumns  →  ["config"]
        #   4: group B numeric cols  →  ["cycles"]
        mock_st.multiselect.side_effect = [
            ["benchmark", "config"],
            ["ipc"],
            ["config"],
            ["cycles"],
        ]

        # selectbox:
        #   1: Transformation → "Mean Calculator" (from existing type)
        #   2: Mean type → "geomean" (from existing)
        #   3: Replacing column → "benchmark"
        mock_st.selectbox.side_effect = [
            "Mean Calculator",
            "geomean",
            "benchmark",
        ]

        mock_st.columns.side_effect = [
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
        ]

        # session_state is set from existing pipeline count
        mock_st.session_state = {}  # will be initialized from existing_count
        mock_st.button.return_value = False

        result: Dict[str, Any] = SplitApplyConfig.render(
            data=data,
            existing_config=existing,
            key_prefix="p_",
            shaper_id="x",
        )

        grp_a: Dict[str, Any] = result["groups"][0]
        assert len(grp_a["pipeline"]) == 1
        assert grp_a["pipeline"][0]["meanAlgorithm"] == "geomean"


class TestSplitApplyConfigSubStepDirect:
    """Direct tests on _render_sub_step for each shaper type."""

    @patch(f"{_MOD}.st")
    def test_mean_sub_step(self, mock_st: MagicMock) -> None:
        """_render_sub_step dispatches to _render_mean_step."""
        from src.web.pages.ui.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()
        cat_cols: List[str] = ["benchmark", "config"]

        mock_st.selectbox.side_effect = [
            "Mean Calculator",  # Transformation
            "arithmean",  # Mean type
            "benchmark",  # Replacing column
        ]
        mock_st.multiselect.return_value = ["config"]  # groupBy

        result = SplitApplyConfig._render_sub_step(
            data=data,
            columns=["ipc"],
            join_columns=cat_cols,
            categorical_cols=cat_cols,
            existing_step={},
            key_base="k",
            step_index=0,
        )

        assert result is not None
        assert result["type"] == "mean"
        assert result["meanVars"] == ["ipc"]

    @patch(f"{_MOD}.st")
    def test_normalize_sub_step(self, mock_st: MagicMock) -> None:
        """_render_sub_step dispatches to _render_normalize_step."""
        from src.web.pages.ui.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()
        cat_cols: List[str] = ["benchmark", "config"]

        mock_st.selectbox.side_effect = [
            "Normalize",  # Transformation
            "config",  # normalizerColumn
            "base",  # normalizerValue
        ]
        mock_st.multiselect.return_value = ["config"]

        result = SplitApplyConfig._render_sub_step(
            data=data,
            columns=["ipc"],
            join_columns=cat_cols,
            categorical_cols=cat_cols,
            existing_step={},
            key_base="k",
            step_index=0,
        )

        assert result is not None
        assert result["type"] == "normalize"

    @patch(
        "src.web.pages.ui.components.shapers.sort_config.SortConfig.render",
        return_value={"order_dict": {}},
    )
    @patch(f"{_MOD}.st")
    def test_sort_sub_step(self, mock_st: MagicMock, _mock_sort: MagicMock) -> None:
        """_render_sub_step dispatches to SortConfig.render."""
        from src.web.pages.ui.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()
        cat_cols: List[str] = ["benchmark", "config"]

        mock_st.selectbox.return_value = "Sort"

        result = SplitApplyConfig._render_sub_step(
            data=data,
            columns=["ipc"],
            join_columns=cat_cols,
            categorical_cols=cat_cols,
            existing_step={},
            key_base="k",
            step_index=0,
        )

        assert result is not None
        assert result["type"] == "sort"

    @patch(
        "src.web.pages.ui.components.shapers.selector_transformer_configs"
        ".ConditionSelectorConfig.render",
        return_value={"conditionColumn": "benchmark"},
    )
    @patch(f"{_MOD}.st")
    def test_filter_sub_step(self, mock_st: MagicMock, _mock_filter: MagicMock) -> None:
        """_render_sub_step dispatches to ConditionSelectorConfig.render."""
        from src.web.pages.ui.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()
        cat_cols: List[str] = ["benchmark", "config"]

        mock_st.selectbox.return_value = "Filter"

        result = SplitApplyConfig._render_sub_step(
            data=data,
            columns=["ipc"],
            join_columns=cat_cols,
            categorical_cols=cat_cols,
            existing_step={},
            key_base="k",
            step_index=0,
        )

        assert result is not None
        assert result["type"] == "conditionSelector"


class TestSplitApplyConfigNormalizeEdge:
    """Edge cases for the normalize step renderer."""

    @patch(f"{_MOD}.st")
    def test_normalizer_column_not_in_data(self, mock_st: MagicMock) -> None:
        """When normalizerColumn is not in data, no baseline selectbox."""
        from src.web.pages.ui.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        # Data with columns that don't match the returned normalizer col
        data: pd.DataFrame = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        cat_cols: List[str] = ["benchmark", "config"]

        # selectbox returns "" for normalizer column (empty)
        mock_st.selectbox.side_effect = [
            "Normalize",  # Transformation
            "",  # normalizerColumn → empty
        ]
        mock_st.multiselect.return_value = []

        result = SplitApplyConfig._render_sub_step(
            data=data,
            columns=["x"],
            join_columns=cat_cols,
            categorical_cols=cat_cols,
            existing_step={},
            key_base="k",
            step_index=0,
        )

        assert result is not None
        assert result["normalizerValue"] is None
