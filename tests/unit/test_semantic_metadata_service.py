"""Semantic labels, units, conversions, and automatic figure labels."""

import pandas as pd
import pytest

from src.core.models import ColumnSemantics, DatasetSemantics
from src.core.services.managers.semantic_metadata_service import SemanticMetadataService
from src.core.services.managers.schema_contract_service import SchemaContractService


def _annotated() -> pd.DataFrame:
    return SemanticMetadataService.attach(
        pd.DataFrame({"benchmark": ["a", "b"], "latency": [1.0, 2.5]}),
        DatasetSemantics(
            (
                ColumnSemantics("benchmark", "Workload"),
                ColumnSemantics("latency", "Mean latency", "milliseconds"),
            )
        ),
    )


def test_attach_inspect_and_convert_compatible_units_without_mutation() -> None:
    # [test->req~ring5.data.semantic-units~1]
    source = pd.DataFrame({"benchmark": ["a", "b"], "latency": [1.0, 2.5]})
    annotated = _annotated()
    converted = SemanticMetadataService.convert(annotated, "latency", "us")

    assert source.attrs == {}
    assert annotated["latency"].tolist() == [1.0, 2.5]
    assert converted["latency"].tolist() == pytest.approx([1000.0, 2500.0])
    assert SemanticMetadataService.inspect(annotated).for_column("latency") == ColumnSemantics(
        "latency", "Mean latency", "ms"
    )
    assert SemanticMetadataService.inspect(converted).for_column("latency") == ColumnSemantics(
        "latency", "Mean latency", "us"
    )


def test_temperature_conversion_supports_offsets() -> None:
    # [test->req~ring5.data.semantic-units~1]
    celsius = SemanticMetadataService.attach(
        pd.DataFrame({"temperature": [0.0, 100.0]}),
        DatasetSemantics((ColumnSemantics("temperature", "CPU temperature", "°C"),)),
    )

    fahrenheit = SemanticMetadataService.convert(celsius, "temperature", "°F")

    assert fahrenheit["temperature"].tolist() == pytest.approx([32.0, 212.0])


@pytest.mark.parametrize(
    ("column", "target", "message"),
    [
        ("latency", "MB", "not compatible"),
        ("latency", "parsecs", "Unsupported unit"),
        ("missing", "s", "does not exist"),
    ],
)
def test_conversion_rejects_invalid_requests(column: str, target: str, message: str) -> None:
    # [test->req~ring5.data.semantic-units~1]
    with pytest.raises((KeyError, ValueError), match=message):
        SemanticMetadataService.convert(_annotated(), column, target)


def test_figure_labels_are_inferred_but_explicit_labels_win() -> None:
    # [test->req~ring5.data.semantic-units~1]
    inferred = SemanticMetadataService.enrich_figure_config(
        _annotated(), {"x": "benchmark", "y": "latency"}
    )
    explicit = SemanticMetadataService.enrich_figure_config(
        _annotated(),
        {"x": "benchmark", "y": "latency", "xlabel": "Custom X", "ylabel": "Custom Y"},
    )

    assert inferred["xlabel"] == "Workload"
    assert inferred["ylabel"] == "Mean latency (ms)"
    assert explicit["xlabel"] == "Custom X"
    assert explicit["ylabel"] == "Custom Y"


def test_parallel_dimensions_receive_semantic_labels() -> None:
    # [test->req~ring5.data.semantic-units~1]
    config = SemanticMetadataService.enrich_figure_config(
        _annotated(),
        {"parallel_dimensions": ["latency", "benchmark"], "parallel_labels": {}},
    )

    assert config["parallel_labels"] == {
        "latency": "Mean latency (ms)",
        "benchmark": "Workload",
    }


def test_schema_inference_retains_existing_semantic_metadata() -> None:
    # [test->req~ring5.data.semantic-units~1]
    contract = SchemaContractService.infer(_annotated(), name="retained")

    assert contract.columns[0].semantic_label == "Workload"
    assert contract.columns[1].semantic_label == "Mean latency"
    assert contract.columns[1].unit == "ms"
