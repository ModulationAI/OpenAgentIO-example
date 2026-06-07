"""publisher_agent publishes an event that subscriber-agent can receive.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/pub_sub/publisher_agent/main.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
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


MESSAGE_EVENT = "agent.message.created"


@dataclass
class Message:
    from_: str
    text: str

    def to_payload(self) -> dict[str, str]:
        return {
            "from": self.from_,
            "text": self.text,
        }


async def main() -> None:
    agent_id = "publisher-agent"

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
        msg = Message(
            from_="publisher-agent",
            text="hello from OpenAgentIO pub/sub",
        )

        try:
            payload = json.dumps(msg.to_payload(), separators=(",", ":")).encode("utf-8")
        except Exception as err:
            print(f"encode payload: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        env = Envelope.new(MESSAGE_EVENT)
        env.from_ = msg.from_
        env.payload = payload

        print(f'[publisher-agent] publishing "{MESSAGE_EVENT}"')
        print(f"[publisher-agent] payload: {payload.decode('utf-8')}")

        try:
            await b.publish(env)
        except Exception as err:
            print(f"publish failed: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        try:
            await wait_for_demo_transport(tp)
        except Exception as err:
            print(f"wait for publish: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        print("[publisher-agent] message published")
    finally:
        await b.close()


if __name__ == "__main__":
    asyncio.run(main())
