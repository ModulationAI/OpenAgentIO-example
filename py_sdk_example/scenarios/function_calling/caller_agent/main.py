"""caller_agent asks tool-agent to execute named functions.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/function_calling/caller_agent/main.py
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict, dataclass
from typing import Any

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
class FunctionCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class FunctionResult:
    name: str
    result: Any


async def main() -> None:
    agent_id = "caller-agent"

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
        calls = [
            FunctionCall(
                name="add_numbers",
                arguments={
                    "a": 7,
                    "b": 5,
                },
            ),
            FunctionCall(
                name="uppercase_text",
                arguments={
                    "text": "hello openagentio",
                },
            ),
        ]

        print("[caller-agent] requesting function calls from tool-agent")
        for call in calls:
            try:
                result = await invoke_function(b, call)
            except Exception as err:
                print(f"call {call.name} failed: {err}", file=sys.stderr)
                raise SystemExit(1) from err

            print(f"[caller-agent] {result.name} -> {result.result}")
    finally:
        await b.close()


async def invoke_function(b: Bus, call: FunctionCall) -> FunctionResult:
    resp = await b.invoke("tool-agent", asdict(call), WithTimeout(10))

    payload = resp.payload_json()
    if not isinstance(payload, dict):
        raise ValueError("decode response: expected object payload")

    return FunctionResult(
        name=str(payload.get("name", "")),
        result=payload.get("result"),
    )


if __name__ == "__main__":
    asyncio.run(main())
