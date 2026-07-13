"""Dispatch shaper configuration to its Streamlit component."""

import logging
from typing import cast

import pandas as pd
import streamlit as st

from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.pipeline_service import PipelineService
from src.core.services.shapers.validation import validate_shaper_config
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

# Display name mapping — delegates to the single source of truth
# in ``ShaperFactory``. This module only provides the reverse
# (type → display) for compatibility.
SHAPER_TYPE_MAP: dict[str, str] = {
    **ShaperFactory.get_display_name_map(),
    **{v: k for k, v in ShaperFactory.get_display_name_map().items()},
}

# Shaper type → UI config renderer. Every registered, user-selectable shaper
# must have an entry here (enforced by test_shaper_ui_completeness) so a shaper
# can never appear in the dropdown without a way to configure it.
CONFIG_DISPATCH = {
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
    existing_config: ShaperStepConfig | None,
    owner_id: int | None = None,
) -> ShaperStepConfig:
    """Render the configuration UI for a shaper type.

    Args:
        shaper_type: Type of shaper to configure.
        data: Current dataframe used to populate controls.
        shaper_id: Unique ID for this shaper instance.
        existing_config: Existing configuration, if any.
        owner_id: Optional plot or owner ID used to namespace widget keys.

    Returns:
        Configuration dictionary with its ``type`` key set.
    """
    key_prefix = f"p{owner_id}_" if owner_id is not None else ""
    safe_config: ShaperStepConfig = cast(ShaperStepConfig, existing_config or {})

    if shaper_type in CONFIG_DISPATCH:
        try:
            config: ShaperStepConfig = CONFIG_DISPATCH[shaper_type](
                data, safe_config, key_prefix, shaper_id
            )
            # Every persisted shaper configuration requires its type discriminator.
            config["type"] = shaper_type

            return config
        except Exception as e:
            st.exception(e)
            logger.error(f"UI: Configuration UI failed for {shaper_type}: {e}", exc_info=True)
            return cast(ShaperStepConfig, {"type": shaper_type})

    logger.warning(f"UI: Unknown shaper type encountered: {shaper_type}")
    return cast(ShaperStepConfig, {"type": shaper_type})


def apply_shapers(
    data: pd.DataFrame | None, shapers_config: list[ShaperStepConfig]
) -> pd.DataFrame:
    """
    Apply a sequence of shapers to the data.

    The UI concern — skipping incomplete steps with a user-facing warning — is
    handled here; execution itself is delegated to the single canonical engine
    ``PipelineService.process_pipeline`` so there is exactly one execution loop.

    Args:
        data: Input DataFrame (or None)
        shapers_config: List of shaper configurations

    Returns:
        Transformed DataFrame

    Raises:
        ValueError: If data is None or shaper execution fails
    """
    if data is None:
        raise ValueError("Shaper Orchestrator: Cannot apply shapers to None data.")

    # UI concern: validate and drop incomplete steps with a user-facing warning.
    valid_steps: list[ShaperStepConfig] = []
    for idx, shaper_cfg in enumerate(shapers_config):
        shaper_type = shaper_cfg.get("type")
        if not shaper_type:
            logger.warning(f"Pipeline step {idx + 1}: Skipping shaper with no type specified")
            continue

        is_valid, missing_fields = validate_shaper_config(shaper_type, shaper_cfg)
        if not is_valid:
            fields_to_report = missing_fields or ["<unspecified>"]
            missing_str = ", ".join(f"'{f}'" for f in fields_to_report)
            st.warning(
                f"⚠️ Pipeline step {idx + 1} ({shaper_type}): "
                f"Configuration incomplete. Missing or empty fields: {missing_str}. "
                f"Please fill in all required fields."
            )
            logger.debug(
                f"PIPELINE: Skipping incomplete shaper {shaper_type} "
                f"at step {idx + 1}, missing: {missing_fields}"
            )
            continue

        valid_steps.append(shaper_cfg)

    # Execution: the single canonical pipeline engine.
    try:
        return PipelineService.process_pipeline(data, valid_steps)
    except ValueError as e:
        st.error(f"❌ Pipeline execution failed: {e}")
        logger.error(f"PIPELINE: {e}", exc_info=True)
        raise
