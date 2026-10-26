"""Session.load admits its declared public source types before invoking Core."""

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

import ring5

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("perl_pool")]


def test_public_load_rejects_descriptor_and_other_unsupported_objects_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "stats.txt").write_text("simTicks 1.25\n", encoding="utf-8")
    variables: list[str | ring5.StatConfig] = [
        ring5.StatConfig(
            "value", "scalar", source_name="simTicks", params={"source_type": "scalar"}
        ),
        ring5.StatConfig(
            "label", "configuration", params={"source_type": "configuration", "on_empty": "NA"}
        ),
    ]
    with ring5.Session() as session:
        parsed = session.parse(str(inputs), variables)
        expected = session.load(parsed)
        state = session.api.state_manager
        origin = state.get_loaded_origin()
        assert origin is not None
        unsupported: list[object] = [
            parsed.output,
            Path(parsed.csv_path),
            expected,
            expected.frame,
            {"output": parsed.output, "source_context": parsed.source_context},
            object(),
            None,
        ]
        blocked = MagicMock(side_effect=AssertionError("Unsupported source reached Core"))
        with monkeypatch.context() as context:
            context.setattr(session.api, "load_data", blocked)
            for source in unsupported:
                with pytest.raises(
                    ring5.DataLoadError, match="CSV path string or ring5.ParseResult"
                ):
                    session.load(source)  # type: ignore[arg-type]
                current = state.get_data()
                assert current is not None
                pd.testing.assert_frame_equal(current, expected.frame)
                assert state.get_loaded_origin() is origin
        blocked.assert_not_called()
        assert expected.rows() == [{"value": 1.25, "label": "NA"}]
        # The explicit advanced Core descriptor seam retains its typed capability.
        session.api.load_data(parsed.output)
        current = state.get_data()
        assert current is not None
        pd.testing.assert_frame_equal(current, expected.frame)
        assert state.get_loaded_origin() is None
        assert session.load(parsed).rows() == expected.rows()
        external = tmp_path / "external.csv"
        external.write_text("kind,value\n001,1.25\n", encoding="utf-8")
        assert session.load(str(external)).rows() == [{"kind": 1, "value": 1.25}]
