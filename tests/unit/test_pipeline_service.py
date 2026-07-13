"""Tests for PipelineService — the canonical shaper-pipeline execution engine."""

from typing import cast

import pandas as pd
import pytest

from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.shapers.pipeline_service import PipelineService


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "benchmark": ["bzip2", "gcc", "mcf"],
            "ipc": [1.5, 2.3, 3.1],
        }
    )


class TestProcessPipeline:
    """Tests for PipelineService.process_pipeline."""

    def test_empty_pipeline_returns_input(self, sample_df: pd.DataFrame) -> None:
        result = PipelineService.process_pipeline(sample_df, [])
        assert result.equals(sample_df)

    def test_valid_step_applies(self, sample_df: pd.DataFrame) -> None:
        pipeline = cast(
            list[ShaperStepConfig],
            [{"type": "columnSelector", "columns": ["benchmark"]}],
        )
        result = PipelineService.process_pipeline(sample_df, pipeline)
        assert list(result.columns) == ["benchmark"]

    @pytest.mark.parametrize(
        "bad_step",
        [
            {"Type": "columnSelector"},  # key typo
            {"type": ""},  # empty type
            {"type": None},  # explicit None
            {"params": {}},  # no type at all
        ],
    )
    def test_step_without_type_raises(
        self, sample_df: pd.DataFrame, bad_step: dict[str, object]
    ) -> None:
        """A malformed step must raise — silently skipping it would return
        un-transformed data while the caller believes the pipeline ran."""
        pipeline = cast(list[ShaperStepConfig], [bad_step])
        with pytest.raises(ValueError, match="has no 'type'"):
            PipelineService.process_pipeline(sample_df, pipeline)

    def test_step_without_type_reports_index(self, sample_df: pd.DataFrame) -> None:
        pipeline = cast(
            list[ShaperStepConfig],
            [
                {"type": "columnSelector", "columns": ["benchmark", "ipc"]},
                {"columns": []},
            ],
        )
        with pytest.raises(ValueError, match="step 1"):
            PipelineService.process_pipeline(sample_df, pipeline)

    def test_unknown_shaper_type_raises(self, sample_df: pd.DataFrame) -> None:
        pipeline = cast(list[ShaperStepConfig], [{"type": "nonexistentShaper"}])
        with pytest.raises(ValueError):
            PipelineService.process_pipeline(sample_df, pipeline)


class TestPipelineStepError:
    """Failures carry structured location data — no message parsing needed."""

    def test_missing_type_carries_index(self, sample_df: pd.DataFrame) -> None:
        from src.core.services.shapers.pipeline_service import PipelineStepError

        pipeline = cast(list[ShaperStepConfig], [{"columns": []}])
        with pytest.raises(PipelineStepError) as exc_info:
            PipelineService.process_pipeline(sample_df, pipeline)
        assert exc_info.value.step_index == 0
        assert exc_info.value.shaper_type is None

    def test_failing_step_carries_index_and_type(self, sample_df: pd.DataFrame) -> None:
        """With two same-type steps, the SECOND failing must report index 1."""
        from src.core.services.shapers.pipeline_service import PipelineStepError

        pipeline = cast(
            list[ShaperStepConfig],
            [
                {"type": "columnSelector", "columns": ["benchmark", "ipc"]},
                {"type": "columnSelector", "columns": ["does_not_exist"]},
            ],
        )
        with pytest.raises(PipelineStepError) as exc_info:
            PipelineService.process_pipeline(sample_df, pipeline)
        assert exc_info.value.step_index == 1
        assert exc_info.value.shaper_type == "columnSelector"

    def test_is_a_valueerror(self) -> None:
        from src.core.services.shapers.pipeline_service import PipelineStepError

        assert issubclass(PipelineStepError, ValueError)
