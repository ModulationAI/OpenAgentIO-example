"""handoff-agents registers router-agent and specialist targets for handoff.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/agent_handoff/handoff-agents/main.py
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
    WithTimeout,
    WithTransport,
    dial,
)
from py_sdk_example.internal.common import wait_for_demo_transport


@dataclass
class Question:
    text: str


@dataclass
class Answer:
    handled_by: str
    text: str


async def main() -> None:
    agent_id = "handoff-agents"

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
            await b.handle_invoke("router-agent", lambda e: handle_router(b, e))
        except Exception as err:
            print(f"register router-agent: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        try:
            await b.handle_invoke("billing-agent", handle_billing)
        except Exception as err:
            print(f"register billing-agent: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        try:
            await b.handle_invoke("tech-agent", handle_tech)
        except Exception as err:
            print(f"register tech-agent: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        try:
            await wait_for_demo_transport(tp)
        except Exception as err:
            print(f"wait for handlers: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        print("[handoff-agents] listening for handoff requests")
        print("[handoff-agents] targets: router-agent, billing-agent, tech-agent")
        print("[handoff-agents] start the user in another terminal:")
        print("  py_sdk_example/.venv/bin/python py_sdk_example/scenarios/agent_handoff/user_agent/main.py")
        print("[handoff-agents] press Ctrl+C to exit")

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        await stop.wait()
        print("[handoff-agents] shutting down")
    finally:
        await b.close()


async def handle_router(b: Bus, e: Envelope) -> dict[str, str]:
    question = decode_question(e)

    target = choose_target(question.text)
    print(f"\n[router-agent] handoff to {target} for: {question.text}")

    try:
        resp = await b.invoke(target, asdict(question), WithTimeout(5))
    except Exception as err:
        raise RuntimeError(f"handoff to {target} failed: {err}") from err

    payload = resp.payload_json()
    if not isinstance(payload, dict):
        raise ValueError("decode handoff response: expected object payload")

    answer = Answer(
        handled_by=str(payload.get("handled_by", "")),
        text=str(payload.get("text", "")),
    )
    return asdict(answer)


async def handle_billing(e: Envelope) -> dict[str, str]:
    question = decode_question(e)

    print(f"[billing-agent] handling: {question.text}")
    return asdict(
        Answer(
            handled_by="billing-agent",
            text="Billing can help with invoice and payment questions.",
        )
    )


async def handle_tech(e: Envelope) -> dict[str, str]:
    question = decode_question(e)

    print(f"[tech-agent] handling: {question.text}")
    return asdict(
        Answer(
            handled_by="tech-agent",
            text="Tech support can help troubleshoot API and integration issues.",
        )
    )


def choose_target(text: str) -> str:
    lower = text.lower()
    if "invoice" in lower or "billing" in lower or "payment" in lower:
        return "billing-agent"
    return "tech-agent"


def decode_question(e: Envelope) -> Question:
    payload = e.payload_json()
    if not isinstance(payload, dict):
        raise ValueError("decode question: expected object payload")
    return Question(text=str(payload.get("text", "")))


if __name__ == "__main__":
    asyncio.run(main())
