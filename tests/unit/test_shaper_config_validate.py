"""Canonical facade execution reports failures without publishing partial results."""

from typing import cast
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.shapers.shapers_impl import DefaultShapersAPI


class TestApplyShapers:
    """Tests for the shapers facade pipeline contract."""

    def test_empty_pipeline(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = DefaultShapersAPI().process_pipeline(df, [])
        assert len(result) == 3
        assert list(result.columns) == ["a"]

    def test_none_data_raises(self) -> None:
        with pytest.raises(ValueError, match="pandas DataFrame"):
            DefaultShapersAPI().process_pipeline(None, [])

    def test_rejects_shaper_with_no_type(self) -> None:
        df = pd.DataFrame({"a": [1, 2]})
        with pytest.raises(ValueError, match="registered shaper type"):
            DefaultShapersAPI().process_pipeline(df, [cast(ShaperStepConfig, {"some": "config"})])

    def test_rejects_incomplete_config(self) -> None:
        """Incomplete configuration cannot execute an identity pipeline."""
        df = pd.DataFrame({"a": [1, 2]})
        config = [
            cast(ShaperStepConfig, {"type": "normalize", "normalizeVars": ["a"]})
        ]  # missing fields
        with pytest.raises(ValueError, match="Missing required parameter"):
            DefaultShapersAPI().process_pipeline(df, config)

    @patch("src.core.services.shapers.pipeline_service.ShaperFactory.create_shaper")
    def test_successful_shaper_execution(self, mock_factory: MagicMock) -> None:
        # Execution is delegated to the single canonical PipelineService engine.
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        transformed = pd.DataFrame({"a": [1, 2], "b": [4, 5]})

        mock_shaper = MagicMock(return_value=transformed)
        mock_factory.return_value = mock_shaper

        config = [cast(ShaperStepConfig, {"type": "columnSelector", "columns": ["a", "b"]})]
        result = DefaultShapersAPI().process_pipeline(df, config)

        assert len(result) == 2
        mock_factory.assert_called_once_with("columnSelector", config[0])

    @patch("src.core.services.shapers.pipeline_service.ShaperFactory.create_shaper")
    def test_shaper_error_halts_pipeline(self, mock_factory: MagicMock) -> None:
        # Execution errors reach the controller without publishing partial data.
        mock_factory.side_effect = ValueError("bad config")

        df = pd.DataFrame({"a": [1]})
        config = [cast(ShaperStepConfig, {"type": "columnSelector", "columns": ["a"]})]

        with pytest.raises(ValueError, match="Failed to apply shaper"):
            DefaultShapersAPI().process_pipeline(df, config)

    @patch("src.core.services.shapers.pipeline_service.ShaperFactory.create_shaper")
    def test_runtime_error_in_shaper_surfaces_as_valueerror(self, mock_factory: MagicMock) -> None:
        mock_shaper = MagicMock(side_effect=RuntimeError("unexpected"))
        mock_factory.return_value = mock_shaper

        df = pd.DataFrame({"a": [1]})
        config = [cast(ShaperStepConfig, {"type": "columnSelector", "columns": ["a"]})]

        with pytest.raises(ValueError, match="Failed to apply shaper"):
            DefaultShapersAPI().process_pipeline(df, config)

    def test_does_not_mutate_original_data(self) -> None:
        """A shaper pipeline must not mutate the caller's DataFrame."""
        # [test->req~ring5.shaping.independent-pipelines~1]
        # [test->req~ring5.quality.immutable-data~1]
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        config = [cast(ShaperStepConfig, {"type": "columnSelector", "columns": ["a"]})]
        DefaultShapersAPI().process_pipeline(df, config)
        # The original frame is untouched (the shaper copies internally).
        assert list(df.columns) == ["a", "b"]
        assert len(df) == 3
