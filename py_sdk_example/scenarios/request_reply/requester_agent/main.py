"""requester_agent sends a request to responder-agent and waits for one response.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/request_reply/requester_agent/main.py
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict, dataclass

from openagentio import (
    Bus,
    Recover,
    Trace,
    WithAgentID,
    WithMiddleware,
    WithNATSName,
    WithTimeout,
    WithTransport,
    dial,
)


@dataclass
class Question:
    text: str


@dataclass
class Answer:
    text: str


async def main() -> None:
    agent_id = "requester-agent"

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
        req = Question(text="hello from requester-agent")

        print("[requester-agent] invoking responder-agent")
        print(f"[requester-agent] request: {req.text}")

        try:
            resp = await b.invoke(
                "responder-agent",
                asdict(req),
                WithTimeout(10),
            )
        except Exception as err:
            print(f"invoke failed: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        payload = resp.payload_json()
        if not isinstance(payload, dict):
            print("decode response: expected object payload", file=sys.stderr)
            raise SystemExit(1)

        answer = Answer(text=str(payload.get("text", "")))
        print(f"[requester-agent] response: {answer.text}")
    finally:
        await b.close()


if __name__ == "__main__":
    asyncio.run(main())
