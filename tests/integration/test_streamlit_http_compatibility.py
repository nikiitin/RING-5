"""Exercise the installed web stack through its public HTTP boundary."""

import gzip
from pathlib import Path
from urllib.request import Request, urlopen

from tests.helpers.streamlit_server import free_loopback_port, running_streamlit


def test_streamlit_serves_compressed_html(tmp_path: Path) -> None:
    """A real server serves its app shell and a compressible static response."""
    script = tmp_path / "app.py"
    script.write_text('import streamlit as st\nst.write("Compatibility probe")\n', encoding="utf-8")
    static = tmp_path / "static"
    static.mkdir()
    payload = "compatibility probe\n" * 500
    (static / "probe.txt").write_text(payload, encoding="utf-8")
    with running_streamlit(
        script,
        port=free_loopback_port(),
        environment={"STREAMLIT_SERVER_ENABLE_STATIC_SERVING": "true"},
    ) as url:
        # Current Streamlit ships a precompressed shell (often Brotli) and may
        # return identity for other encodings. Exercise gzip on an owned asset.
        with urlopen(url, timeout=10) as response:
            assert response.status == 200
            assert "<html" in response.read().decode("utf-8").lower()
        request = Request(url + "/app/static/probe.txt", headers={"Accept-Encoding": "gzip"})
        with urlopen(request, timeout=10) as response:
            assert response.status == 200
            assert response.headers["Content-Encoding"] == "gzip"
            assert gzip.decompress(response.read()).decode("utf-8") == payload
