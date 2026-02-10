"""
Shaper Configuration Orchestrator for RING-5.
Dispatches configuration requests to specialized shaper UI components.
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.web.services.shapers.factory import ShaperFactory
from src.web.ui.components.shapers.mean_config import MeanConfig
from src.web.ui.components.shapers.normalize_config import NormalizeConfig
from src.web.ui.components.shapers.selector_transformer_configs import (
    ColumnSelectorConfig,
    ConditionSelectorConfig,
    TransformerConfig,
)

logger = logging.getLogger(__name__)

# Constants mapping Human readable names to factory keys
SHAPER_TYPE_MAP = {
    "Column Selector": "columnSelector",
    "Normalize": "normalize",
    "Mean Calculator": "mean",
    "Filter": "conditionSelector",
    "Transformer": "transformer",
    # Reverse mapping for compatibility
    "columnSelector": "Column Selector",
    "normalize": "Normalize",
    "mean": "Mean Calculator",
    "conditionSelector": "Filter",
    "transformer": "Transformer",
}


def configure_shaper(
    shaper_type: str,
    data: pd.DataFrame,
    shaper_id: str,
    existing_config: Optional[Dict[str, Any]],
    owner_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Orchestrate the configuration UI for a given shaper type.

    Adheres to Layer C principles: Strictly Presentation, delegates logic to factory.
    """
    key_prefix = f"p{owner_id}_" if owner_id is not None else ""
    existing_config = existing_config or {}

    config_dispatch = {
        "columnSelector": ColumnSelectorConfig.render,
        "normalize": NormalizeConfig.render,
        "mean": MeanConfig.render,
        "conditionSelector": ConditionSelectorConfig.render,
        "transformer": TransformerConfig.render,
    }

    if shaper_type in config_dispatch:
        try:
            config = config_dispatch[shaper_type](data, existing_config, key_prefix, shaper_id)
            # Ensure 'type' is ALWAYS present even if component returned empty or partial
            if isinstance(config, dict):
                config["type"] = shaper_type
            return config
        except Exception as e:
            st.error(f"UI Error configuring {shaper_type}: {e}")
            logger.error(f"UI: Configuration failed for {shaper_type}: {e}", exc_info=True)
            return {}

    logger.warning(f"UI: Unknown shaper type encountered: {shaper_type}")
    return {}


def apply_shapers(data: pd.DataFrame, shapers_config: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Apply a sequence of shapers to the data.
    Delegates to ShaperFactory (Layer B interaction).
    """
    if data is None:
        raise ValueError("Shaper Orchestrator: Cannot apply shapers to None data.")

    result = data.copy()
    for shaper_cfg in shapers_config:
        try:
            shaper_type = shaper_cfg.get("type")
            if not shaper_type:
                continue

            shaper = ShaperFactory.create_shaper(shaper_type, shaper_cfg)
            result = shaper(result)
        except Exception as e:
            # Fail Fast, Fail Loud (Rule #5)
            error_msg = (
                f"TRANSFORMATION FAILED: {shaper_cfg.get('type')} Shaper execution error: {e}"
            )
            st.error(error_msg)
            logger.error(f"DOMAIN: {error_msg}", exc_info=True)
            raise e  # Reraise to halt pipeline if necessary

    return result
