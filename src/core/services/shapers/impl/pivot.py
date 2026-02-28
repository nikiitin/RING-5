"""
Pivot Shapers — Transform data between wide and long formats.

Provides capabilities for:
1. Pivot Longer (Melt): Unpivot a DataFrame from wide to long format.
2. Pivot Wider: Pivot a DataFrame from long to wide format.
"""

import logging
import re
from typing import Any, cast

import pandas as pd

from src.core.models.shaper_models import (
    PivotLongerShaperConfig,
    PivotWiderShaperConfig,
)
from src.core.services.shapers.shaper import Shaper

logger = logging.getLogger(__name__)


def extract_with_pattern(
    value: str, pattern: str, group_indices: list[int], separator: str = "_"
) -> str:
    """
    Extract specific capture groups from a string using a regex pattern.

    Args:
        value: The string to extract from.
        pattern: Regex pattern with capture groups.
        group_indices: List of group indices to keep and join.
        separator: Separator to use when joining multiple groups.

    Returns:
        Joined capture groups or the original value if no match.
    """
    try:
        match = re.search(pattern, value)
        if not match:
            return value

        parts = []
        for idx in group_indices:
            try:
                parts.append(str(match.group(idx)))
            except IndexError:
                continue

        return separator.join(parts) if parts else value
    except (re.error, TypeError, IndexError) as exc:
        logger.warning("extract_with_pattern failed for %r: %s", value, exc)
        return value


class PivotLonger(Shaper):
    """
    Pivot Longer (Melt) Data Shaper.

    Transforms data from a wide format to a long format by unpivoting
    selected columns. Optionally uses a regular expression to extract
    a variable part from the column names.
    """

    def __init__(self, params: dict[str, str | list[str]]) -> None:
        """Initialize with PivotLongerShaperConfig."""
        self.config = cast(PivotLongerShaperConfig, params)
        super().__init__(params)

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

        # Apply extraction pattern and filtering if provided
        pattern = self.config.get("extract_pattern")
        if pattern:
            try:
                var_name = self.config["var_name"]
                pattern = str(self.config.get("extract_pattern", ""))
                group_indices = list(self.config.get("extract_group_indices", [1]))
                separator = str(self.config.get("extract_separator", "_"))

                # Selective unpivoting logic
                filters = self.config.get("selection_filters", {})
                strategy = self.config.get("selection_strategy", "discard")
                merge_label = self.config.get("merge_label", "other")

                if filters:
                    compiled = re.compile(pattern)
                    # Convert filter keys to integers once
                    int_filters = {int(k): v for k, v in filters.items()}

                    def process_row(val: Any) -> str | None:
                        orig_str = str(val)
                        match = compiled.search(orig_str)
                        if not match:
                            return None

                        # Check if matches filters
                        for group_idx, allowed_vals in int_filters.items():
                            try:
                                if str(match.group(group_idx)) not in allowed_vals:
                                    if strategy == "discard":
                                        return None
                                    return merge_label
                            except IndexError:
                                if strategy == "discard":
                                    return None
                                return merge_label

                        # Extract using already found match groups if possible,
                        # or fall back to extract_with_pattern
                        parts = []
                        for idx in group_indices:
                            try:
                                parts.append(str(match.group(idx)))
                            except IndexError:
                                continue
                        return separator.join(parts) if parts else orig_str

                    # Apply filter/merge logic in a single pass where possible
                    result[var_name] = result[var_name].apply(process_row)

                    # Drop rows that returned None (discard strategy)
                    result = result.dropna(subset=[var_name])

                    # If merge strategy, we might have multiple rows with the same merge_label
                    if strategy == "merge":
                        # We need to aggregate the value column for the merged rows
                        id_vars = self.config["id_vars"]
                        val_name = self.config["value_name"]

                        # Group by everything EXCEPT the value column and sum
                        result = result.groupby(id_vars + [var_name], as_index=False).agg(
                            {val_name: "sum"}
                        )
                else:
                    # Vectorized extraction: regex matching in C via pandas
                    original_values = result[var_name].astype(str)
                    extracted_df = original_values.str.extract(pattern, expand=True)
                    n_groups = len(extracted_df.columns)
                    # group_indices are 1-based (re convention); DataFrame cols are 0-based
                    col_indices = [idx - 1 for idx in group_indices if 0 < idx <= n_groups]
                    if col_indices:
                        if len(col_indices) == 1:
                            joined = extracted_df.iloc[:, col_indices[0]]
                        else:
                            selected = extracted_df.iloc[:, col_indices]
                            joined = selected.apply(
                                lambda row: separator.join(s for s in row if pd.notna(s)),
                                axis=1,
                            )
                        # Keep original value where regex didn't match
                        no_match = extracted_df.isna().all(axis=1)
                        result[var_name] = joined.where(~no_match, original_values)
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
        self.config = cast(PivotWiderShaperConfig, params)
        super().__init__(params)

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
        # No copy needed: pivot_table() creates a new DataFrame.
        result = data_frame

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

        # Perform pivot using pivot_table with aggfunc to handle duplicate
        # (index, columns) combinations gracefully instead of raising ValueError.
        try:
            result = result.pivot_table(
                index=index_cols,
                columns=columns_col,
                values=values_col,
                aggfunc="first",
            )
            # Reset index to flatten the resulting DataFrame
            result = result.reset_index()
            # If the columns have a name (from columns_col), remove it for cleaner output
            result.columns.name = None
        except Exception as e:
            raise ValueError(f"Failed to pivot wider: {e}") from e

        return result
