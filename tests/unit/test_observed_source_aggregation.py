"""Scan aggregation preserves observations without synthesizing native grid bounds."""

from src.core.models.source_evidence import AmbiguousSourceKind
from src.core.models.parsing_models import ScannedVariable, ScanFileResult, SourceInstance
from src.parsing.gem5.impl.gem5_parser import Gem5Parser


class TestObservedSourceAggregation:
    # [test->req~ring5.ingestion.distribution-range-scan~2]
    def test_merging_logic_in_async_pipeline(self) -> None:
        evidence = AmbiguousSourceKind(("distribution", "vector"))
        raw_results = [
            ScanFileResult(
                path,
                [
                    ScannedVariable(
                        "dist_var",
                        None,
                        entries,
                        source_evidence=evidence,
                        instances=(SourceInstance("dist_var", ()),),
                    )
                ],
            )
            for path, entries in [("f0", ["-5", "10"]), ("f1", ["-10", "15"])]
        ]
        result = Gem5Parser.aggregate_scan_results(raw_results)
        assert len(result.variables) == 1
        dist = result.variables[0]
        assert dist.name == "dist_var"
        assert set(dist.entries) == {"-10", "-5", "10", "15"}
        assert dist.type is None and dist.source_evidence == evidence
        assert "minimum" not in dist.to_dict() and "maximum" not in dist.to_dict()

    def test_grouping_logic_in_facade(self) -> None:
        evidence = AmbiguousSourceKind(("distribution", "vector"))
        variable = ScannedVariable(
            r"system.cpu\d+.dist",
            None,
            ["0", "20"],
            source_evidence=evidence,
            instances=(
                SourceInstance("system.cpu0.dist", ("0",)),
                SourceInstance("system.cpu1.dist", ("1",)),
            ),
        )
        result = Gem5Parser.aggregate_scan_results([ScanFileResult("f0", [variable])])
        assert len(result.variables) == 1
        group = result.variables[0]
        assert group.name == r"system.cpu\d+.dist"
        assert group.entries == ["0", "20"]
        assert group.instances == variable.instances
        assert group.source_evidence == evidence and group.type is None
        assert "minimum" not in group.to_dict() and "maximum" not in group.to_dict()
