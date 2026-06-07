"""subscriber_agent subscribes to events from publisher-agent.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/pub_sub/subscriber_agent/main.py
"""
from __future__ import annotations

import asyncio
import signal
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from openagentio import (
    Bus,
    Envelope,
    Recover,
    Subscription,
    Trace,
    WithAgentID,
    WithMiddleware,
    WithNATSName,
    WithTransport,
    dial,
)
from py_sdk_example.internal.common import wait_for_demo_transport


MESSAGE_EVENT = "agent.message.created"


@dataclass
class Message:
    from_: str
    text: str


async def main() -> None:
    agent_id = "subscriber-agent"

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

    sub: Subscription | None = None
    try:
        try:
            sub = await b.subscribe(MESSAGE_EVENT, handle_message)
        except Exception as err:
            print(f"subscribe: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        try:
            await wait_for_demo_transport(tp)
        except Exception as err:
            print(f"wait for subscription: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        print(f'[subscriber-agent] subscribed to "{MESSAGE_EVENT}"')
        print("[subscriber-agent] start the publisher in another terminal:")
        print("  py_sdk_example/.venv/bin/python py_sdk_example/scenarios/pub_sub/publisher_agent/main.py")
        print("[subscriber-agent] press Ctrl+C to exit")

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        await stop.wait()
        print("[subscriber-agent] shutting down")
    finally:
        if sub is not None:
            await sub.unsubscribe()
        await b.close()


async def handle_message(e: Envelope) -> None:
    payload = e.payload_json()
    if not isinstance(payload, dict):
        raise ValueError("decode payload: expected object payload")

    msg = Message(
        from_=str(payload.get("from", "")),
        text=str(payload.get("text", "")),
    )

    print(f'\n[subscriber-agent] received "{e.event_type}"')
    print(f"[subscriber-agent] event_id={e.event_id} trace_id={e.trace_id}")
    print(f"[subscriber-agent] message from {msg.from_}: {msg.text}")


if __name__ == "__main__":
    asyncio.run(main())
