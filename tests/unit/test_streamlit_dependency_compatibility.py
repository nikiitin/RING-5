"""Compatibility checks for Streamlit's explicitly constrained dependencies."""

from __future__ import annotations

import asyncio

from starlette.types import Message, Receive, Scope, Send
from streamlit.web.server.starlette.starlette_gzip_middleware import (
    MediaAwareGZipMiddleware,
)


def test_streamlit_gzip_middleware_matches_starlette_responder_api() -> None:
    """Exercise the boundary that broke when Starlette 1.4 was resolved."""
    messages: list[Message] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        del scope, receive
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"RING-5 readiness response",
                "more_body": False,
            }
        )

    async def receive() -> Message:
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        messages.append(message)

    middleware = MediaAwareGZipMiddleware(app, minimum_size=1)
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/readiness",
        "headers": [(b"accept-encoding", b"gzip")],
    }

    asyncio.run(middleware(scope, receive, send))

    response_headers = dict(messages[0]["headers"])
    assert response_headers[b"content-encoding"] == b"gzip"
