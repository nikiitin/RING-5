#!/usr/bin/env python3
"""
Normalization Shaper
Implements data normalization relative to a baseline configuration.

Performance: Caches normalized results based on data fingerprint.
"""

import hashlib
import logging
from typing import Any, Dict, List

import pandas as pd

from src.core.performance import cached
from src.web.services.shapers.uni_df_shaper import UniDfShaper

logger = logging.getLogger(__name__)


class Normalize(UniDfShaper):
    """
    Shaper that normalizes numeric columns relative to a baseline configuration.

    This shaper groups data by specified columns and scales the selected variables
    by the value(s) found in a designated baseline row within each group.
    """

    def __init__(self, params: Dict[str, Any]) -> None:
        """
        Initialize the Normalize shaper with parameters.

        Args:
            params: Dictionary containing:
                - normalizeVars (List[str]): Columns to normalize.
                - normalizerVars (Optional[List[str]]): Columns to sum for the baseline value.
                - normalizerColumn (str): Column that identifies the baseline row.
                - normalizerValue (str): Value in normalizerColumn that indicates the baseline.
                - groupBy (List[str]): Columns used to define groups.
                - normalizeSd (Optional[bool]): Whether to normalize .sd columns. Defaults to True.
        """
        # Assign properties before super().__init__ as _verify_params needs them
        self._normalize_vars: List[str] = params.get("normalizeVars", [])
        self._normalizer_column: str = params.get("normalizerColumn", "")
        self._normalizer_value: Any = params.get("normalizerValue", "")
        self._group_by: List[str] = params.get("groupBy", [])
        self._normalizer_vars: List[str] = params.get("normalizerVars", self._normalize_vars)
        self._normalize_sd: bool = params.get("normalizeSd", True)

        # Store params for caching fingerprint
        self._params = params

        super().__init__(params)

        # Mandatory parameters with strict validation
        if (
            not self._normalize_vars
            or not self._normalizer_column
            or not self._normalizer_value
            or not self._group_by
        ):
            # _verify_params will catch missing keys for standard usage,
            # but we keep this for direct instantiations if any.
            pass

        # Type validation
        self._validate_init_types()

    def _verify_params(self) -> bool:
        """Verify that mandatory parameters exist in the params dict."""
        super()._verify_params()
        required = ["normalizeVars", "normalizerColumn", "normalizerValue", "groupBy"]
        for r in required:
            if r not in self.params:
                raise ValueError(f"Normalize: Missing required parameter '{r}'")
        return True

    def _validate_init_types(self) -> None:
        """Validate that initialization parameters have correct types."""
        if not isinstance(self._normalize_vars, list):
            raise TypeError("normalizeVars must be a list")
        if not isinstance(self._group_by, list):
            raise TypeError("groupBy must be a list")
        if not isinstance(self._normalizer_column, str):
            raise TypeError("normalizerColumn must be a string")
        if not isinstance(self._normalize_sd, bool):
            raise TypeError("normalizeSd must be a boolean")

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """
        Check that the dataframe contains all required columns and valid baseline values.

        Args:
            data_frame: The pandas DataFrame to check.

        Returns:
            True if all preconditions are met.

        Raises:
            ValueError: If columns are missing or normalization baseline is invalid.
        """
        super()._verify_preconditions(data_frame)

        # Verify columns exist and are numeric
        all_numeric_required = list(set(self._normalizer_vars + self._normalize_vars))
        for col in all_numeric_required:
            if col not in data_frame.columns:
                raise ValueError(f"Required numeric column '{col}' not found in dataframe.")
            if not pd.api.types.is_numeric_dtype(data_frame[col]):
                raise ValueError(f"Column '{col}' must be numeric for normalization.")

        if self._normalizer_column not in data_frame.columns:
            raise ValueError(f"Grouping column '{self._normalizer_column}' not found.")

        # Ensure baseline value exists
        if self._normalizer_value not in data_frame[self._normalizer_column].values:
            raise ValueError(
                f"Baseline value '{self._normalizer_value}' not found in column '{self._normalizer_column}'."
            )

        # Group validation
        groups = data_frame.groupby(self._group_by)
        if len(groups) == 0:
            raise ValueError("No groups found for the specified groupBy columns.")

        for name, group in groups:
            baseline_rows = group[group[self._normalizer_column] == self._normalizer_value]
            if len(baseline_rows) != 1:
                raise ValueError(
                    f"Ambiguous baseline: Group {name} has {len(baseline_rows)} baseline rows. "
                    "Each group must have exactly one row matching the normalizer value."
                )

        return True

    def _normalize_group(self, group: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize a single group of data.

        Args:
            group: A subdivision of the original dataframe.

        Returns:
            A new dataframe with normalized values.
        """
        result = group.copy()

        # Identify the baseline row for this group
        baseline = result[result[self._normalizer_column] == self._normalizer_value]

        if baseline.empty:
            return result

        # Calculate denominator (sum of specified normalizer variables)
        denominator = baseline[self._normalizer_vars].iloc[0].sum()

        if denominator == 0:
            # Prevent division by zero: zero out normalized columns
            for var in self._normalize_vars:
                result[var] = 0.0
                if self._normalize_sd:
                    sd_col = f"{var}.sd"
                    if sd_col in result.columns:
                        result[sd_col] = 0.0
            return result

        # Perform the actual scaling
        for var in self._normalize_vars:
            result[var] = result[var] / denominator
            if self._normalize_sd:
                sd_col = f"{var}.sd"
                if sd_col in result.columns:
                    result[sd_col] = result[sd_col] / denominator

        return result

    @staticmethod
    def _compute_data_fingerprint(data: pd.DataFrame, params: Dict[str, Any]) -> str:
        """
        Compute fingerprint for caching normalization results.

        Args:
            data: Input DataFrame
            params: Normalization parameters

        Returns:
            Hash string representing data+params combination
        """
        # Combine data shape, relevant columns, and params
        relevant_cols = (
            params.get("normalizeVars", [])
            + params.get("groupBy", [])
            + [params.get("normalizerColumn", "")]
        )

        fingerprint_parts = [
            f"shape:{data.shape}",
            f"cols:{sorted(relevant_cols)}",
            f"params:{sorted(params.items())}",
        ]

        # Add sample of actual data for change detection
        if len(data) > 0:
            sample_rows = data[relevant_cols].head(2).to_json() if relevant_cols else ""
            fingerprint_parts.append(f"sample:{sample_rows}")

        fingerprint = "|".join(fingerprint_parts)
        return hashlib.md5(fingerprint.encode(), usedforsecurity=False).hexdigest()[:16]

    @cached(ttl=300, maxsize=32)  # Cache for 5 minutes, max 32 normalized datasets
    def _cached_normalize(self, data_frame: pd.DataFrame, fingerprint: str) -> pd.DataFrame:
        """
        Cached normalization execution.

        Args:
            data_frame: Input data
            fingerprint: Data fingerprint for cache key

        Returns:
            Normalized DataFrame
        """
        import warnings

        with warnings.catch_warnings():
            # Suppress pandas warning about group keys
            warnings.filterwarnings(
                "ignore",
                category=FutureWarning,
                message=".*DataFrameGroupBy.apply operated on the grouping columns.*",
            )
            return data_frame.groupby(self._group_by, group_keys=False).apply(self._normalize_group)

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Execute the normalization pipeline with caching.

        Args:
            data_frame: Input data.

        Returns:
            New dataframe with normalized columns.
        """
        self._verify_preconditions(data_frame)

        # Compute fingerprint for caching
        fingerprint = self._compute_data_fingerprint(data_frame, self._params)

        # Use cached version
        return self._cached_normalize(data_frame, fingerprint)


if __name__ == "__main__":
    # Self-test block
    test_df = pd.DataFrame(
        {
            "config": ["baseline", "eval"],
            "bench": ["B1", "B1"],
            "cycles": [1000, 1500],
            "energy": [50, 60],
        }
    )

    normalizer = Normalize(
        {
            "normalizeVars": ["cycles", "energy"],
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["bench"],
        }
    )

    logger.debug("Pre-normalization:")
    logger.debug(test_df)
    logger.debug("\nPost-normalization:")
    logger.debug(normalizer(test_df))
