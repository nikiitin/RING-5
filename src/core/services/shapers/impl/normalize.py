"""Shaper for baseline-relative normalization within groups."""

import logging
import warnings
from typing import Any, cast, override

import pandas as pd
from pandas import DataFrame

from src.core.models.shaper_models import NormalizeShaperConfig
from src.core.performance import cached, compute_data_fingerprint
from src.core.services.shapers.uni_df_shaper import UniDfShaper

logger = logging.getLogger(__name__)


class Normalize(UniDfShaper):
    """
    Shaper that normalizes numeric columns relative to a baseline configuration.

    This shaper groups data by specified columns and scales the selected variables
    by the value(s) found in a designated baseline row within each group.
    """

    def __init__(self, params: dict[str, Any]) -> None:
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
        # Use cast for type-safe access
        config = cast(NormalizeShaperConfig, params)

        # Assign properties before super().__init__ as _verify_params needs them
        self._normalize_vars: list[str] = config.get("normalizeVars", [])
        self._normalizer_column: str = config.get("normalizerColumn", "")
        self._normalizer_value: str = config.get("normalizerValue", "")
        self._group_by: list[str] = config.get("groupBy", [])
        self._normalizer_vars: list[str] = config.get("normalizerVars", self._normalize_vars)
        self._normalize_sd: bool = config.get("normalizeSd", True)

        # Store params for caching fingerprint
        self._params = params

        super().__init__(params)

        # Type validation
        self._validate_init_types()

    @override
    def _verify_params(self) -> bool:
        """Verify that mandatory parameters exist in the params dict."""
        super()._verify_params()
        config = cast(NormalizeShaperConfig, self.params)
        required = ["normalizeVars", "normalizerColumn", "normalizerValue", "groupBy"]
        for r in required:
            if r not in config:
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

    @override
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
        if self._normalizer_value not in data_frame[self._normalizer_column].unique():
            raise ValueError(
                f"Baseline value '{self._normalizer_value}' not found "
                f"in column '{self._normalizer_column}'."
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
        # [impl->req~ring5.shaping.normalize~1]
        result = group.copy()

        # Identify the baseline row for this group
        baseline = result[result[self._normalizer_column] == self._normalizer_value]

        if baseline.empty:
            return result

        # Calculate denominator (sum of specified normalizer variables)
        baseline_vars = baseline[self._normalizer_vars]
        denominator = baseline_vars.iloc[0].sum()

        if pd.isna(denominator) or denominator == 0:
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

    @cached(ttl=300, maxsize=32, key_func=lambda self, df, fp: fp)
    def _normalize_with_cache(self, data_frame: pd.DataFrame, fingerprint: str) -> pd.DataFrame:
        """
        Execute normalization with fingerprint-based caching.

        The @cached decorator uses the fingerprint parameter as the cache key,
        avoiding inefficient DataFrame stringification.

        Args:
            data_frame: Input data
            fingerprint: Data fingerprint for cache key (used by decorator)

        Returns:
            Normalized DataFrame
        """

        # [impl->req~ring5.quality.bounded-caching~1]

        with warnings.catch_warnings():
            # Suppress pandas warning about group keys
            warnings.filterwarnings(
                "ignore",
                category=FutureWarning,
                message=".*DataFrameGroupBy.apply operated on the grouping columns.*",
            )
            # pandas >=2.x compat: groupby().apply() may drop grouping columns
            # (FutureWarning in 2.x, default in 3.0). Preserve them manually.
            grouped = data_frame.groupby(self._group_by, group_keys=False)
            result: pd.DataFrame = grouped.apply(self._normalize_group)

            # pandas >=2.x compat: grouping columns may be dropped, re-add them
            if not all(col in result.columns for col in self._group_by):
                # Merge with original group columns
                for col in self._group_by:
                    if col not in result.columns:
                        result[col] = data_frame[col].copy()

            # Preserve the original column order. Re-adding grouping columns
            # above appends them at the end; pandas 3.0's groupby().apply() drops
            # them by default, so without this the input order is lost (e.g. the
            # groupBy column jumps to the end). New columns (e.g. .sd) keep their
            # trailing position.
            ordered = [c for c in data_frame.columns if c in result.columns]
            extra = [c for c in result.columns if c not in ordered]
            result = result[ordered + extra]

        return result

    @override
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Execute the normalization pipeline with caching.

        Args:
            data_frame: Input data.

        Returns:
            New dataframe with normalized columns.
        """
        self._verify_preconditions(data_frame)

        # Compute fingerprint for caching (only hash metadata, not entire DataFrame).
        # Include ``normalizer_vars`` because it supplies the denominator (see
        # ``_normalize_group``) and can differ from ``normalize_vars``; omitting it lets a
        # different baseline value return a stale (wrong) normalized frame within the TTL.
        relevant_cols = (
            self._normalize_vars
            + self._normalizer_vars
            + self._group_by
            + [self._normalizer_column]
        )
        fingerprint = compute_data_fingerprint(data_frame, self._params, relevant_cols)

        # Use cache with fingerprint as key (NOT the DataFrame itself).
        # Shallow copy (CoW) so callers can never mutate the cache-resident
        # frame in place and poison later hits.
        result: DataFrame = self._normalize_with_cache(data_frame, fingerprint)
        return result.copy(deep=False)


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
