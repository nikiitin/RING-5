"""Browser diagnostic identity and exported document contracts."""

import pytest

from tests.helpers.html_assertions import assert_plotly_document
from tests.helpers.streamlit_server import artifact_stem


def test_artifact_names_distinguish_classes_parameters_and_workers() -> None:
    """Equal method names cannot overwrite another test's diagnostic artifact."""
    nodeids = [
        "tests/e2e/test_page.py::TestFirst::test_load[param/a]",
        "tests/e2e/test_page.py::TestSecond::test_load[param/a]",
        "tests/e2e/test_page.py::TestFirst::test_load[param/b]",
    ]
    names = {artifact_stem(nodeid, worker) for nodeid in nodeids for worker in ("gw0", "gw1")}
    assert len(names) == 6
    assert all("/" not in name and len(name) < 160 for name in names)


@pytest.mark.parametrize("doctype", ["", "<!doctype html>\n"])
def test_document_assertion_accepts_optional_doctype(doctype: str) -> None:
    """A valid HTML5 doctype does not change the export contract."""
    assert_plotly_document(
        doctype + '<html><head></head><body><div></div><script>Plotly.newPlot("p");'
        "</script></body></html>"
    )


@pytest.mark.parametrize(
    "content",
    [
        "<html>not a chart</html>",
        '<html><head></head><body><div></div><script src="https://cdn.example/plotly.js">'
        '</script><script>Plotly.newPlot("p");</script></body></html>',
    ],
)
def test_document_assertion_rejects_incomplete_or_network_dependent_exports(content: str) -> None:
    """An HTML prefix alone cannot establish a complete offline chart."""
    with pytest.raises(AssertionError):
        assert_plotly_document(content)
