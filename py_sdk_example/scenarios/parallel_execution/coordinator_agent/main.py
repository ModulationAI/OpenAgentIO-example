"""coordinator_agent invokes multiple worker targets in parallel and combines their results.

Run:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/parallel_execution/coordinator_agent/main.py
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict, dataclass

from openagentio import (
    Bus,
    Recover,
    Trace,
    WithAgentID,
    WithMiddleware,
    WithNATSName,
    WithTimeout,
    WithTransport,
    dial,
)


@dataclass
class AnalyzeRequest:
    text: str


@dataclass
class AnalysisResult:
    agent: str
    text: str


async def main() -> None:
    agent_id = "coordinator-agent"

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
        req = AnalyzeRequest(
            text="OpenAgentIO helps agents communicate with each other.",
        )
        targets = ["summary-agent", "sentiment-agent", "keywords-agent"]

        print("[coordinator-agent] invoking workers in parallel")
        print(f"[coordinator-agent] input: {req.text}")

        tasks = [invoke_worker(b, target, req) for target in targets]
        try:
            results = await asyncio.gather(*tasks)
        except Exception as err:
            print(str(err), file=sys.stderr)
            raise SystemExit(1) from err

        summary = {result.agent: result.text for result in results}

        print("[coordinator-agent] combined result:")
        for target in targets:
            print(f"  {target}: {summary[target]}")
    finally:
        await b.close()


async def invoke_worker(
    b: Bus,
    target: str,
    req: AnalyzeRequest,
) -> AnalysisResult:
    try:
        resp = await b.invoke(target, asdict(req), WithTimeout(10))
    except Exception as err:
        raise RuntimeError(f"{target} failed: {err}") from err

    payload = resp.payload_json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"{target} failed: decode response: expected object payload")

    return AnalysisResult(
        agent=str(payload.get("agent", "")),
        text=str(payload.get("text", "")),
    )


if __name__ == "__main__":
    asyncio.run(main())
