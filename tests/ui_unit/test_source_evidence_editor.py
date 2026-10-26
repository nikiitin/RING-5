"""Real scanned-label views keep explicit parser editor contracts runnable."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import ring5
from streamlit.testing.v1 import AppTest

from src.core.common.source_entry_labels import canonical_source_entry
from src.parsing.gem5.impl.scanning.scanner import Gem5StatsScanner

pytestmark = pytest.mark.xdist_group("perl_pool")


@pytest.mark.parametrize(
    "kind,entry,expected",
    [
        ("histogram", "0", "0-0"),
        ("histogram", "-1", "-1--1"),
        ("histogram", "0-0", "0-0"),
        ("vector", "0", "0"),
        ("distribution", "0", "0"),
        ("", "0", "0"),
    ],
)
def test_explicit_contract_label_projection_preserves_other_literal_names(
    kind: str, entry: str, expected: str
) -> None:
    assert canonical_source_entry(kind, entry) == expected


def test_saved_histogram_vector_selection_survives_real_editor_and_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RING5_DATA_DIR", str(tmp_path / "storage"))
    path = tmp_path / "stats.txt"
    path.write_text("h::gmean 1\nh::0 2\n")
    record = Gem5StatsScanner.get_instance().scan_file(path).variables[0].to_dict()
    assert record["entries"] == ["0", "gmean"]
    script = """from copy import deepcopy
import json
import streamlit as st
from src.core.application_api import ApplicationAPI
from src.web.components.data_source.variable_editor import VariableEditor
api=ApplicationAPI()
original={"name":"h","type":"vector","params":{"source_type":"histogram","entries":["0-0"]}}
config=deepcopy(original)
records=json.loads(PAYLOAD)
VariableEditor.render_vector_config(api,config,original,"saved",records,None,"stats.txt")
st.session_state["result"]=config
api.close()
""".replace("PAYLOAD", repr(json.dumps([record])))
    app = AppTest.from_string(script).run(timeout=15)
    assert not app.exception
    assert app.multiselect[0].options == ["0-0"]
    assert app.multiselect[0].value == ["0-0"]
    draft = app.session_state["result"]
    assert draft["params"] == {"source_type": "histogram", "entries": ["0-0"]}
    with ring5.Session() as session:
        configs = session.api.compile_parse_variables([draft])
        parsed = session.parse(str(tmp_path), variables=configs)
        assert session.load(parsed).rows() == [{"h..0-0": 2.0}]
    assert record["entries"] == ["0", "gmean"]
