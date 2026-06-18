"""backend-agent performs the actual calculation.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/otel_tracing/backend/main.py
"""
from __future__ import annotations

import asyncio
import signal
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from opentelemetry import trace

from openagentio import (
    Bus,
    Envelope,
    OTelEnvelopePreparer,
    OTelTrace,
    Recover,
    WithAgentID,
    WithEnvelopePreparer,
    WithMiddleware,
    WithNATSName,
    WithTransport,
    dial,
)
from py_sdk_example.internal.common import wait_for_demo_transport
from py_sdk_example.internal.otel import init_tracer


@dataclass
class CalcRequest:
    a: int
    b: int
    op: str


@dataclass
class CalcResponse:
    result: int
    agent: str


async def main() -> None:
    shutdown = init_tracer("backend-agent")
    agent_id = "backend-agent"

    try:
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
                OTelTrace(),
            ),
            WithEnvelopePreparer(
                OTelEnvelopePreparer(),
            ),
        )

        try:
            try:
                await b.handle_invoke("backend-agent", handle_calc)
            except Exception as err:
                print(f"register backend-agent: {err}", file=sys.stderr)
                raise SystemExit(1) from err

            try:
                await wait_for_demo_transport(tp)
            except Exception as err:
                print(f"wait for handlers: {err}", file=sys.stderr)
                raise SystemExit(1) from err

            print("[backend-agent] listening for calculation requests")
            print("[backend-agent] press Ctrl+C to exit")

            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop.set)
            await stop.wait()
            print("[backend-agent] shutting down")
        finally:
            await b.close()
    finally:
        shutdown()


async def handle_calc(e: Envelope) -> dict[str, object]:
    payload = e.payload_json()
    if not isinstance(payload, dict):
        raise ValueError("decode request: expected object payload")

    req = CalcRequest(
        a=int(payload.get("a", 0)),
        b=int(payload.get("b", 0)),
        op=str(payload.get("op", "")),
    )

    tracer = trace.get_tracer("backend-agent")
    with tracer.start_as_current_span(
        "backend.calculate",
        attributes={
            "calc.a": req.a,
            "calc.b": req.b,
            "calc.op": req.op,
        },
    ):
        if req.op == "add":
            result = req.a + req.b
        elif req.op == "mul":
            result = req.a * req.b
        else:
            raise ValueError(f"unsupported op: {req.op}")

        print(f"[backend-agent] calculated {req.a} {req.op} {req.b} = {result}")

        return asdict(
            CalcResponse(
                result=result,
                agent="backend-agent",
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
