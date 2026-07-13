"""UI configuration tests for scripting and grouping shapers."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from src.core.services.shapers.factory import ShaperFactory


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bench": ["a", "a", "b", "b"],
            "policy": ["base", "x", "base", "x"],
            "p": [2.0, 4.0, 0.0, 1.0],
            "q": [1.0, 2.0, 3.0, 1.0],
        }
    )


def test_derive_column_config_sum_round_trips():
    with patch("src.web.components.shapers.derive_column_config.st") as st:
        st.selectbox.return_value = "sum"
        st.text_input.return_value = "s"
        st.multiselect.return_value = ["p", "q"]
        from src.web.components.shapers.derive_column_config import DeriveColumnConfig

        cfg = DeriveColumnConfig.render(_df(), {}, "", 1)
    assert cfg == {"op": "sum", "dest": "s", "sources": ["p", "q"]}
    out = ShaperFactory.create_shaper("deriveColumn", {"type": "deriveColumn", **cfg})(_df())
    assert out["s"].tolist() == [3.0, 6.0, 3.0, 2.0]


def test_group_cardinality_config_round_trips():
    with patch("src.web.components.shapers.selector_transformer_configs.st") as st:
        st.columns.return_value = [st, st]
        st.multiselect.return_value = ["bench"]
        st.selectbox.side_effect = ["policy", "eq"]  # countColumn, then mode (c2)
        st.number_input.return_value = 2  # count (c1)
        from src.web.components.shapers.selector_transformer_configs import (
            GroupCardinalitySelectorConfig,
        )

        cfg = GroupCardinalitySelectorConfig.render(_df(), {}, "", 1)
    assert cfg == {"groupBy": ["bench"], "countColumn": "policy", "count": 2, "mode": "eq"}
    out = ShaperFactory.create_shaper(
        "groupCardinalitySelector", {"type": "groupCardinalitySelector", **cfg}
    )(_df())
    assert set(out["bench"]) == {"a", "b"}  # both groups have 2 distinct policies


def test_group_predicate_config_round_trips():
    with patch("src.web.components.shapers.selector_transformer_configs.st") as st:
        st.columns.return_value = [st, st]
        st.multiselect.return_value = ["bench"]
        # selectbox order: baselineColumn, baselineValue, predicateColumn, drop_when, action
        st.selectbox.side_effect = ["policy", "base", "p", "zero_or_nan", "drop"]
        from src.web.components.shapers.selector_transformer_configs import (
            GroupPredicateSelectorConfig,
        )

        cfg = GroupPredicateSelectorConfig.render(_df(), {}, "", 1)
    assert cfg == {
        "groupBy": ["bench"],
        "baselineColumn": "policy",
        "baselineValue": "base",
        "predicateColumn": "p",
        "drop_when": "zero_or_nan",
        "action": "drop",
    }
    out = ShaperFactory.create_shaper(
        "groupPredicateSelector", {"type": "groupPredicateSelector", **cfg}
    )(_df())
    assert set(out["bench"]) == {"a"}  # group "b" has base p == 0 → dropped
