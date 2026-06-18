"""client sends a calculation request to gateway-agent and prints the trace.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/otel_tracing/client/main.py
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from opentelemetry import trace

from openagentio import (
    Bus,
    OTelEnvelopePreparer,
    WithAgentID,
    WithEnvelopePreparer,
    WithNATSName,
    WithTimeout,
    WithTransport,
    dial,
)
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
    shutdown = init_tracer("otel-client")

    try:
        tracer = trace.get_tracer("otel-client")
        with tracer.start_as_current_span(
            "client.calc-request",
            attributes={
                "calc.a": 14,
                "calc.b": 3,
                "calc.op": "add",
            },
        ) as span:
            span_context = span.get_span_context()
            if span_context.is_valid:
                print(f"[client] TraceID: {span_context.trace_id:032x}")

            try:
                tp = await dial(WithNATSName("otel-client"))
            except Exception as err:
                print(f"transport: {err}", file=sys.stderr)
                raise SystemExit(1) from err

            b = Bus.new(
                WithAgentID("otel-client"),
                WithTransport(tp),
                WithEnvelopePreparer(
                    OTelEnvelopePreparer(),
                ),
            )

            try:
                req = CalcRequest(a=14, b=3, op="add")
                print(f"[client] invoking gateway-agent with {req.a} {req.op} {req.b}")

                try:
                    resp = await b.invoke(
                        "gateway-agent",
                        asdict(req),
                        WithTimeout(5),
                    )
                except Exception as err:
                    span.record_exception(err)
                    print(f"invoke failed: {err}", file=sys.stderr)
                    raise SystemExit(1) from err

                payload = resp.payload_json()
                if not isinstance(payload, dict):
                    print("decode response: expected object payload", file=sys.stderr)
                    raise SystemExit(1)

                result = CalcResponse(
                    result=int(payload.get("result", 0)),
                    agent=str(payload.get("agent", "")),
                )
                print(f"[client] result={result.result} handled_by={result.agent}")
                print("[client] open http://localhost:16686 and search by TraceID to view the trace")
            finally:
                await b.close()
    finally:
        shutdown()


if __name__ == "__main__":
    asyncio.run(main())
