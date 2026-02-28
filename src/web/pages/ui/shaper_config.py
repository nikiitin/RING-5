"""
Shaper Configuration Orchestrator for RING-5.
Dispatches configuration requests to specialized shaper UI components.
"""

import logging
from typing import cast

import pandas as pd
import streamlit as st

from src.core.models.data_models import ShaperStepConfig
from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.validation import validate_shaper_config
from src.web.components.shapers.mean_config import MeanConfig
from src.web.components.shapers.normalize_config import NormalizeConfig
from src.web.components.shapers.pivot_config import PivotLongerConfig, PivotWiderConfig
from src.web.components.shapers.selector_transformer_configs import (
    ColumnSelectorConfig,
    ConditionSelectorConfig,
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


def configure_shaper(
    shaper_type: str,
    data: pd.DataFrame,
    shaper_id: int,
    existing_config: ShaperStepConfig | None,
    owner_id: int | None = None,
) -> ShaperStepConfig:
    """
    Orchestrate the configuration UI for a given shaper type.

    Adheres to Layer C principles: Strictly Presentation, delegates logic to factory.

    Args:
        shaper_type: Type of shaper to configure
        data: Current DataFrame for context
        shaper_id: Unique ID for this shaper instance
        existing_config: Existing configuration dict if any
        owner_id: Optional plot/owner ID for unique keys

    Returns:
        Configuration dictionary with 'type' key set
    """
    key_prefix = f"p{owner_id}_" if owner_id is not None else ""
    safe_config: ShaperStepConfig = cast(ShaperStepConfig, existing_config or {})

    config_dispatch = {
        "columnSelector": ColumnSelectorConfig.render,
        "normalize": NormalizeConfig.render,
        "mean": MeanConfig.render,
        "conditionSelector": ConditionSelectorConfig.render,
        "splitApply": SplitApplyConfig.render,
        "transformer": TransformerConfig.render,
        "sort": SortConfig.render,
        "pivotLonger": PivotLongerConfig.render,
        "pivotWider": PivotWiderConfig.render,
    }

    if shaper_type in config_dispatch:
        try:
            config: ShaperStepConfig = config_dispatch[shaper_type](
                data, safe_config, key_prefix, shaper_id
            )
            # Ensure 'type' is ALWAYS present even if component returned empty or partial
            config["type"] = shaper_type

            return config
        except Exception as e:
            # UI component itself threw an error (not config validation)
            st.exception(e)
            logger.error(f"UI: Configuration UI failed for {shaper_type}: {e}", exc_info=True)
            return cast(
                ShaperStepConfig, {"type": shaper_type}
            )  # Minimal config so UI doesn't break

    logger.warning(f"UI: Unknown shaper type encountered: {shaper_type}")
    return cast(ShaperStepConfig, {"type": shaper_type})


def apply_shapers(
    data: pd.DataFrame | None, shapers_config: list[ShaperStepConfig]
) -> pd.DataFrame:
    """
    Apply a sequence of shapers to the data.
    Delegates to ShaperFactory (Layer B interaction).

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

    result = data.copy()
    for idx, shaper_cfg in enumerate(shapers_config):
        shaper_type = shaper_cfg.get("type")
        if not shaper_type:
            logger.warning(f"Pipeline step {idx + 1}: Skipping shaper with no type specified")
            continue

        # Validate configuration before creating shaper
        is_valid, missing_fields = validate_shaper_config(shaper_type, shaper_cfg)
        if not is_valid:
            # Configuration incomplete - show user-friendly warning, don't raise exception
            fields_to_report = missing_fields or ["<unspecified>"]
            missing_str = ", ".join(f"'{f}'" for f in fields_to_report)
            warning_msg = (
                f"⚠️ Pipeline step {idx + 1} ({shaper_type}): "
                f"Configuration incomplete. Missing or empty fields: {missing_str}. "
                f"Please fill in all required fields."
            )
            st.warning(warning_msg)
            logger.debug(
                f"PIPELINE: Skipping incomplete shaper {shaper_type} "
                f"at step {idx + 1}, missing: {missing_fields}"
            )
            continue  # Skip this shaper, don't attempt to create/execute it

        try:
            shaper = ShaperFactory.create_shaper(shaper_type, shaper_cfg)
            result = shaper(result)
        except ValueError as e:
            # Configuration validation error from shaper itself
            error_msg = f"❌ Pipeline step {idx + 1} ({shaper_type}): " f"Configuration error - {e}"
            st.error(error_msg)
            logger.error(f"PIPELINE: Config validation failed for {shaper_type}: {e}")
            raise ValueError(error_msg) from e
        except KeyError as e:
            # Missing column or data issue
            error_msg = (
                f"❌ Pipeline step {idx + 1} ({shaper_type}): "
                f"Data error - Missing required column or field: {e}"
            )
            st.error(error_msg)
            logger.error(f"PIPELINE: Data validation failed for {shaper_type}: {e}")
            raise KeyError(error_msg) from e
        except Exception as e:
            # Unexpected error during transformation
            error_msg = (
                f"❌ Pipeline step {idx + 1} ({shaper_type}): " f"Transformation failed - {e}"
            )
            st.exception(e)
            logger.error(f"PIPELINE: Transformation failed for {shaper_type}: {e}", exc_info=True)
            raise e  # Reraise to halt pipeline

    return result
