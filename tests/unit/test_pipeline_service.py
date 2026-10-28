"""Tests for PipelineService — the canonical shaper-pipeline execution engine."""

from typing import cast
from unittest.mock import Mock, patch

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

    def test_repeated_shaper_type_applies_each_configuration_in_order(self) -> None:
        source = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9], "d": [10, 11, 12]})
        original = source.copy(deep=True)
        pipeline: list[ShaperStepConfig] = [
            {"type": "columnSelector", "columns": ["a", "b", "c"]},
            {"type": "columnSelector", "columns": ["a", "b"]},
        ]
        result = PipelineService.process_pipeline(source, pipeline)
        pd.testing.assert_frame_equal(result, original[["a", "b"]])
        pd.testing.assert_frame_equal(source, original)

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
        with pytest.raises(ValueError, match="registered shaper type"):
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


@pytest.mark.parametrize("returned", [None, 1, pd.Series([1])])
def test_invalid_step_output_fails_before_metadata_and_later_steps(returned: object) -> None:
    from src.core.services.shapers.pipeline_service import PipelineStepError

    source = pd.DataFrame({"x": [1]})
    before = source.copy(deep=True)
    pipeline: list[ShaperStepConfig] = [
        {"type": "columnSelector", "columns": ["x"]},
        {"type": "columnSelector", "columns": ["x"]},
    ]
    operation = Mock(return_value=returned)
    with (
        patch(
            "src.core.services.shapers.pipeline_service.ShaperFactory.create_shaper",
            side_effect=[operation, AssertionError("later step reached")],
        ) as create,
        patch("src.core.services.shapers.pipeline_service._distribution_policy") as policy,
        pytest.raises(PipelineStepError) as failure,
    ):
        PipelineService.process_pipeline(source, pipeline)
    assert failure.value.step_index == 0
    assert failure.value.shaper_type == "columnSelector"
    assert type(failure.value.__cause__) is TypeError
    assert str(failure.value.__cause__) == (
        f"Shaper output must be a pandas DataFrame; got {type(returned).__name__}."
    )
    assert create.call_count == 1
    operation.assert_called_once()
    policy.assert_not_called()
    pd.testing.assert_frame_equal(source, before)


@pytest.mark.parametrize("values", [[], [2.5]])
def test_frame_step_output_reaches_the_current_metadata_policy(values: list[float]) -> None:
    from src.core.services.shapers.pipeline_service import _distribution_policy

    source = pd.DataFrame({"x": [1]})
    returned = pd.DataFrame({"x": pd.Series(values, dtype="float64")})
    operation = Mock(return_value=returned)
    with (
        patch(
            "src.core.services.shapers.pipeline_service.ShaperFactory.create_shaper",
            return_value=operation,
        ),
        patch(
            "src.core.services.shapers.pipeline_service._distribution_policy",
            wraps=_distribution_policy,
        ) as policy,
    ):
        result = PipelineService.process_pipeline(
            source, [{"type": "columnSelector", "columns": ["x"]}]
        )
    policy.assert_called_once()
    assert policy.call_args.args[2] is returned
    pd.testing.assert_frame_equal(result, returned)
    assert source["x"].tolist() == [1]
