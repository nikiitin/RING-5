"""Browser diagnostic identity and exported document contracts."""

import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.helpers.html_assertions import assert_plotly_document
from tests.helpers.streamlit_server import artifact_stem, free_loopback_port, running_streamlit


def test_server_rejects_occupied_port_without_launching(tmp_path: Path) -> None:
    """A foreign application must never become the browser fixture's target."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        with patch("tests.helpers.streamlit_server.subprocess.Popen") as launch:
            with pytest.raises(RuntimeError, match="already occupied"):
                with running_streamlit(tmp_path / "app.py", port=port):
                    pytest.fail("An unrelated listener was accepted as the app.")
            launch.assert_not_called()


def test_server_rejects_foreign_listener_that_wins_launch_race(tmp_path: Path) -> None:
    """A listener created after the port check cannot satisfy owned readiness."""
    requests: list[str] = []

    class ForeignApp(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<html>another application</html>")

        def log_message(self, format: str, *args: object) -> None:
            return

    process = MagicMock()
    process.poll.side_effect = [None, 1, 1]
    servers: list[ThreadingHTTPServer] = []

    def launch(command: list[str], **kwargs: object) -> MagicMock:
        port = int(command[command.index("--server.port") + 1])
        server = ThreadingHTTPServer(("127.0.0.1", port), ForeignApp)
        servers.append(server)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return process

    try:
        with patch("tests.helpers.streamlit_server.subprocess.Popen", side_effect=launch):
            with pytest.raises(RuntimeError, match="exited during startup"):
                with running_streamlit(tmp_path / "app.py", port=free_loopback_port()):
                    pytest.fail("A racing foreign application was accepted.")
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
    assert requests and requests[0].startswith("/_ring5_test_")


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
