"""worker_agent registers multiple worker targets for the parallel execution demo.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/parallel_execution/worker_agent/main.py
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
class AnalyzeRequest:
    text: str


@dataclass
class AnalysisResult:
    agent: str
    text: str


async def main() -> None:
    agent_id = "worker-agent"

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
        handlers = {
            "summary-agent": handle_summary,
            "sentiment-agent": handle_sentiment,
            "keywords-agent": handle_keywords,
        }
        for target, handler in handlers.items():
            try:
                await b.handle_invoke(target, handler)
            except Exception as err:
                print(f"register {target}: {err}", file=sys.stderr)
                raise SystemExit(1) from err

        try:
            await wait_for_demo_transport(tp)
        except Exception as err:
            print(f"wait for handlers: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        print("[worker-agents] listening for parallel requests")
        print("[worker-agents] targets: summary-agent, sentiment-agent, keywords-agent")
        print("[worker-agents] start the coordinator in another terminal:")
        print("  py_sdk_example/.venv/bin/python py_sdk_example/scenarios/parallel_execution/coordinator_agent/main.py")
        print("[worker-agents] press Ctrl+C to exit")

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        await stop.wait()
        print("[worker-agents] shutting down")
    finally:
        await b.close()


async def handle_summary(e: Envelope) -> dict[str, str]:
    req = decode_request(e)

    print(f"\n[summary-agent] analyzing: {req.text}")
    return asdict(
        AnalysisResult(
            agent="summary-agent",
            text="OpenAgentIO connects multiple agents.",
        )
    )


async def handle_sentiment(e: Envelope) -> dict[str, str]:
    req = decode_request(e)

    print(f"\n[sentiment-agent] analyzing: {req.text}")
    return asdict(
        AnalysisResult(
            agent="sentiment-agent",
            text="positive",
        )
    )


async def handle_keywords(e: Envelope) -> dict[str, str]:
    req = decode_request(e)

    print(f"\n[keywords-agent] analyzing: {req.text}")
    words = ["OpenAgentIO", "agents", "communication"]
    return asdict(
        AnalysisResult(
            agent="keywords-agent",
            text=", ".join(words),
        )
    )


def decode_request(e: Envelope) -> AnalyzeRequest:
    payload = e.payload_json()
    if not isinstance(payload, dict):
        raise ValueError("decode request: expected object payload")
    return AnalyzeRequest(text=str(payload.get("text", "")))


if __name__ == "__main__":
    asyncio.run(main())
