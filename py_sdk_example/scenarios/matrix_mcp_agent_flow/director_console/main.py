"""Recording-friendly director console for the Matrix -> MCP -> SSE demo.

The director console is read-only: it subscribes to the same Bus events as the
real flow and prints a compact timeline for screen recording. It does not
publish, invoke, or alter the business path.

Run:

    cd /Users/gubaoer/boyle_lab/learning/openagentio_example
    py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/director_console/main.py
"""

from __future__ import annotations

import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from openagentio import Bus, Envelope, WithAgentID, WithNATSName, WithTransport, dial
from py_sdk_example.internal.common import wait_for_demo_transport


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _short(value: object, max_chars: int = 84) -> str:
    text = str(value or "").replace("\n", " ").strip()
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 1]}..."


def _trace_id(env: Envelope) -> str:
    if env.trace_id:
        return env.trace_id
    if env.traceparent:
        parts = env.traceparent.split("-")
        if len(parts) == 4:
            return parts[1]
    return ""


def _line(stage: str, detail: str) -> None:
    print(f"{_now()}  {stage:<8} {detail}", flush=True)


def _banner(title: str) -> None:
    print("", flush=True)
    print("=" * 78, flush=True)
    print(f"{_now()}  {title}", flush=True)
    print("=" * 78, flush=True)


async def on_inbound(env: Envelope) -> None:
    payload = env.payload_json()
    if not isinstance(payload, dict):
        return
    room = payload.get("room_id", "")
    sender = payload.get("sender", "")
    text = _short(payload.get("text", ""))
    trace_id = _trace_id(env)

    _banner("OPENAGENTIO LIVE PROTOCOL FLOW")
    _line("MATRIX", f"{sender} -> {room}")
    _line("BUS", "event=matrix.message.received transport=nats://127.0.0.1:4222")
    if trace_id:
        _line("TRACE", f"trace_id={trace_id}")
    _line("PROMPT", f'"{text}"')


async def on_outbound(env: Envelope) -> None:
    payload = env.payload_json()
    if not isinstance(payload, dict):
        return
    text = _short(payload.get("text", ""))
    if text.startswith("Received."):
        _line("MATRIX", "progress reply sent -> room")
        return
    if text.startswith("Repo evidence"):
        _line("MATRIX", "evidence progress reply sent -> room")
        return
    _line("MATRIX", "final review sent")
    _line("RESULT", text)


async def on_timeline(env: Envelope) -> None:
    payload = env.payload_json()
    if not isinstance(payload, dict):
        return
    stage = str(payload.get("stage", "DEMO")).upper()[:8]
    detail = _short(payload.get("detail", ""), max_chars=110)
    if detail:
        _line(stage, detail)


async def main() -> None:
    try:
        tp = await dial(WithNATSName("director-console"))
    except Exception as err:
        print(f"transport: {err}", file=sys.stderr)
        raise SystemExit(1) from err

    bus = Bus.new(
        WithAgentID("director-console"),
        WithTransport(tp),
    )

    try:
        await bus.subscribe("matrix.message.received", on_inbound)
        await bus.subscribe("matrix.message.send", on_outbound)
        await bus.subscribe("demo.timeline", on_timeline)
        await wait_for_demo_transport(tp)
        print(
            "[director] waiting for Matrix -> OpenAgentIO -> MCP -> SSE -> Matrix events...",
            flush=True,
        )

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        await stop.wait()
    finally:
        await bus.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
