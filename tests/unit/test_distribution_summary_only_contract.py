"""Summary requests retain measured values without certifying native frequency cells."""

from pathlib import Path

import math
import pytest

from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsing_models import StatConfig
from src.parsing.gem5.impl import source_bindings
from src.parsing.gem5.impl.strategies.simple import SimpleStatsStrategy

pytestmark = pytest.mark.xdist_group("perl_pool")


@pytest.mark.parametrize("output_type", ["distribution", "histogram", "vector"])
@pytest.mark.parametrize("oneline", [False, True])
@pytest.mark.parametrize("measured_summary", [False, True])
def test_summary_only_ignores_unrequested_fractional_cells_and_owns_no_layout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    output_type: str,
    oneline: bool,
    measured_summary: bool,
) -> None:
    def no_grid(*args: object, **kwargs: object) -> None:
        raise AssertionError("Summary-only extraction must not construct a native grid.")

    monkeypatch.setattr(source_bindings, "DistributionGeometry", no_grid)
    monkeypatch.setattr(source_bindings, "native_bucket_label", no_grid)
    source = tmp_path / "stats.txt"
    header = "d::samples 2\n" + ("d::mean 1.25\n" if measured_summary else "")
    frequencies = (
        "d::bucket_size 1\nd::min_bucket 0.250000\nd::max_bucket 1.250000\nd | 2 | 3\n"
        if oneline
        else "d::0.25 2\nd::1.25 3\n"
    )
    source.write_text(header + frequencies)
    config = StatConfig(
        "summary",
        output_type,
        source_name="d",
        statistics_only=True,
        params={"source_type": "distribution", "statistics": ["mean"]},
    )
    plan = source_bindings.resolve_sources([config], None, file_count=1, metadata_columns=())
    assert plan.accumulators[0].layout is None
    work = SimpleStatsStrategy().get_work_items((str(source),), plan)[0]
    result = work()
    variable = result.variables[0]
    assert variable.layout is None and variable.schema.layout is None
    assert tuple(cell.column for cell in variable.cells) == ("summary..mean",)
    value = variable.cells[0].value
    assert isinstance(value, float)
    if measured_summary:
        assert value == 1.25 and variable.missing_measurements == 0
    else:
        assert math.isnan(value) and variable.missing_measurements == 1
    table = ParsedOutputIO.resolve((result,), ("summary",), (str(source),))
    assert table.schema.variables[0].layout is None
    output = ParsedOutputIO.publish(tmp_path / "summary.csv", table)
    frame = ParsedOutputIO.to_frame(output)
    assert tuple(frame.columns) == ("summary..mean",)
    assert "ring5.distribution_layouts" not in frame.attrs
