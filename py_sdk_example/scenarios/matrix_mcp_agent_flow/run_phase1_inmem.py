"""Local InMemory runner for Phase 1 No-Matrix Core Flow.

This script runs the entire Phase 1 flow in a single process using the
InMemory transport, so no NATS server is required. It is useful for quick
local verification before switching to the distributed NATS setup.

Run:

    cd /Users/gubaoer/boyle_lab/learning/openagentio_example
    py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/run_phase1_inmem.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from openagentio import (
    Bus,
    Envelope,
    InMemoryDriver,
    WithAgentID,
    WithSessionPropagation,
    WithTransport,
)
from py_sdk_example.internal.common import wait_for_demo_transport


def _payload(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


async def on_send(env: Envelope) -> None:
    payload = env.payload_json()
    if not isinstance(payload, dict):
        return
    print("[matrix_sink] --- matrix.message.send ---")
    print(f"[matrix_sink] room_id={payload.get('room_id', '')}")
    print(f"[matrix_sink] text={payload.get('text', '')!r}")
    print(f"[matrix_sink] session_id={env.session_id}")
    print(f"[matrix_sink] conversation_id={env.conversation_id}")
    print(f"[matrix_sink] correlation_id={env.correlation_id}")


async def on_message(bus: Bus, env: Envelope) -> None:
    payload = env.payload_json()
    if not isinstance(payload, dict):
        return
    room_id = payload.get("room_id", "")
    sender = payload.get("sender", "")
    text = payload.get("text", "")
    print(f"[router] received from {sender} in {room_id}: {text!r}")

    reply = (
        f"Received your message: {text}\n\n"
        "Phase 1 core flow is working. "
        "Future phases will invoke MCP tools and a streaming reviewer."
    )
    reply_env = Envelope.new("matrix.message.send")
    reply_env.payload = _payload({"room_id": room_id, "text": reply})
    reply_env.session_id = env.session_id
    reply_env.conversation_id = env.conversation_id
    reply_env.correlation_id = env.correlation_id
    await bus.publish(reply_env)
    print(f"[router] published matrix.message.send to {room_id}")


async def main() -> None:
    bus = Bus.new(
        WithAgentID("phase1-local-runner"),
        WithTransport(InMemoryDriver()),
        WithSessionPropagation(True),
    )
    await bus.connect()

    try:
        await bus.subscribe("matrix.message.send", on_send)
        await bus.subscribe(
            "matrix.message.received", lambda env: on_message(bus, env)
        )

        room_id = "!demo:localhost"
        sender = "@admin:localhost"
        event_id = f"${uuid.uuid4()}"
        prompt = (
            "@openagentio inspect this repo and tell me whether it is ready "
            "for public release."
        )

        prompt_env = Envelope.new("matrix.message.received")
        prompt_env.payload = _payload(
            {
                "text": prompt,
                "html": None,
                "room_id": room_id,
                "sender": sender,
                "event_id": event_id,
                "origin_server_ts": 0,
                "msgtype": "m.text",
            }
        )
        prompt_env.session_id = room_id
        prompt_env.conversation_id = room_id
        prompt_env.correlation_id = event_id
        await bus.publish(prompt_env)
        print(f"[demo-prompt] published matrix.message.received event_id={event_id}")
        await wait_for_demo_transport(bus._transport)
        # Give handlers a moment to print before exiting.
        await asyncio.sleep(0.5)
    finally:
        await bus.close()


if __name__ == "__main__":
    asyncio.run(main())
