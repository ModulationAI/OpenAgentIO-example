"""responder_agent handles request/reply calls from requester-agent.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/request_reply/responder_agent/main.py
"""
from __future__ import annotations

import asyncio
import signal
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from openagentio import (
    Bus,
    Envelope,
    Recover,
    Trace,
    WithAgentID,
    WithMiddleware,
    WithNATSName,
    WithTransport,
    dial,
)
from py_sdk_example.internal.common import wait_for_demo_transport


@dataclass
class Question:
    text: str


@dataclass
class Answer:
    text: str


async def main() -> None:
    agent_id = "responder-agent"

    try:
        tp = await dial(WithNATSName(agent_id))
    except Exception as err:
        print(f"transport: {err}", file=sys.stderr)
        raise SystemExit(1) from err

    b = Bus.new(
        WithAgentID(agent_id),
        WithTransport(tp),
        WithMiddleware(
            Recover(),
            Trace(),
        ),
    )

    try:
        try:
            await b.handle_invoke("responder-agent", handle_question)
        except Exception as err:
            print(f"register invoke handler: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        await wait_for_demo_transport(tp)

        print("[responder-agent] listening for request/reply calls")
        print("[responder-agent] start the requester in another terminal:")
        print("  py_sdk_example/.venv/bin/python py_sdk_example/scenarios/request_reply/requester_agent/main.py")
        print("[responder-agent] press Ctrl+C to exit")

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        await stop.wait()
        print("[responder-agent] shutting down")
    finally:
        await b.close()


async def handle_question(e: Envelope) -> dict[str, str]:
    payload = e.payload_json()
    if not isinstance(payload, dict):
        raise ValueError("decode request: expected object payload")

    question = Question(text=str(payload.get("text", "")))
    print(f"\n[responder-agent] request from {e.from_}: {question.text}")

    return asdict(Answer(text="hello from responder-agent"))


if __name__ == "__main__":
    asyncio.run(main())
