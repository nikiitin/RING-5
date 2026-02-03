"""
Shaper Configuration Orchestrator for RING-5.
Dispatches configuration requests to specialized shaper UI components.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

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

# Required parameters for each shaper type
# Note: conditionSelector has no universal required params since it supports multiple modes
# (values, range, threshold, value+mode, condition+value for legacy)
SHAPER_REQUIRED_PARAMS = {
    "normalize": ["normalizeVars", "normalizerColumn", "normalizerValue", "groupBy"],
    "mean": ["groupingColumns", "meanVars"],
    "columnSelector": ["columns"],
    "conditionSelector": ["column"],  # Only 'column' is always required
    "transformer": ["column"],  # Only 'column' is always required
}


def validate_shaper_config(
    shaper_type: str, config: Dict[str, Any]
) -> Tuple[bool, Optional[List[str]]]:
    """
    Validate if a shaper configuration has all required parameters filled.

    Args:
        shaper_type: Type of shaper to validate
        config: Configuration dictionary

    Returns:
        Tuple of (is_valid, list_of_missing_fields)
        - is_valid: True if all required params present and non-empty
        - list_of_missing_fields: List of missing/empty field names, None if valid
    """
    required_params = SHAPER_REQUIRED_PARAMS.get(shaper_type, [])
    missing_fields = []

    for param in required_params:
        value = config.get(param)
        # Check if param is missing or empty (empty list, empty string, None, etc.)
        if value is None or (isinstance(value, (list, str)) and len(value) == 0):
            missing_fields.append(param)

    if missing_fields:
        return False, missing_fields

    return True, None


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
            # UI component itself threw an error (not config validation)
            error_msg = f"Error rendering {shaper_type} configuration: {str(e)}"
            st.error(error_msg)
            logger.error(f"UI: Configuration UI failed for {shaper_type}: {e}", exc_info=True)
            return {"type": shaper_type}  # Return minimal config so UI doesn't break

    logger.warning(f"UI: Unknown shaper type encountered: {shaper_type}")
    return {"type": shaper_type}


def apply_shapers(data: pd.DataFrame, shapers_config: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Apply a sequence of shapers to the data.
    Delegates to ShaperFactory (Layer B interaction).

    Args:
        data: Input DataFrame
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
            error_msg = (
                f"❌ Pipeline step {idx + 1} ({shaper_type}): " f"Configuration error - {str(e)}"
            )
            st.error(error_msg)
            logger.error(f"PIPELINE: Config validation failed for {shaper_type}: {e}")
            raise ValueError(error_msg) from e
        except KeyError as e:
            # Missing column or data issue
            error_msg = (
                f"❌ Pipeline step {idx + 1} ({shaper_type}): "
                f"Data error - Missing required column or field: {str(e)}"
            )
            st.error(error_msg)
            logger.error(f"PIPELINE: Data validation failed for {shaper_type}: {e}")
            raise KeyError(error_msg) from e
        except Exception as e:
            # Unexpected error during transformation
            error_msg = (
                f"❌ Pipeline step {idx + 1} ({shaper_type}): " f"Transformation failed - {str(e)}"
            )
            st.error(error_msg)
            logger.error(f"PIPELINE: Transformation failed for {shaper_type}: {e}", exc_info=True)
            raise e  # Reraise to halt pipeline

    return result
