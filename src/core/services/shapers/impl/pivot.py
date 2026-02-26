"""
Pivot Shapers — Transform data between wide and long formats.

Provides capabilities for:
1. Pivot Longer (Melt): Unpivot a DataFrame from wide to long format.
2. Pivot Wider: Pivot a DataFrame from long to wide format.
"""

from typing import cast

import pandas as pd

from src.core.models.shaper_models import (
    PivotLongerShaperConfig,
    PivotWiderShaperConfig,
)
from src.core.services.shapers.shaper import Shaper


class PivotLonger(Shaper):
    """
    Pivot Longer (Melt) Data Shaper.

    Transforms data from a wide format to a long format by unpivoting
    selected columns. Optionally uses a regular expression to extract
    a variable part from the column names.
    """

    def __init__(self, params: dict[str, str | list[str]]) -> None:
        """Initialize with PivotLongerShaperConfig."""
        super().__init__(params)
        self.config = cast(PivotLongerShaperConfig, self.params)

    def _verify_params(self) -> bool:
        """Verify required parameters are present."""
        super()._verify_params()
        if "id_vars" not in self.config or not self.config["id_vars"]:
            raise ValueError("PivotLonger requires 'id_vars'.")
        if "value_vars" not in self.config or not self.config["value_vars"]:
            raise ValueError("PivotLonger requires 'value_vars'.")
        if "var_name" not in self.config:
            raise ValueError("PivotLonger requires 'var_name'.")
        if "value_name" not in self.config:
            raise ValueError("PivotLonger requires 'value_name'.")
        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Execute the pivot_longer operation on the data."""
        super().__call__(data_frame)
        result = data_frame.copy()

        # Validate columns
        missing_id_vars = [col for col in self.config["id_vars"] if col not in result.columns]
        missing_val_vars = [col for col in self.config["value_vars"] if col not in result.columns]

        if missing_id_vars:
            raise KeyError(f"id_vars not found in dataframe: {missing_id_vars}")
        if missing_val_vars:
            raise KeyError(f"value_vars not found in dataframe: {missing_val_vars}")

        # Perform melt
        result = pd.melt(
            result,
            id_vars=self.config["id_vars"],
            value_vars=self.config["value_vars"],
            var_name=self.config["var_name"],
            value_name=self.config["value_name"],
        )

        # Apply extraction pattern if provided
        pattern = self.config.get("extract_pattern")
        if pattern:
            try:
                # Use pandas str.extract which expects a capture group
                extracted = result[self.config["var_name"]].str.extract(pattern, expand=False)
                # If extraction fails (NaNs), fallback to original string or fillna
                result[self.config["var_name"]] = extracted.fillna(result[self.config["var_name"]])
            except Exception as e:
                raise ValueError(f"Failed to apply extraction pattern '{pattern}': {e}") from e

        return result


class PivotWider(Shaper):
    """
    Pivot Wider Data Shaper.

    Transforms data from a long format to a wide format using pivot().
    """

    def __init__(self, params: dict[str, str | list[str]]) -> None:
        """Initialize with PivotWiderShaperConfig."""
        super().__init__(params)
        self.config = cast(PivotWiderShaperConfig, self.params)

    def _verify_params(self) -> bool:
        """Verify required parameters are present."""
        super()._verify_params()
        if "index" not in self.config or not self.config["index"]:
            raise ValueError("PivotWider requires 'index' columns.")
        if "columns" not in self.config or not self.config["columns"]:
            raise ValueError("PivotWider requires a 'columns' target.")
        if "values" not in self.config or not self.config["values"]:
            raise ValueError("PivotWider requires a 'values' target.")
        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Execute the pivot_wider operation on the data."""
        super().__call__(data_frame)
        result = data_frame.copy()

        index_cols = self.config["index"]
        columns_col = self.config["columns"]
        values_col = self.config["values"]

        missing_idx = [col for col in index_cols if col not in result.columns]
        if missing_idx:
            raise KeyError(f"index columns not found in dataframe: {missing_idx}")
        if columns_col not in result.columns:
            raise KeyError(f"columns target not found in dataframe: '{columns_col}'")
        if values_col not in result.columns:
            raise KeyError(f"values target not found in dataframe: '{values_col}'")

        # Perform pivot
        try:
            result = result.pivot(
                index=index_cols,
                columns=columns_col,
                values=values_col,
            )
            # Reset index to flatten the resulting DataFrame
            result = result.reset_index()
            # If the columns have a name (from columns_col), remove it for cleaner output
            result.columns.name = None
        except Exception as e:
            raise ValueError(f"Failed to pivot wider: {e}") from e

        return result
