"""user_agent sends a question to router-agent and receives the specialist answer.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/agent_handoff/user_agent/main.py
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
    handled_by: str
    text: str


async def main() -> None:
    agent_id = "user-agent"

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
        question = Question(text="I need help with my invoice")

        print("[user-agent] invoking router-agent")
        print(f"[user-agent] question: {question.text}")

        try:
            resp = await b.invoke("router-agent", asdict(question), WithTimeout(10))
        except Exception as err:
            print(f"invoke failed: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        payload = resp.payload_json()
        if not isinstance(payload, dict):
            print("decode response: expected object payload", file=sys.stderr)
            raise SystemExit(1)

        answer = Answer(
            handled_by=str(payload.get("handled_by", "")),
            text=str(payload.get("text", "")),
        )

        print(f"[user-agent] response from {answer.handled_by}: {answer.text}")
    finally:
        await b.close()


if __name__ == "__main__":
    asyncio.run(main())
