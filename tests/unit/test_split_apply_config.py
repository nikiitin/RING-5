"""Tests for SplitApplyConfig shaper UI component — N-group delegation."""

from typing import Any, cast
from unittest.mock import MagicMock, patch

import pandas as pd

from src.core.models.shaper_models import ShaperStepConfig

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


def _sample_data_4cols() -> pd.DataFrame:
    """DataFrame with 2 categorical + 4 numeric columns."""
    return pd.DataFrame(
        {
            "benchmark": ["mcf", "omnet"],
            "config": ["base", "opt"],
            "v1": [1.0, 2.0],
            "v2": [10.0, 20.0],
            "v3": [100.0, 200.0],
            "v4": [1000.0, 2000.0],
        }
    )


# ── Module path for patching ─────────────────────────────────────

_MOD = "src.web.components.shapers.split_apply_config"


# ── TestSplitApplyConfigRender (2 groups, no sub-steps) ──────────


class TestSplitApplyConfigRender:
    """Test the top-level render() with 0 sub-pipeline steps."""

    @patch(f"{_MOD}._init_dispatch")
    @patch(f"{_MOD}.st")
    def test_render_basic_no_steps(self, mock_st: MagicMock, _mock_init: MagicMock) -> None:
        """render() with 0 steps returns joinColumns + 2 empty groups."""
        from src.web.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()

        # multiselect calls:
        #   1: join columns → ["benchmark", "config"]
        #   2: group 0 numeric cols → ["ipc"]
        #   3: group 1 numeric cols → ["cycles"]
        mock_st.multiselect.side_effect = [
            ["benchmark", "config"],
            ["ipc"],
            ["cycles"],
        ]

        # slider returns 2 (default)
        mock_st.slider.return_value = 2

        # expander returns context managers
        mock_st.expander.side_effect = [_ctx_mgr(), _ctx_mgr()]

        # columns(2) for add/remove buttons in each group
        mock_st.columns.side_effect = [
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
        ]

        mock_st.session_state = {}
        mock_st.button.return_value = False

        result = SplitApplyConfig.render(
            data=data,
            existing_config=cast(Any, {}),
            key_prefix="p_",
            shaper_id=0,
        )

        assert result.get("joinColumns") == ["benchmark", "config"]
        groups = result.get("groups", [])
        assert len(groups) == 2
        assert groups[0].get("columns") == ["ipc"]
        assert groups[0].get("pipeline") == []
        assert groups[1].get("columns") == ["cycles"]
        assert groups[1].get("pipeline") == []

    @patch(f"{_MOD}._init_dispatch")
    @patch(f"{_MOD}.st")
    def test_render_restores_existing_join(self, mock_st: MagicMock, _mock_init: MagicMock) -> None:
        """render() passes existing joinColumns as defaults."""
        from src.web.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()

        mock_st.multiselect.side_effect = [
            ["benchmark"],
            [],
            [],
        ]
        mock_st.slider.return_value = 2
        mock_st.expander.side_effect = [_ctx_mgr(), _ctx_mgr()]
        mock_st.columns.side_effect = [
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
        ]
        mock_st.session_state = {}
        mock_st.button.return_value = False

        result = SplitApplyConfig.render(
            data=data,
            existing_config=cast(Any, {"joinColumns": ["benchmark"]}),
            key_prefix="p_",
            shaper_id=0,
        )

        assert result.get("joinColumns") == ["benchmark"]


# ── TestSplitApplyConfigSubStepDelegation ────────────────────────


