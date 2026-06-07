"""worker_agent accepts tasks and publishes completion events later.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/async_task/worker_agent/main.py
"""
from __future__ import annotations

import asyncio
import json
import signal
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from openagentio import (
    Bus,
    Envelope,
    Recover,
    TaskCompleted as TaskCompletedEvent,
    Trace,
    WithAgentID,
    WithMiddleware,
    WithNATSName,
    WithTransport,
    dial,
)
from py_sdk_example.internal.common import wait_for_demo_transport


@dataclass
class TaskRequest:
    input: str


@dataclass
class TaskAccepted:
    task_id: str
    status: str


@dataclass
class TaskCompleted:
    task_id: str
    result: str


async def main() -> None:
    agent_id = "task-worker"

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
            await b.handle_invoke("task-worker", lambda e: handle_task(b, tp, e))
        except Exception as err:
            print(f"register task-worker: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        try:
            await wait_for_demo_transport(tp)
        except Exception as err:
            print(f"wait for handler: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        print("[task-worker] listening for async tasks")
        print("[task-worker] start the client in another terminal:")
        print("  py_sdk_example/.venv/bin/python py_sdk_example/scenarios/async_task/task_agent/main.py")
        print("[task-worker] press Ctrl+C to exit")

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        await stop.wait()
        print("[task-worker] shutting down")
    finally:
        await b.close()


async def handle_task(b: Bus, tp: object, e: Envelope) -> dict[str, str]:
    payload = e.payload_json()
    if not isinstance(payload, dict):
        raise ValueError("decode task request: expected object payload")

    req = TaskRequest(input=str(payload.get("input", "")))
    task_id = e.event_id
    print(f"\n[task-worker] accepted task {task_id}: {req.input}")

    asyncio.create_task(complete_task(b, tp, task_id, req))

    return asdict(
        TaskAccepted(
            task_id=task_id,
            status="accepted",
        )
    )


async def complete_task(
    b: Bus,
    tp: object,
    task_id: str,
    req: TaskRequest,
) -> None:
    await asyncio.sleep(1.5)

    done = TaskCompleted(
        task_id=task_id,
        result="finished: " + req.input,
    )

    env = Envelope.new(TaskCompletedEvent)
    env.from_ = "task-worker"
    env.correlation_id = task_id
    env.payload = json.dumps(asdict(done), separators=(",", ":")).encode("utf-8")

    try:
        await b.publish(env)
    except Exception as err:
        print(f"publish completed event: {err}", file=sys.stderr)
        return

    try:
        await wait_for_demo_transport(tp)
    except Exception as err:
        print(f"wait for completed event: {err}", file=sys.stderr)
        return

    print(f"[task-worker] completed task {task_id}")


if __name__ == "__main__":
    asyncio.run(main())
