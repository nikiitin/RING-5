"""Tests for the ring5 CLI (in-process — no subprocess)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ring5.cli import build_parser, main

# Shares the conftest `portfolios_dir` patching with the public-api suite —
# keep both files in one xdist group so they never interleave across workers.
pytestmark = [pytest.mark.xdist_group("ring5_portfolios"), pytest.mark.public_api]


class TestParserStructure:
    def test_subcommands_registered(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["doctor"])
        assert args.command == "doctor"

    def test_parse_requires_variable_and_output(self) -> None:
        with pytest.raises(SystemExit):
            build_parser().parse_args(["parse", "/some/dir"])

    def test_render_defaults(self) -> None:
        args = build_parser().parse_args(["render", "p", "-o", "out"])
        assert args.engine == "matplotlib"
        assert args.format is None
        assert args.no_deterministic is False


class TestDoctorCommand:
    # [test->req~ring5.api.doctor~1]
    def test_doctor_runs(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = main(["doctor"])
        out = capsys.readouterr().out
        assert "dependency check" in out
        assert code in (0, 1)  # 1 only when the essential Perl binary is absent


class TestParseCommand:
    # [test->req~ring5.cli.parse~1]
    def test_parse_materializes_session_owned_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        run = tmp_path / "run"
        run.mkdir()
        (run / "stats.txt").write_text("simTicks 42 # ticks\n")
        output = tmp_path / "result.csv"

        assert main(["parse", str(run), "-v", "simTicks", "-o", str(output)]) == 0
        assert pd.read_csv(output).loc[0, "simTicks"] == 42
        assert "wrote" in capsys.readouterr().out

    def test_parse_accepts_repeated_variables(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        run = tmp_path / "run"
        run.mkdir()
        (run / "stats.txt").write_text("simTicks 42 # ticks\nsimInsts 17 # instructions\n")
        output = tmp_path / "result.csv"

        code = main(
            [
                "parse",
                str(run),
                "-v",
                "simTicks",
                "-v",
                "simInsts",
                "-o",
                str(output),
            ]
        )

        assert code == 0
        parsed = pd.read_csv(output)
        assert parsed.loc[0, "simTicks"] == 42
        assert parsed.loc[0, "simInsts"] == 17
        assert "wrote" in capsys.readouterr().out


class TestRenderCommand:
    # [test->req~ring5.portfolio.batch-replay~1]
    # [test->req~ring5.cli.render~1]
    def test_render_portfolio_to_pdf(self, tmp_path: Path, portfolios_dir: Path) -> None:
        import ring5

        df = pd.DataFrame({"x": ["a", "b"], "y": [1.0, 2.0]})
        with ring5.Session() as s:
            s.create_plot("bar", data=df, config={"x": "x", "y": "y"}, name="cli_test")
            s.save_portfolio("cli_probe")

        code = main(["render", "cli_probe", "-o", str(tmp_path / "figs"), "--format", "pdf"])
        assert code == 0
        written = list((tmp_path / "figs").glob("*.pdf"))
        assert len(written) == 1
        assert written[0].read_bytes()[:5] == b"%PDF-"

    def test_missing_portfolio_exits_2(
        self, tmp_path: Path, portfolios_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(["render", "nope", "-o", str(tmp_path / "figs")])
        assert code == 2
        assert "error:" in capsys.readouterr().err

    def test_future_portfolio_exits_2(
        self, tmp_path: Path, portfolios_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (portfolios_dir / "future.json").write_text(json.dumps({"schema_version": 99}))
        code = main(["render", "future", "-o", str(tmp_path / "figs")])
        assert code == 2
        assert "newer than this RING-5" in capsys.readouterr().err


class TestUpgradeCommand:
    # [test->req~ring5.portfolio.upgrade-protection~1]
    def test_upgrade_persists_current_schema(
        self, portfolios_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # V1 on disk: no schema_version, export_* keys
        v1 = {
            "data_csv": "x,y\na,1\n",
            "plots": [
                {
                    "id": 0,
                    "name": "p",
                    "plot_type": "bar",
                    "config": {"x": "x", "y": "y", "export_format": "png"},
                    "processed_data": "x,y\na,1\n",
                }
            ],
            "plot_counter": 1,
            "config": {},
            "parse_variables": [],
        }
        (portfolios_dir / "old.json").write_text(json.dumps(v1))

        code = main(["upgrade", "old"])
        assert code == 0

        upgraded = json.loads((portfolios_dir / "old.json").read_text())
        assert upgraded["schema_version"] == 2
        assert "export_format" not in upgraded["plots"][0]["config"]


class TestUpgradeRefusal:
    # [test->req~ring5.portfolio.upgrade-protection~1]
    def test_upgrade_refuses_incomplete_restore(
        self, portfolios_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Re-saving a partial restore would permanently destroy what could
        not be loaded — upgrade must refuse and leave the file untouched."""
        bad = {
            "data_csv": "x,y\na,1\n",
            "plots": [
                {
                    "id": 0,
                    "name": "future_plot",
                    "plot_type": "no_such_plot_type",
                    "config": {},
                    "processed_data": "x,y\na,1\n",
                }
            ],
            "plot_counter": 1,
            "config": {},
            "parse_variables": [],
        }
        target = portfolios_dir / "bad.json"
        target.write_text(json.dumps(bad))
        before = target.read_bytes()

        code = main(["upgrade", "bad"])

        assert code == 2
        assert target.read_bytes() == before, "upgrade modified a file it refused"
        err = capsys.readouterr().err
        assert "refusing to upgrade" in err
        assert "future_plot" in err
