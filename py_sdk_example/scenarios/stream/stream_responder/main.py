"""stream_responder handles streaming requests and sends response chunks.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/stream/stream_responder/main.py
"""
from __future__ import annotations

import asyncio
import signal
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from openagentio import (
    Bus,
    Envelope,
    Recover,
    StreamWriter,
    Trace,
    WithAgentID,
    WithMiddleware,
    WithNATSName,
    WithTransport,
    dial,
)
from py_sdk_example.internal.common import wait_for_demo_transport


@dataclass
class Prompt:
    text: str


async def main() -> None:
    agent_id = "stream-responder"

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
            await b.handle_stream("stream-responder", handle_prompt)
        except Exception as err:
            print(f"register stream handler: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        try:
            await wait_for_demo_transport(tp)
        except Exception as err:
            print(f"wait for handler: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        print("[stream-responder] listening for streaming calls")
        print("[stream-responder] start the requester in another terminal:")
        print("  py_sdk_example/.venv/bin/python py_sdk_example/scenarios/stream/stream_requester/main.py")
        print("[stream-responder] press Ctrl+C to exit")

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        await stop.wait()
        print("[stream-responder] shutting down")
    finally:
        await b.close()


async def handle_prompt(e: Envelope, w: StreamWriter) -> None:
    payload = e.payload_json()
    if not isinstance(payload, dict):
        raise ValueError("decode prompt: expected object payload")

    prompt = Prompt(text=str(payload.get("text", "")))
    print(f"\n[stream-responder] prompt from {e.from_}: {prompt.text}")

    await w.started({"meta": {"agent": "stream-responder"}})

    chunks = ["hello ", "from ", "stream-responder"]
    for chunk in chunks:
        await w.delta({"delta": chunk})
        await asyncio.sleep(0.2)

    await w.final({"result": {"text": "hello from stream-responder"}})


if __name__ == "__main__":
    asyncio.run(main())
