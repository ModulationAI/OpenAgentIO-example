"""sse_agent provides a stable, mock-backed streaming reviewer.

Registers the ``release-reviewer`` stream target. The reviewer consumes
repo evidence produced by the router-agent and emits a deterministic,
chunked analysis suitable for recording. Output is roughly 60% fixed
template and 40% dynamic based on evidence file names, git status, and
grep results.

In Phase 4 OpenTelemetry tracing is added (opt-in via ``OTEL_ENABLED=1`` or
``OTEL_EXPORTER_OTLP_ENDPOINT``).

Run (requires a local NATS server on nats://localhost:4222):

    cd /Users/gubaoer/boyle_lab/learning/openagentio_example
    py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/sse_agent/main.py

Run with OTel (requires Jaeger on localhost:4317):

    OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/sse_agent/main.py
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path
from types import TracebackType
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from opentelemetry import trace

from openagentio import (
    Bus,
    Envelope,
    OTelEnvelopePreparer,
    OTelTrace,
    Recover,
    StreamWriter,
    WithAgentID,
    WithEnvelopePreparer,
    WithMiddleware,
    WithNATSName,
    WithTransport,
    dial,
)
from py_sdk_example.internal.common import wait_for_demo_transport
from py_sdk_example.internal.otel import init_tracer


def _otel_enabled() -> bool:
    """Return True when the user explicitly enables OTel tracing."""
    return os.getenv("OTEL_ENABLED", "") == "1" or bool(
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    )


def _otel_options():
    """Return Bus options for OTel when enabled, otherwise an empty list."""
    if not _otel_enabled():
        return []
    return [
        WithMiddleware(
            Recover(),
            OTelTrace(),
        ),
        WithEnvelopePreparer(
            OTelEnvelopePreparer(),
        ),
    ]


class _NoOpSpan:
    """Context manager that satisfies the span API used by this script."""

    def __enter__(self) -> "_NoOpSpan":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return None

    def set_status(self, status: Any) -> None:
        return None

    def set_attribute(self, key: str, value: Any) -> None:
        return None


def _span(
    tracer_name: str,
    name: str,
    *,
    attributes: dict[str, Any] | None = None,
):
    """Create a span when OTel is enabled, otherwise return a no-op context."""
    if not _otel_enabled():
        return _NoOpSpan()
    tracer = trace.get_tracer(tracer_name)
    return tracer.start_as_current_span(
        name,
        attributes=attributes or {},
    )


async def reviewer(env: Envelope, writer: StreamWriter) -> None:
    with _span(
        "sse-reviewer",
        "sse-reviewer.generate",
        attributes={
            "stream.target": "release-reviewer",
            "acp.session_id": env.session_id,
            "acp.conversation_id": env.conversation_id,
        },
    ) as span:
        payload = env.payload_json()
        if not isinstance(payload, dict):
            await writer.error({"message": "expected JSON object payload"})
            if _otel_enabled():
                span.set_status(trace.Status(trace.StatusCode.ERROR, "bad payload"))
            return

        question = str(payload.get("question", ""))
        evidence = payload.get("evidence", {})
        if not isinstance(evidence, dict):
            evidence = {}

        git_status = str(evidence.get("git_status", "unknown"))
        files = [
            "README.md",
            "prompts/overview.md",
            "prompts/publicity.md",
            "sdk/python/pyproject.toml",
            "ROADMAP.md",
        ]
        present_files = [
            name for name in files if isinstance(evidence.get(name), str)
        ]
        file_list = ", ".join(present_files) if present_files else "selected files"

        grep_result = str(evidence.get("grep_envelope_md", ""))
        grep_count = len(
            [line for line in grep_result.splitlines() if line.strip()]
        )

        if _otel_enabled():
            span.set_attribute("review.git_status", git_status)
            span.set_attribute("review.grep_count", grep_count)
            span.set_attribute("review.file_count", len(present_files))

        await writer.started(
            {
                "meta": {
                    "agent": "release-reviewer",
                    "question": question,
                    "evidence_files": present_files,
                    "git_status": git_status,
                }
            }
        )

        chunks = [
            f"Based on the evidence collected from {file_list}, ",
            "the OpenAgentIO project is currently in a developer-preview state. ",
            "Matrix room messages can enter the Bus as events through the MatrixEventBridge, ",
            "MCP server tools can be exposed as native invoke targets through the McpToolBridge, ",
            "and streaming agents can be wired in as SSE stream targets. ",
            "Session identifiers and W3C trace context propagate across all three bridges, ",
            "so a single Matrix message can trigger MCP tool calls and an SSE stream "
            "while preserving one trace. ",
            f"Git status reports '{git_status}', "
            f"and grep found {grep_count} references to 'Envelope' in markdown files. ",
            "Conclusion: the repository is ready for a controlled public release announcement, "
            "provided the documentation clearly states the developer-preview boundaries.",
        ]

        # Fixed pacing for stable recording.
        delays = [0.45, 0.42, 0.48, 0.40, 0.44, 0.46, 0.41, 0.43, 0.47]
        for i, chunk in enumerate(chunks):
            await writer.delta({"delta": chunk})
            await asyncio.sleep(delays[i % len(delays)])

        await writer.final(
            {
                "result": {
                    "verdict": "developer-preview ready",
                    "git_status": git_status,
                    "envelope_refs_in_md": grep_count,
                }
            }
        )


async def main() -> None:
    shutdown = init_tracer("sse-reviewer") if _otel_enabled() else lambda: None
    agent_id = "sse-reviewer"

    try:
        try:
            tp = await dial(WithNATSName(agent_id))
        except Exception as err:
            print(f"transport: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        bus = Bus.new(
            WithAgentID(agent_id),
            WithTransport(tp),
            *_otel_options(),
        )

        try:
            await bus.handle_stream("release-reviewer", reviewer)
            await wait_for_demo_transport(tp)
            print("[sse-reviewer] registered release-reviewer stream target")
            print("[sse-reviewer] press Ctrl+C to exit")

            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop.set)
            await stop.wait()
            print("[sse-reviewer] shutting down")
        finally:
            await bus.close()
    finally:
        shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
