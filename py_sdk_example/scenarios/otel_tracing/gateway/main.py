"""gateway-agent receives calculation requests and delegates to backend-agent.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/otel_tracing/gateway/main.py
"""
from __future__ import annotations

import asyncio
import signal
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

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
    WithTimeout,
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
    shutdown = init_tracer("gateway-agent")
    agent_id = "gateway-agent"

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
                await b.handle_invoke("gateway-agent", lambda e: handle_gateway(b, e))
            except Exception as err:
                print(f"register gateway-agent: {err}", file=sys.stderr)
                raise SystemExit(1) from err

            try:
                await wait_for_demo_transport(tp)
            except Exception as err:
                print(f"wait for handlers: {err}", file=sys.stderr)
                raise SystemExit(1) from err

            print("[gateway-agent] listening for calculation requests")
            print("[gateway-agent] will delegate to backend-agent")
            print("[gateway-agent] press Ctrl+C to exit")

            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop.set)
            await stop.wait()
            print("[gateway-agent] shutting down")
        finally:
            await b.close()
    finally:
        shutdown()


async def handle_gateway(b: Bus, e: Envelope) -> dict[str, object]:
    payload = e.payload_json()
    if not isinstance(payload, dict):
        raise ValueError("decode request: expected object payload")

    req = CalcRequest(
        a=int(payload.get("a", 0)),
        b=int(payload.get("b", 0)),
        op=str(payload.get("op", "")),
    )

    tracer = trace.get_tracer("gateway-agent")
    with tracer.start_as_current_span(
        "gateway.delegate",
        attributes={
            "calc.a": req.a,
            "calc.b": req.b,
            "calc.op": req.op,
        },
    ) as span:
        print(f"[gateway-agent] delegating {req.a} {req.op} {req.b} to backend-agent")

        try:
            resp = await b.invoke(
                "backend-agent",
                asdict(req),
                WithTimeout(5),
            )
        except Exception as err:
            span.record_exception(err)
            span.set_status(Status(StatusCode.ERROR, str(err)))
            raise RuntimeError(f"delegate to backend-agent failed: {err}") from err

        payload = resp.payload_json()
        if not isinstance(payload, dict):
            raise ValueError("decode backend response: expected object payload")

        result = CalcResponse(
            result=int(payload.get("result", 0)),
            agent=str(payload.get("agent", "")),
        )
        result.agent = "gateway-agent -> " + result.agent
        return asdict(result)


if __name__ == "__main__":
    asyncio.run(main())
