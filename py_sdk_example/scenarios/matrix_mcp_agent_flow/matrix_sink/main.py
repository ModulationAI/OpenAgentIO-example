"""matrix_sink prints outbound Matrix messages to the terminal.

This is a stand-in for the real Matrix bridge in the No-Matrix Core Flow.
Instead of sending messages back to a Matrix room, it subscribes to
``matrix.message.send`` and prints the payload to stdout so the
end-to-end event flow can be verified without Synapse/Element Web.

In Phase 4 OpenTelemetry tracing is added (opt-in via ``OTEL_ENABLED=1`` or
``OTEL_EXPORTER_OTLP_ENDPOINT``).

Run (requires a local NATS server on nats://localhost:4222):

    cd /Users/gubaoer/boyle_lab/learning/openagentio_example
    py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/matrix_sink/main.py

Run with OTel (requires Jaeger on localhost:4317):

    OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/matrix_sink/main.py
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from openagentio import (
    Bus,
    Envelope,
    OTelEnvelopePreparer,
    OTelTrace,
    Recover,
    WithAgentID,
    WithEnvelopePreparer,
    WithMiddleware,
    WithNATSName,
    WithTransport,
    dial,
)
from py_sdk_example.internal.common import wait_for_demo_transport
from py_sdk_example.internal.otel import init_tracer


def _otel_enabled() -> bool:
    """Return True when the user explicitly enables OTel tracing."""
    return os.getenv("OTEL_ENABLED", "") == "1" or bool(
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    )


def _otel_options():
    """Return Bus options for OTel when enabled, otherwise an empty list."""
    if not _otel_enabled():
        return []
    return [
        WithMiddleware(
            Recover(),
            OTelTrace(),
        ),
        WithEnvelopePreparer(
            OTelEnvelopePreparer(),
        ),
    ]


async def on_send(env: Envelope) -> None:
    payload = env.payload_json()
    if not isinstance(payload, dict):
        print("[matrix_sink] received non-object payload", file=sys.stderr)
        return

    room_id = payload.get("room_id", "")
    text = payload.get("text", "")

    print("[matrix_sink] --- matrix.message.send ---")
    print(f"[matrix_sink] room_id={room_id}")
    print(f"[matrix_sink] text={text!r}")
    print(f"[matrix_sink] session_id={env.session_id}")
    print(f"[matrix_sink] conversation_id={env.conversation_id}")
    print(f"[matrix_sink] correlation_id={env.correlation_id}")


async def main() -> None:
    shutdown = init_tracer("matrix-sink") if _otel_enabled() else lambda: None
    agent_id = "matrix-sink"

    try:
        try:
            tp = await dial(WithNATSName(agent_id))
        except Exception as err:
            print(f"transport: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        bus = Bus.new(
            WithAgentID(agent_id),
            WithTransport(tp),
            *_otel_options(),
        )

        try:
            await bus.subscribe("matrix.message.send", on_send)
            await wait_for_demo_transport(tp)
            print("[matrix_sink] waiting for matrix.message.send events...")
            print("[matrix_sink] press Ctrl+C to exit")

            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop.set)
            await stop.wait()
            print("[matrix_sink] shutting down")
        finally:
            await bus.close()
    finally:
        shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
