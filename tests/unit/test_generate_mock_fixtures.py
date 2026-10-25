"""Fresh-checkout mock-data generation uses the real current parser contract."""

from pathlib import Path

import pandas as pd
import pytest

from scripts import generate_mock_fixtures as generator

pytestmark = pytest.mark.xdist_group("perl_pool")


def test_missing_fixture_is_generated_from_isolated_real_stats(tmp_path: Path, monkeypatch) -> None:
    stats_root = tmp_path / "stats"
    output = tmp_path / "mock" / "configurer_test_case01.csv"
    for seed, ticks, misses in [(0, 10.5, 2), (1, 14.5, 4)]:
        path = stats_root / str(seed) / "stats.txt"
        path.parent.mkdir(parents=True)
        path.write_text(
            "config_description_abbrev=baseline\nbenchmark_name=case\n"
            f"simTicks {ticks}\nsystem.cpu0.branchMispredicts {misses}\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generator, "STATS_ROOT", stats_root)
    monkeypatch.setattr(generator, "OUTPUT_CSV", output)
    assert not output.exists()

    assert generator.main() == 0

    result = pd.read_csv(output, sep=r"\s+")
    assert list(result.columns) == generator.FINAL_ORDER
    assert result.to_dict("records") == [
        {
            "benchmark_name": "case",
            "config_description_abbrev": "baseline",
            "simTicks": 12.5,
            "branchMispredicts": 3.0,
        }
    ]
    before = output.read_bytes()
    assert generator.main() == 0
    assert output.read_bytes() == before