class TestSplitApplyConfigSubStepDelegation:
    """Test that _render_sub_step delegates to real config renderers."""

    @patch(
        f"{_MOD}._SUB_SHAPER_DISPATCH",
        {
            "Mean Calculator": (
                "mean",
                MagicMock(
                    return_value={
                        "meanAlgorithm": "arithmean",
                        "meanVars": ["ipc"],
                        "groupingColumns": ["config"],
                        "replacingColumn": "benchmark",
                    }
                ),
            ),
            "Normalize": ("normalize", MagicMock(return_value={})),
            "Sort": ("sort", MagicMock(return_value={})),
            "Filter": ("conditionSelector", MagicMock(return_value={})),
        },
    )
    @patch(f"{_MOD}.st")
    def test_mean_delegates_to_real_renderer(self, mock_st: MagicMock) -> None:
        """_render_sub_step chooses Mean and delegates to MeanConfig."""
        from src.web.components.shapers.split_apply_config import (
            _SUB_SHAPER_DISPATCH,
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()

        mock_st.selectbox.return_value = "Mean Calculator"

        result = SplitApplyConfig._render_sub_step(
            data=data,
            columns=["ipc"],
            join_columns=["benchmark", "config"],
            categorical_cols=["benchmark", "config"],
            existing_step=cast(Any, {}),
            key_base="k",
            step_index=0,
        )

        assert result is not None
        assert result.get("type") == "mean"
        assert result.get("meanAlgorithm") == "arithmean"

        # Verify the real render function was called
        _, render_fn = _SUB_SHAPER_DISPATCH["Mean Calculator"]
        render_fn.assert_called_once()  # type: ignore[attr-defined]

    @patch(
        f"{_MOD}._SUB_SHAPER_DISPATCH",
        {
            "Mean Calculator": ("mean", MagicMock(return_value={})),
            "Normalize": (
                "normalize",
                MagicMock(
                    return_value={
                        "normalizerVars": ["ipc"],
                        "normalizeVars": ["ipc"],
                        "normalizerColumn": "config",
                        "normalizerValue": "base",
                        "groupBy": ["benchmark"],
                    }
                ),
            ),
            "Sort": ("sort", MagicMock(return_value={})),
            "Filter": ("conditionSelector", MagicMock(return_value={})),
        },
    )
    @patch(f"{_MOD}.st")
    def test_normalize_delegates_to_real_renderer(self, mock_st: MagicMock) -> None:
        """_render_sub_step chooses Normalize and delegates."""
        from src.web.components.shapers.split_apply_config import (
            _SUB_SHAPER_DISPATCH,
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()
        mock_st.selectbox.return_value = "Normalize"

        result = SplitApplyConfig._render_sub_step(
            data=data,
            columns=["ipc"],
            join_columns=["benchmark", "config"],
            categorical_cols=["benchmark", "config"],
            existing_step=cast(Any, {}),
            key_base="k",
            step_index=0,
        )

        assert result is not None
        assert result.get("type") == "normalize"
        assert result.get("normalizerColumn") == "config"

        _, render_fn = _SUB_SHAPER_DISPATCH["Normalize"]
        render_fn.assert_called_once()  # type: ignore[attr-defined]

    @patch(
        f"{_MOD}._SUB_SHAPER_DISPATCH",
        {
            "Mean Calculator": ("mean", MagicMock(return_value={})),
            "Normalize": ("normalize", MagicMock(return_value={})),
            "Sort": (
                "sort",
                MagicMock(
                    return_value={
                        "order_dict": {"config": ["opt", "base"]},
                    }
                ),
            ),
            "Filter": ("conditionSelector", MagicMock(return_value={})),
        },
    )
    @patch(f"{_MOD}.st")
    def test_sort_delegates_to_real_renderer(self, mock_st: MagicMock) -> None:
        """_render_sub_step chooses Sort and delegates to SortConfig."""
        from src.web.components.shapers.split_apply_config import (
            _SUB_SHAPER_DISPATCH,
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()
        mock_st.selectbox.return_value = "Sort"

        result = SplitApplyConfig._render_sub_step(
            data=data,
            columns=["ipc"],
            join_columns=["benchmark", "config"],
            categorical_cols=["benchmark", "config"],
            existing_step=cast(Any, {}),
            key_base="k",
            step_index=0,
        )

        assert result is not None
        assert result.get("type") == "sort"

        _, render_fn = _SUB_SHAPER_DISPATCH["Sort"]
        render_fn.assert_called_once()  # type: ignore[attr-defined]

    @patch(
        f"{_MOD}._SUB_SHAPER_DISPATCH",
        {
            "Mean Calculator": ("mean", MagicMock(return_value={})),
            "Normalize": ("normalize", MagicMock(return_value={})),
            "Sort": ("sort", MagicMock(return_value={})),
            "Filter": (
                "conditionSelector",
                MagicMock(
                    return_value={
                        "conditionColumn": "benchmark",
                    }
                ),
            ),
        },
    )
    @patch(f"{_MOD}.st")
    def test_filter_delegates_to_real_renderer(self, mock_st: MagicMock) -> None:
        """_render_sub_step chooses Filter and delegates."""
        from src.web.components.shapers.split_apply_config import (
            _SUB_SHAPER_DISPATCH,
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()
        mock_st.selectbox.return_value = "Filter"

        result = SplitApplyConfig._render_sub_step(
            data=data,
            columns=["ipc"],
            join_columns=["benchmark", "config"],
            categorical_cols=["benchmark", "config"],
            existing_step=cast(Any, {}),
            key_base="k",
            step_index=0,
        )

        assert result is not None
        assert result.get("type") == "conditionSelector"

        _, render_fn = _SUB_SHAPER_DISPATCH["Filter"]
        render_fn.assert_called_once()  # type: ignore[attr-defined]


# ── TestSplitApplyConfigWithStep ─────────────────────────────────


class TestSplitApplyConfigWithStep:
    """Test render() with sub-pipeline steps using mocked delegation."""

    @patch(
        f"{_MOD}._SUB_SHAPER_DISPATCH",
        {
            "Mean Calculator": (
                "mean",
                MagicMock(
                    return_value={
                        "meanAlgorithm": "arithmean",
                        "meanVars": ["ipc"],
                        "groupingColumns": ["config"],
                        "replacingColumn": "benchmark",
                    }
                ),
            ),
            "Normalize": ("normalize", MagicMock(return_value={})),
            "Sort": ("sort", MagicMock(return_value={})),
            "Filter": ("conditionSelector", MagicMock(return_value={})),
        },
    )
    @patch(f"{_MOD}._init_dispatch")
    @patch(f"{_MOD}.st")
    def test_one_mean_step_in_group_a(self, mock_st: MagicMock, _mock_init: MagicMock) -> None:
        """A group with 1 Mean step returns proper config via delegation."""
        from src.web.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()

        # multiselect: join cols, group A cols, group B cols
        mock_st.multiselect.side_effect = [
            ["benchmark", "config"],
            ["ipc"],
            ["cycles"],
        ]
        mock_st.slider.return_value = 2
        mock_st.expander.side_effect = [_ctx_mgr(), _ctx_mgr()]
        mock_st.columns.side_effect = [
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
        ]

        # selectbox for shaper type in group A step 0
        mock_st.selectbox.return_value = "Mean Calculator"

        # session_state: group A has 1 step, group B has 0
        mock_st.session_state = {
            "p_sa_g0_0_step_count": 1,
        }
        mock_st.button.return_value = False

        result = SplitApplyConfig.render(
            data=data,
            existing_config=cast(Any, {}),
            key_prefix="p_",
            shaper_id=0,
        )

        groups = result.get("groups", [])
        grp_a = groups[0]
        pipeline_a = grp_a.get("pipeline", [])
        assert len(pipeline_a) == 1
        step = pipeline_a[0]
        assert step.get("type") == "mean"
        assert step.get("meanAlgorithm") == "arithmean"


# ── TestSplitApplyConfigNGroups ──────────────────────────────────


class TestSplitApplyConfigNGroups:
    """Test N-group support (3 and 4 groups)."""

    @patch(f"{_MOD}._init_dispatch")
    @patch(f"{_MOD}.st")
    def test_three_groups_render(self, mock_st: MagicMock, _mock_init: MagicMock) -> None:
        """render() with 3 groups returns 3 group configs."""
        from src.web.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data_4cols()

        mock_st.multiselect.side_effect = [
            ["benchmark", "config"],
            ["v1"],
            ["v2"],
            ["v3"],
        ]
        mock_st.slider.return_value = 3
        mock_st.expander.side_effect = [_ctx_mgr(), _ctx_mgr(), _ctx_mgr()]
        mock_st.columns.side_effect = [
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
        ]
        mock_st.session_state = {}
        mock_st.button.return_value = False

        result = SplitApplyConfig.render(
            data=data,
            existing_config=cast(Any, {}),
            key_prefix="p_",
            shaper_id=0,
        )

        groups = result.get("groups", [])
        assert len(groups) == 3
        assert groups[0].get("columns") == ["v1"]
        assert groups[1].get("columns") == ["v2"]
        assert groups[2].get("columns") == ["v3"]

    @patch(f"{_MOD}._init_dispatch")
    @patch(f"{_MOD}.st")
    def test_four_groups_render(self, mock_st: MagicMock, _mock_init: MagicMock) -> None:
        """render() with 4 groups returns 4 group configs."""
        from src.web.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data_4cols()

        mock_st.multiselect.side_effect = [
            ["benchmark", "config"],
            ["v1"],
            ["v2"],
            ["v3"],
            ["v4"],
        ]
        mock_st.slider.return_value = 4
        mock_st.expander.side_effect = [
            _ctx_mgr(),
            _ctx_mgr(),
            _ctx_mgr(),
            _ctx_mgr(),
        ]
        mock_st.columns.side_effect = [
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
        ]
        mock_st.session_state = {}
        mock_st.button.return_value = False

        result = SplitApplyConfig.render(
            data=data,
            existing_config=cast(Any, {}),
            key_prefix="p_",
            shaper_id=0,
        )

        groups = result.get("groups", [])
        assert len(groups) == 4
        for i in range(4):
            assert groups[i].get("columns") == [f"v{i + 1}"]

    @patch(f"{_MOD}._init_dispatch")
    @patch(f"{_MOD}.st")
    def test_existing_config_restores_group_count(
        self, mock_st: MagicMock, _mock_init: MagicMock
    ) -> None:
        """Existing config with 3 groups defaults the slider to 3."""
        from src.web.components.shapers.split_apply_config import (
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data_4cols()

        existing: ShaperStepConfig = {  # type: ignore
            "joinColumns": ["benchmark", "config"],
            "groups": [
                {"columns": ["v1"], "pipeline": []},
                {"columns": ["v2"], "pipeline": []},
                {"columns": ["v3"], "pipeline": []},
            ],
        }

        mock_st.multiselect.side_effect = [
            ["benchmark", "config"],
            ["v1"],
            ["v2"],
            ["v3"],
        ]
        mock_st.slider.return_value = 3
        mock_st.expander.side_effect = [_ctx_mgr(), _ctx_mgr(), _ctx_mgr()]
        mock_st.columns.side_effect = [
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
        ]
        mock_st.session_state = {}
        mock_st.button.return_value = False

        result = SplitApplyConfig.render(
            data=data,
            existing_config=cast(Any, existing),
            key_prefix="p_",
            shaper_id=0,
        )

        assert len(result.get("groups", [])) == 3
        # Verify slider was called with value=3
        mock_st.slider.assert_called_once()
        call_kwargs = mock_st.slider.call_args
        assert call_kwargs[1].get("value") == 3 or call_kwargs[0][0] == "Number of groups"


# ── TestSplitApplyConfigExistingPipeline ─────────────────────────


class TestSplitApplyConfigExistingPipeline:
    """Test that existing pipeline config is passed to delegated renderers."""

    @patch(
        f"{_MOD}._SUB_SHAPER_DISPATCH",
        {
            "Mean Calculator": (
                "mean",
                MagicMock(
                    return_value={
                        "meanAlgorithm": "geomean",
                        "meanVars": ["ipc"],
                        "groupingColumns": ["config"],
                        "replacingColumn": "benchmark",
                    }
                ),
            ),
            "Normalize": ("normalize", MagicMock(return_value={})),
            "Sort": ("sort", MagicMock(return_value={})),
            "Filter": ("conditionSelector", MagicMock(return_value={})),
        },
    )
    @patch(f"{_MOD}._init_dispatch")
    @patch(f"{_MOD}.st")
    def test_existing_config_passed_to_delegate(
        self, mock_st: MagicMock, _mock_init: MagicMock
    ) -> None:
        """Existing step config is forwarded to the delegated renderer."""
        from src.web.components.shapers.split_apply_config import (
            _SUB_SHAPER_DISPATCH,
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()

        existing: ShaperStepConfig = {  # type: ignore
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

        mock_st.multiselect.side_effect = [
            ["benchmark", "config"],
            ["ipc"],
            ["cycles"],
        ]
        mock_st.slider.return_value = 2
        mock_st.expander.side_effect = [_ctx_mgr(), _ctx_mgr()]
        mock_st.columns.side_effect = [
            [_ctx_mgr(), _ctx_mgr()],
            [_ctx_mgr(), _ctx_mgr()],
        ]
        mock_st.selectbox.return_value = "Mean Calculator"
        mock_st.session_state = {}
        mock_st.button.return_value = False

        result = SplitApplyConfig.render(
            data=data,
            existing_config=cast(Any, existing),
            key_prefix="p_",
            shaper_id=0,
        )

        groups = result.get("groups", [])
        grp_a = groups[0]
        pipeline_a = grp_a.get("pipeline", [])
        assert len(pipeline_a) == 1
        assert pipeline_a[0].get("meanAlgorithm") == "geomean"

        # Verify the existing_step was passed to the delegated renderer
        _, render_fn = _SUB_SHAPER_DISPATCH["Mean Calculator"]
        call_args = render_fn.call_args  # type: ignore[attr-defined]
        passed_existing = call_args[0][1]  # 2nd positional arg
        assert passed_existing["type"] == "mean"
        assert passed_existing["meanAlgorithm"] == "geomean"


# ── TestSplitApplyConfigKeyPrefixing ─────────────────────────────


class TestSplitApplyConfigKeyPrefixing:
    """Test that delegated renderers receive properly prefixed keys."""

    @patch(
        f"{_MOD}._SUB_SHAPER_DISPATCH",
        {
            "Mean Calculator": ("mean", MagicMock(return_value={"meanAlgorithm": "arithmean"})),
            "Normalize": ("normalize", MagicMock(return_value={})),
            "Sort": ("sort", MagicMock(return_value={})),
            "Filter": ("conditionSelector", MagicMock(return_value={})),
        },
    )
    @patch(f"{_MOD}.st")
    def test_key_prefix_contains_group_and_step(self, mock_st: MagicMock) -> None:
        """Key prefix passed to delegate includes group/step info."""
        from src.web.components.shapers.split_apply_config import (
            _SUB_SHAPER_DISPATCH,
            SplitApplyConfig,
        )

        data: pd.DataFrame = _sample_data()
        mock_st.selectbox.return_value = "Mean Calculator"

        SplitApplyConfig._render_sub_step(
            data=data,
            columns=["ipc"],
            join_columns=["benchmark", "config"],
            categorical_cols=["benchmark", "config"],
            existing_step=cast(Any, {}),
            key_base="p_sa_g1_0_s0",
            step_index=0,
        )

        _, render_fn = _SUB_SHAPER_DISPATCH["Mean Calculator"]
        call_args = render_fn.call_args  # type: ignore[attr-defined]
        # key_prefix should be "p_sa_g1_0_s0_"
        assert call_args[0][2] == "p_sa_g1_0_s0_"
        # shaper_id should be "sub0"
        assert call_args[0][3] == "sub0"


# ── TestInitDispatch ─────────────────────────────────────────────


class TestInitDispatch:
    """Test the lazy dispatch initialization."""

    def test_init_dispatch_populates_dict(self) -> None:
        """_init_dispatch fills _SUB_SHAPER_DISPATCH with all 4 types."""
        import src.web.components.shapers.split_apply_config as mod

        # Reset state
        mod._SUB_SHAPER_DISPATCH.clear()
        mod._STATE["initialized"] = False

        mod._init_dispatch()

        assert mod._STATE["initialized"] is True
        assert "Mean Calculator" in mod._SUB_SHAPER_DISPATCH
        assert "Normalize" in mod._SUB_SHAPER_DISPATCH
        assert "Sort" in mod._SUB_SHAPER_DISPATCH
        assert "Filter" in mod._SUB_SHAPER_DISPATCH

        # Each entry is (type_str, callable)
        for _display_name, (type_str, render_fn) in mod._SUB_SHAPER_DISPATCH.items():
            assert isinstance(type_str, str)
            assert callable(render_fn)

    def test_init_dispatch_idempotent(self) -> None:
        """Calling _init_dispatch twice doesn't duplicate entries."""
        import src.web.components.shapers.split_apply_config as mod

        mod._SUB_SHAPER_DISPATCH.clear()
        mod._STATE["initialized"] = False

        mod._init_dispatch()
        first_count: int = len(mod._SUB_SHAPER_DISPATCH)

        mod._init_dispatch()
        assert len(mod._SUB_SHAPER_DISPATCH) == first_count
