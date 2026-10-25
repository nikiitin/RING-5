"""Dispatch shaper configuration to its Streamlit component."""

from collections.abc import Callable, Mapping
import logging
from typing import cast

import pandas as pd
import streamlit as st

from src.core.models.shaper_models import ShaperStepConfig
from src.web.components.shapers.derive_column_config import DeriveColumnConfig
from src.web.components.shapers.mean_config import MeanConfig
from src.web.components.shapers.normalize_config import NormalizeConfig
from src.web.components.shapers.pivot_config import PivotLongerConfig, PivotWiderConfig
from src.web.components.shapers.selector_transformer_configs import (
    ColumnSelectorConfig,
    ConditionSelectorConfig,
    GroupCardinalitySelectorConfig,
    GroupPredicateSelectorConfig,
    ItemSelectorConfig,
    TransformerConfig,
)
from src.web.components.shapers.sort_config import SortConfig
from src.web.components.shapers.split_apply_config import SplitApplyConfig

logger = logging.getLogger(__name__)

# Shaper type → UI config renderer. Every registered, user-selectable shaper
# must have an entry here (enforced by test_shaper_ui_completeness) so a shaper
# can never appear in the dropdown without a way to configure it.
CONFIG_DISPATCH: dict[str, Callable[..., ShaperStepConfig]] = {
    "columnSelector": ColumnSelectorConfig.render,
    "normalize": NormalizeConfig.render,
    "mean": MeanConfig.render,
    "conditionSelector": ConditionSelectorConfig.render,
    "itemSelector": ItemSelectorConfig.render,
    "splitApply": SplitApplyConfig.render,
    "transformer": TransformerConfig.render,
    "sort": SortConfig.render,
    "pivotLonger": PivotLongerConfig.render,
    "pivotWider": PivotWiderConfig.render,
    "deriveColumn": DeriveColumnConfig.render,
    "groupCardinalitySelector": GroupCardinalitySelectorConfig.render,
    "groupPredicateSelector": GroupPredicateSelectorConfig.render,
}


def configure_shaper(
    shaper_type: str,
    data: pd.DataFrame,
    shaper_id: int,
    existing_config: Mapping[str, object] | None,
    owner_id: int | None = None,
    *,
    display_names: dict[str, str],
) -> Mapping[str, object]:
    """Render the configuration UI for a shaper type.

    Args:
        shaper_type: Type of shaper to configure.
        data: Current dataframe used to populate controls.
        shaper_id: Unique ID for this shaper instance.
        existing_config: Existing configuration, if any.
        owner_id: Optional plot or owner ID used to namespace widget keys.
        display_names: Current facade-provided editor labels and identifiers.

    Returns:
        Configuration dictionary with its ``type`` key set.
    """
    key_prefix = f"p{owner_id}_" if owner_id is not None else ""
    if shaper_type in CONFIG_DISPATCH:
        safe_config = cast(ShaperStepConfig, existing_config or {})
        try:
            config: ShaperStepConfig
            if shaper_type == "splitApply":
                config = SplitApplyConfig.render(
                    data, safe_config, key_prefix, shaper_id, display_names=display_names
                )
            else:
                config = CONFIG_DISPATCH[shaper_type](data, safe_config, key_prefix, shaper_id)
            # Every persisted shaper configuration requires its type discriminator.
            return cast(ShaperStepConfig, {**config, "type": shaper_type})
        except Exception as e:
            st.exception(e)
            logger.error(f"UI: Configuration UI failed for {shaper_type}: {e}", exc_info=True)
            return cast(ShaperStepConfig, {**safe_config, "type": shaper_type})

    st.info("This transformation has no configuration editor. Its configuration is preserved.")
    return {**(existing_config or {}), "type": shaper_type}
