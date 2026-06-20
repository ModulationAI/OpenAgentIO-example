"""send_demo_prompt.py publishes a fake Matrix inbound event.

This triggers the No-Matrix Core Flow without needing Synapse, Element Web,
or a real Matrix bot token. The payload shape matches the contract produced
by ``MatrixEventBridge`` so the router-agent and matrix-sink can be reused
when the real Matrix bridge is wired in later phases.

In Phase 4 this script can initialize OpenTelemetry (when ``OTEL_ENABLED=1``
or ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set) so the published event starts a
trace that flows through router-agent, MCP tools, and the streaming reviewer.

Run (requires a local NATS server on nats://localhost:4222):

    cd /Users/gubaoer/boyle_lab/learning/openagentio_example
    py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/send_demo_prompt.py

Run with OTel (requires Jaeger on localhost:4317):

    OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/send_demo_prompt.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from opentelemetry import trace

from openagentio import (
    Bus,
    Envelope,
    OTelEnvelopePreparer,
    WithAgentID,
    WithEnvelopePreparer,
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
    return [WithEnvelopePreparer(OTelEnvelopePreparer())]


async def main() -> None:
    shutdown = init_tracer("send-demo-prompt") if _otel_enabled() else lambda: None

    try:
        try:
            tp = await dial(WithNATSName("demo-prompt-sender"))
        except Exception as err:
            print(f"transport: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        bus = Bus.new(
            WithAgentID("demo-prompt-sender"),
            WithTransport(tp),
            *_otel_options(),
        )
        await bus.connect()

        try:
            room_id = "!demo:localhost"
            sender = "@admin:localhost"
            event_id = f"${uuid.uuid4()}"
            prompt = (
                "@openagentio inspect this repo and tell me whether it is ready "
                "for public release."
            )

            prompt_env = Envelope.new("matrix.message.received")
            prompt_env.payload = json.dumps(
                {
                    "text": prompt,
                    "html": None,
                    "room_id": room_id,
                    "sender": sender,
                    "event_id": event_id,
                    "origin_server_ts": 0,
                    "msgtype": "m.text",
                },
                separators=(",", ":"),
            ).encode("utf-8")
            prompt_env.session_id = room_id
            prompt_env.conversation_id = room_id
            prompt_env.correlation_id = event_id

            if _otel_enabled():
                tracer = trace.get_tracer("send-demo-prompt")
                with tracer.start_as_current_span(
                    "send_demo_prompt.publish",
                    attributes={
                        "matrix.room_id": room_id,
                        "matrix.sender": sender,
                        "matrix.event_id": event_id,
                    },
                ) as span:
                    await bus.publish(prompt_env)
                    print(
                        f"[demo-prompt] published matrix.message.received "
                        f"event_id={event_id} "
                        f"trace_id={span.get_span_context().trace_id:032x}"
                    )
            else:
                await bus.publish(prompt_env)
                print(
                    f"[demo-prompt] published matrix.message.received event_id={event_id}"
                )

            await wait_for_demo_transport(tp)
        finally:
            await bus.close()
    finally:
        shutdown()


if __name__ == "__main__":
    asyncio.run(main())
