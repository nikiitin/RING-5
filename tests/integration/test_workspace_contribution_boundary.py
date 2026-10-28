"""Real manager previews publish independent workspace data beside proven plots."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import ring5
from src.core.common.source_contributions import SOURCE_CONTRIBUTIONS_ATTR
from src.core.common.typed_table_codec import TypedTableCodec
from src.core.models.semantic_metadata_models import ColumnSemantics, DatasetSemantics

pytestmark = pytest.mark.public_api


@pytest.mark.parametrize(
    "operation", ["preprocessor", "mixer", "outlier", "seeds", "semantics", "units"]
)
def test_manager_preview_confirm_and_portfolio_save_keep_workspace_proof_independent(
    operation: str,
    isolated_application_data: Path,
) -> None:
    source = pd.DataFrame(
        {
            "benchmark": ["A"] * 4 + ["B"] * 4,
            "seed": [0, 1, 2, 3] * 2,
            "value": [1.0, 1.0, 1.0, 100.0, 2.0, 2.0, 2.0, 2.0],
            "other": [10.0] * 8,
        }
    )
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar", data=ring5.Table(source), config={"x": "benchmark", "y": "value"}
        )
        assert plot.processed_data is not None
        original_plot_proof = plot.processed_data.attrs[SOURCE_CONTRIBUTIONS_ATTR]
        proven = ring5.Table(plot.processed_data)
        session.add_dataset("working", proven)
        assert SOURCE_CONTRIBUTIONS_ATTR in proven.frame.attrs
        data = session.api.state_manager.get_data()
        assert data is not None
        assert SOURCE_CONTRIBUTIONS_ATTR not in data.attrs
        inputs = session.api.capture_preview_inputs()
        managers = session.api.managers
        if operation == "preprocessor":
            result = managers.apply_operation(data, "Sum", "value", "other", "adjusted")
            assert result["adjusted"].tolist() == [11.0, 11.0, 11.0, 110.0, 12.0, 12.0, 12.0, 12.0]
        elif operation == "mixer":
            result = managers.apply_mixer(data, "combined", ["value", "other"], "Sum")
            assert result["combined"].tolist() == [11.0, 11.0, 11.0, 110.0, 12.0, 12.0, 12.0, 12.0]
        elif operation == "outlier":
            result = managers.remove_outliers(data, "value", ["benchmark"])
            assert result["value"].tolist() == [1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 2.0]
        elif operation == "seeds":
            result = managers.reduce_seeds(data, ["benchmark"], ["value"])
            assert result["benchmark"].tolist() == ["A", "B"]
            assert result["value"].tolist() == [25.75, 2.0]
            assert result["value.sd"].tolist() == [49.5, 0.0]
        else:
            semantics = DatasetSemantics((ColumnSemantics("value", "Latency", "ns"),))
            result = managers.attach_semantics(data, semantics)
            if operation == "units":
                result = managers.convert_unit(result, "value", "us")
                assert result["value"].tolist() == pytest.approx([0.001] * 3 + [0.1] + [0.002] * 4)
            else:
                assert managers.inspect_semantics(result) == semantics
        assert SOURCE_CONTRIBUTIONS_ATTR not in result.attrs
        config = {"operation": operation}
        session.api.set_preview(operation, result, operation_config=config, inputs=inputs)
        confirmed = session.api.confirm_preview(
            operation, operation_config=config, operation=f"Apply {operation}"
        )
        assert SOURCE_CONTRIBUTIONS_ATTR not in confirmed.attrs
        current = session.get_dataset().frame
        decoded = TypedTableCodec.decode(TypedTableCodec.encode(current))
        assert decoded is not None
        pd.testing.assert_frame_equal(decoded, result)
        lineage = session.dataset_lineage()
        assert len(lineage.revisions) == 2
        for revision in lineage.revisions:
            retained = session.get_dataset_revision(revision.revision_id).frame
            assert SOURCE_CONTRIBUTIONS_ATTR not in retained.attrs
            TypedTableCodec.encode(retained)
        assert plot.processed_data.attrs[SOURCE_CONTRIBUTIONS_ATTR] is original_plot_proof
        assert session.drill_down(plot, {"benchmark": "A"}).rows.frame["value"].tolist() == [
            1.0,
            1.0,
            1.0,
            100.0,
        ]
        session.save_portfolio("workspace-independent")
    with ring5.Session() as restored:
        assert restored.load_portfolio("workspace-independent").complete
        restored_data = restored.api.state_manager.get_data()
        assert restored_data is not None
        assert SOURCE_CONTRIBUTIONS_ATTR not in restored_data.attrs
        assert restored.drill_down(restored.plots[0], {"benchmark": "A"}).row_count == 4
