"""Integration coverage for the session background parsing workflow."""

from __future__ import annotations

import time
from pathlib import Path
from typing import cast

import pytest

from src.core.application_api import ApplicationAPI
from src.core.models import ParseJobStatus
from src.core.models.data_models import ParseVariableConfig
from src.core.services.data_services.csv_pool_service import CsvPoolService


@pytest.mark.parametrize("incremental", [False, True])
def test_background_gem5_parse_publishes_and_loads_recent_csv(
    tmp_path: Path,
    incremental: bool,
) -> None:
    stats_root = tmp_path / "stats"
    for index, ticks in enumerate((100, 200)):
        stats_file = stats_root / f"run-{index}" / "stats.txt"
        stats_file.parent.mkdir(parents=True)
        stats_file.write_text(
            "\n".join(
                [
                    "---------- Begin Simulation Statistics ----------",
                    f"simTicks {ticks}",
                    "---------- End Simulation Statistics   ----------",
                ]
            )
        )

    recent_dir = tmp_path / "recent"
    recent_dir.mkdir()
    original_pool_dir = CsvPoolService._pool_dir
    CsvPoolService._pool_dir = recent_dir
    api = ApplicationAPI()
    try:
        snapshot = api.submit_parse_job(
            str(stats_root),
            "stats.txt",
            cast(
                list[ParseVariableConfig],
                [{"name": "simTicks", "type": "scalar"}],
            ),
            incremental=incremental,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            current = api.get_parse_job(snapshot.job_id)
            if current is not None and current.status.is_terminal:
                break
            time.sleep(0.02)
        else:
            raise AssertionError("Background gem5 parse did not finish")

        assert current is not None
        assert current.status == ParseJobStatus.SUCCEEDED
        receipt = api.consume_parse_job(snapshot.job_id)
        assert Path(receipt.csv_path).is_file()
        assert Path(receipt.csv_path).parent == recent_dir
        assert api.get_parse_job(snapshot.job_id) is None

        data = api.state_manager.get_data()
        assert data is not None
        assert len(data) == 2
        assert "simTicks" in data.columns
    finally:
        api.close()
        CsvPoolService._pool_dir = original_pool_dir
