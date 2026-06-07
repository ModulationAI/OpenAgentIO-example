"""task_agent submits a task and waits for its completion event.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/async_task/task_agent/main.py
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from openagentio import (
    Bus,
    Envelope,
    Recover,
    Subscription,
    TaskCompleted as TaskCompletedEvent,
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
    agent_id = "task-client"

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

    completed: asyncio.Queue[TaskCompleted] = asyncio.Queue(maxsize=8)
    sub: Subscription | None = None
    try:
        try:
            sub = await b.subscribe(
                TaskCompletedEvent,
                lambda e: handle_completed(e, completed),
            )
        except Exception as err:
            print(f"subscribe: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        try:
            await wait_for_demo_transport(tp)
        except Exception as err:
            print(f"wait for subscription: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        req = TaskRequest(input="generate a short report")

        print("[task-client] submitting task to task-worker")
        print(f"[task-client] input: {req.input}")

        try:
            resp = await b.invoke("task-worker", asdict(req), WithTimeout(10))
        except Exception as err:
            print(f"submit task failed: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        payload = resp.payload_json()
        if not isinstance(payload, dict):
            print("decode accepted response: expected object payload", file=sys.stderr)
            raise SystemExit(1)

        accepted = TaskAccepted(
            task_id=str(payload.get("task_id", "")),
            status=str(payload.get("status", "")),
        )
        print(f"[task-client] accepted: task_id={accepted.task_id} status={accepted.status}")
        print("[task-client] waiting for completion event")

        try:
            while True:
                done = await asyncio.wait_for(completed.get(), timeout=10)
                if done.task_id != accepted.task_id:
                    continue
                print(
                    f"[task-client] completed: task_id={done.task_id} result={done.result}"
                )
                return
        except asyncio.TimeoutError:
            print("timed out waiting for task completion", file=sys.stderr)
            raise SystemExit(1) from None
    finally:
        if sub is not None:
            await sub.unsubscribe()
        await b.close()


async def handle_completed(
    e: Envelope,
    completed: asyncio.Queue[TaskCompleted],
) -> None:
    payload = e.payload_json()
    if not isinstance(payload, dict):
        raise ValueError("decode completed event: expected object payload")

    done = TaskCompleted(
        task_id=str(payload.get("task_id", "")),
        result=str(payload.get("result", "")),
    )
    await completed.put(done)


if __name__ == "__main__":
    asyncio.run(main())
