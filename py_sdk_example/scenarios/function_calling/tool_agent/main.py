"""tool_agent exposes local Python functions through tool-agent.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/function_calling/tool_agent/main.py
"""
from __future__ import annotations

import asyncio
import signal
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

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
class FunctionCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class FunctionResult:
    name: str
    result: Any


ToolFunc = Callable[[dict[str, Any]], Any]


async def main() -> None:
    agent_id = "tool-agent"

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
        tools: dict[str, ToolFunc] = {
            "add_numbers": add_numbers,
            "uppercase_text": uppercase_text,
        }

        try:
            await b.handle_invoke("tool-agent", handle_function_call(tools))
        except Exception as err:
            print(f"register tool-agent: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        try:
            await wait_for_demo_transport(tp)
        except Exception as err:
            print(f"wait for handler: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        print("[tool-agent] listening for function calls")
        print("[tool-agent] functions: add_numbers, uppercase_text")
        print("[tool-agent] start the caller in another terminal:")
        print("  py_sdk_example/.venv/bin/python py_sdk_example/scenarios/function_calling/caller_agent/main.py")
        print("[tool-agent] press Ctrl+C to exit")

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        await stop.wait()
        print("[tool-agent] shutting down")
    finally:
        await b.close()


def handle_function_call(
    tools: dict[str, ToolFunc],
) -> Callable[[Envelope], Any]:
    async def handle(e: Envelope) -> dict[str, Any]:
        payload = e.payload_json()
        if not isinstance(payload, dict):
            raise ValueError("decode function call: expected object payload")

        call = FunctionCall(
            name=str(payload.get("name", "")),
            arguments=dict(payload.get("arguments", {})),
        )

        tool = tools.get(call.name)
        if tool is None:
            raise ValueError(f"unknown function: {call.name}")

        print(f"\n[tool-agent] calling {call.name} with {call.arguments}")
        result = tool(call.arguments)

        return asdict(
            FunctionResult(
                name=call.name,
                result=result,
            )
        )

    return handle


def add_numbers(args: dict[str, Any]) -> Any:
    a = number_arg(args, "a")
    b = number_arg(args, "b")
    return a + b


def uppercase_text(args: dict[str, Any]) -> Any:
    text = string_arg(args, "text")
    return text.upper()


def number_arg(args: dict[str, Any], name: str) -> float:
    if name not in args:
        raise ValueError(f'missing argument "{name}"')

    value = args[name]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'argument "{name}" must be a number')
    return value


def string_arg(args: dict[str, Any], name: str) -> str:
    if name not in args:
        raise ValueError(f'missing argument "{name}"')

    value = args[name]
    if not isinstance(value, str):
        raise ValueError(f'argument "{name}" must be a string')
    return value


if __name__ == "__main__":
    asyncio.run(main())
