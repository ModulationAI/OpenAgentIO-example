"""server starts an OpenAgentIO Bus with the HTTP/SSE adapter enabled.

It is mainly used by the browser chat demo in ts_sdk_example/scenarios/sse_client.
Three targets are registered:

  - echo      : POST /v1/agents/echo/invoke      returns the request payload as-is.
  - count     : POST /v1/agents/count/stream     emits started + N deltas + final.
  - assistant : POST /v1/agents/assistant/stream emits text deltas for a chat UI.

Start the server:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/http_sse/server.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any

from openagentio import (
    Bus,
    Envelope,
    InMemoryDriver,
    Logging,
    Recover,
    StreamWriter,
    Trace,
    WithAgentID,
    WithLogger,
    WithMiddleware,
    WithTransport,
)


async def main() -> None:
    try:
        import uvicorn
        from openagentio.adapter.http import (
            Logging as HTTPLogging,
            New as HTTPNew,
            Recover as HTTPRecover,
            WithIdleTimeout as WithHTTPIdleTimeout,
            WithLogger as WithHTTPLogger,
            WithMiddleware as WithHTTPMiddleware,
            WithTimeout as WithHTTPTimeout,
        )
    except ImportError as err:
        print(
            "http_sse server requires the Python SDK HTTP dependencies: "
            "starlette and uvicorn",
            file=sys.stderr,
        )
        print(f"import failed: {err}", file=sys.stderr)
        raise SystemExit(1) from err

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    logger = logging.getLogger("sse-server")

    b = Bus.new(
        WithAgentID("sse-server"),
        WithTransport(InMemoryDriver()),
        WithLogger(logger),
        WithMiddleware(
            Recover(logger),
            Trace(),
            Logging(logger),
        ),
    )
    await b.connect()

    try:
        await b.handle_invoke("echo", echo)
        await b.handle_stream("count", count)
        await b.handle_stream("assistant", assistant)

        adapter = HTTPNew(
            b,
            WithHTTPLogger(logger),
            WithHTTPTimeout(30),
            WithHTTPIdleTimeout(10),
            WithHTTPMiddleware(
                HTTPRecover(logger),
                HTTPLogging(logger),
            ),
        )

        host, port = parse_addr(os.environ.get("ADDR", ":9080"))
        logger.info("sse-server listening", extra={"addr": f"{host}:{port}"})

        config = uvicorn.Config(
            adapter.app,
            host=host,
            port=port,
            log_level="info",
            timeout_graceful_shutdown=5,
        )
        server = uvicorn.Server(config)
        await server.serve()
    finally:
        await b.close()


async def echo(e: Envelope) -> bytes | None:
    payload = e.payload or b""
    logging.getLogger("sse-server").info(
        "echo invoked",
        extra={"payload": payload.decode("utf-8")},
    )
    return payload


async def count(e: Envelope, w: StreamWriter) -> None:
    args = payload_dict(e)
    n = int(args.get("n", 0) or 0)
    delay_ms = int(args.get("delay_ms", 0) or 0)
    if n <= 0:
        n = 5
    if delay_ms <= 0:
        delay_ms = 600

    await w.started(
        {
            "meta": {
                "model": "demo-llm",
                "n": n,
                "delay_ms": delay_ms,
            }
        }
    )

    delay = delay_ms / 1000
    for i in range(n):
        await w.delta({"data": {"i": i}})
        await asyncio.sleep(delay)

    await w.final({"result": {"total": n}})


async def assistant(e: Envelope, w: StreamWriter) -> None:
    args = payload_dict(e)
    message = str(args.get("message", "")).strip()
    delay_ms = int(args.get("delay_ms", 0) or 0)
    if not message:
        message = "How does OpenAgentIO streaming work?"
    if delay_ms <= 0:
        delay_ms = 140

    reply = (
        "OpenAgentIO streams this reply over Server-Sent Events. "
        f'Your message was: "{message}". '
        "Each chunk arrives as an agent.response.delta frame, so the browser "
        "can render the answer as it is generated."
    )
    chunks = chunk_words(reply, 3)

    await w.started(
        {
            "meta": {
                "agent": "assistant",
                "delay_ms": delay_ms,
            }
        }
    )

    delay = delay_ms / 1000
    for chunk in chunks:
        await w.delta({"delta": chunk})
        await asyncio.sleep(delay)

    await w.final({"result": {"text": reply}})


def payload_dict(e: Envelope) -> dict[str, Any]:
    payload = e.payload_json()
    if isinstance(payload, dict):
        return payload
    return {}


def chunk_words(text: str, size: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    if size <= 0:
        size = 1

    chunks = []
    for i in range(0, len(words), size):
        chunk_words_ = words[i : i + size]
        chunk = " ".join(chunk_words_)
        if i + size < len(words):
            chunk += " "
        chunks.append(chunk)
    return chunks


def parse_addr(addr: str) -> tuple[str, int]:
    if not addr:
        addr = ":9080"
    if addr.startswith(":"):
        return "0.0.0.0", int(addr[1:])
    host, _, port = addr.rpartition(":")
    if not host:
        host = "0.0.0.0"
    return host, int(port)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
