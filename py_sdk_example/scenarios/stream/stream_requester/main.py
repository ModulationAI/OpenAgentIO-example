"""stream_requester sends a streaming request to stream-responder.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/stream/stream_requester/main.py
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict, dataclass

from openagentio import (
    Bus,
    Recover,
    ResponseDelta,
    ResponseFinal,
    Trace,
    WithAgentID,
    WithIdleTimeout,
    WithMiddleware,
    WithNATSName,
    WithTimeout,
    WithTransport,
    dial,
)


@dataclass
class Prompt:
    text: str


async def main() -> None:
    agent_id = "stream-requester"

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
        prompt = Prompt(text="stream a short greeting")

        print("[stream-requester] invoking stream-responder")
        print(f"[stream-requester] prompt: {prompt.text}")

        try:
            stream = await b.stream_invoke(
                "stream-responder",
                asdict(prompt),
                WithTimeout(15),
                WithIdleTimeout(3),
            )
        except Exception as err:
            print(f"stream invoke failed: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        try:
            print("[stream-requester] response: ", end="", flush=True)
            async for frame in stream:
                if frame.event_type == ResponseDelta:
                    payload = frame.payload_json()
                    if not isinstance(payload, dict):
                        print("\ndecode delta: expected object payload", file=sys.stderr)
                        raise SystemExit(1)
                    print(str(payload.get("delta", "")), end="", flush=True)
                elif frame.event_type == ResponseFinal:
                    payload = frame.payload.decode("utf-8") if frame.payload else "null"
                    print()
                    print(f"[stream-requester] final payload: {payload}")
        except Exception as err:
            print(f"\nstream error: {err}", file=sys.stderr)
            raise SystemExit(1) from err
        finally:
            await stream.close()
    finally:
        await b.close()


if __name__ == "__main__":
    asyncio.run(main())
