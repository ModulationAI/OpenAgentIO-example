"""router_agent wires matrix.message.received to matrix.message.send.

In Phase 2 the router-agent starts an ``McpToolBridge`` and uses the MCP repo
tools (``mcp.repo.git_status``, ``mcp.repo.read_file``, ``mcp.repo.grep``) to
collect release-readiness evidence before publishing the final
``matrix.message.send`` event.

In Phase 4 OpenTelemetry tracing is added (opt-in via ``OTEL_ENABLED=1`` or
``OTEL_EXPORTER_OTLP_ENDPOINT``). The router-agent initializes a tracer,
enables the ``OTelTrace`` middleware and ``OTelEnvelopePreparer`` on the Bus,
and creates manual spans around the matrix message handler, each MCP tool
invocation, and the streaming review call.

Run (requires a local NATS server on nats://localhost:4222):

    cd /Users/gubaoer/boyle_lab/learning/openagentio_example
    py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/router_agent/main.py

Run with OTel (requires Jaeger on localhost:4317):

    OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/router_agent/main.py
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from pathlib import Path
from types import TracebackType
from typing import Any

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
    WithSessionPropagation,
    WithTransport,
    dial,
)
from openagentio.bridge import BUILTIN_FACTORIES, BridgeConfig
from openagentio.bridge.runner import BridgeRunner
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

    def record_exception(self, exception: BaseException) -> None:
        return None

    def set_status(self, status: Any) -> None:
        return None

    def set_attribute(self, key: str, value: Any) -> None:
        return None


def _span(
    tracer_name: str,
    name: str,
    *,
    context: Any = None,
    attributes: dict[str, Any] | None = None,
):
    """Create a span when OTel is enabled, otherwise return a no-op context."""
    if not _otel_enabled():
        return _NoOpSpan()
    tracer = trace.get_tracer(tracer_name)
    return tracer.start_as_current_span(
        name,
        context=context,
        attributes=attributes or {},
    )


def _payload(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def compact_text(text: str, max_chars: int = 4000) -> str:
    """Truncate text to ``max_chars`` while preserving head and tail."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    head = text[:half]
    tail = text[-half:]
    return f"{head}\n\n...[truncated {len(text) - max_chars} chars]...\n\n{tail}"


def demo_reply_mode() -> str:
    """Return the Matrix final reply mode for recording."""
    return os.getenv("DEMO_REPLY_MODE", "full").strip().lower()


def demo_pacing_enabled() -> bool:
    """Return True when recording mode should slow down visible stages."""
    return os.getenv("DEMO_PACING", "").strip().lower() in {"1", "true", "yes"}


async def demo_pause(seconds: float) -> None:
    """Sleep only in recording mode."""
    if demo_pacing_enabled():
        await asyncio.sleep(seconds)


def final_reply_text(review_text: str) -> str:
    """Return either the full reviewer output or a short recording-friendly reply."""
    if demo_reply_mode() != "short":
        return review_text or "(empty review)"
    return (
        "Release readiness: Developer Preview.\n"
        "Evidence: README, overview, publicity, roadmap.\n"
        "Trace: Matrix -> OpenAgentIO -> MCP -> SSE -> Matrix."
    )


async def _text_from_result(result: Envelope) -> str:
    payload = result.payload_json()
    if isinstance(payload, dict):
        return str(payload.get("text", ""))
    return str(payload or "")


async def emit_demo_timeline(
    bus: Bus,
    source_env: Envelope,
    stage: str,
    detail: str,
    **extra: object,
) -> None:
    """Publish a recording-only timeline event for director_console."""
    if not demo_pacing_enabled():
        return
    timeline_env = Envelope.new("demo.timeline")
    timeline_env.payload = _payload({"stage": stage, "detail": detail, **extra})
    timeline_env.session_id = source_env.session_id
    timeline_env.conversation_id = source_env.conversation_id
    timeline_env.correlation_id = source_env.correlation_id
    await bus.publish(timeline_env)


async def collect_repo_evidence(
    bus: Bus, room_id: str, source_env: Envelope
) -> dict[str, object]:
    """Call MCP repo tools and return collected evidence."""
    evidence: dict[str, object] = {}

    await emit_demo_timeline(
        bus,
        source_env,
        "bus",
        "router-agent accepted Matrix event; preserving session + trace context",
    )
    await demo_pause(0.45)

    await emit_demo_timeline(
        bus,
        source_env,
        "mcp",
        "invoke mcp.repo.git_status",
        tool="repo.git_status",
    )
    with _span(
        "mcp-tool-bridge",
        "mcp.invoke",
        attributes={"mcp.tool": "repo.git_status", "matrix.room_id": room_id},
    ) as span:
        try:
            status = await bus.invoke("mcp.repo.git_status", {})
            evidence["git_status"] = compact_text(
                await _text_from_result(status), max_chars=4000
            )
        except Exception as exc:
            if _otel_enabled():
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
            evidence["git_status"] = f"failed: {exc}"
    await demo_pause(0.55)

    files = [
        "README.md",
        "prompts/overview.md",
        "prompts/publicity.md",
        "sdk/python/pyproject.toml",
        "ROADMAP.md",
    ]
    for path in files:
        await emit_demo_timeline(
            bus,
            source_env,
            "mcp",
            f"invoke mcp.repo.read_file path={path}",
            tool="repo.read_file",
            path=path,
        )
        with _span(
            "mcp-tool-bridge",
            "mcp.invoke",
            attributes={"mcp.tool": "repo.read_file", "file.path": path},
        ) as span:
            try:
                result = await bus.invoke("mcp.repo.read_file", {"path": path})
                evidence[path] = compact_text(
                    await _text_from_result(result), max_chars=3000
                )
            except Exception as exc:
                if _otel_enabled():
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                evidence[path] = f"failed: {exc}"
        await demo_pause(0.35)

    await emit_demo_timeline(
        bus,
        source_env,
        "mcp",
        "invoke mcp.repo.grep pattern=Envelope pathspec=*.md",
        tool="repo.grep",
    )
    with _span(
        "mcp-tool-bridge",
        "mcp.invoke",
        attributes={
            "mcp.tool": "repo.grep",
            "grep.pattern": "Envelope",
            "grep.pathspec": "*.md",
        },
    ) as span:
        try:
            grep = await bus.invoke(
                "mcp.repo.grep", {"pattern": "Envelope", "pathspec": "*.md"}
            )
            evidence["grep_envelope_md"] = compact_text(
                await _text_from_result(grep), max_chars=4000
            )
        except Exception as exc:
            if _otel_enabled():
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
            evidence["grep_envelope_md"] = f"failed: {exc}"
    await demo_pause(0.55)

    await emit_demo_timeline(
        bus,
        source_env,
        "mcp",
        "repo evidence collected; returning to router-agent",
    )

    return evidence


async def on_message(bus: Bus, env: Envelope) -> None:
    payload = env.payload_json()
    if not isinstance(payload, dict):
        print("[router] received non-object payload", file=sys.stderr)
        return

    room_id = payload.get("room_id", "")
    sender = payload.get("sender", "")
    text = payload.get("text", "")

    with _span(
        "router-agent",
        "router.handle_matrix_message",
        attributes={
            "matrix.room_id": room_id,
            "matrix.sender": sender,
            "acp.session_id": env.session_id,
            "acp.conversation_id": env.conversation_id,
            "acp.correlation_id": env.correlation_id,
        },
    ):
        print(f"[router] received from {sender} in {room_id}: {text!r}")

        async def send_progress(progress_text: str) -> None:
            progress_env = Envelope.new("matrix.message.send")
            progress_env.payload = _payload(
                {"room_id": room_id, "text": progress_text}
            )
            progress_env.session_id = env.session_id
            progress_env.conversation_id = env.conversation_id
            progress_env.correlation_id = env.correlation_id
            await bus.publish(progress_env)
            print(f"[router] progress: {progress_text!r}")

        await send_progress("Received. Inspecting repository...")
        await demo_pause(0.8)

        evidence = await collect_repo_evidence(bus, room_id, env)

        await send_progress("Repo evidence collected. Running streaming review...")
        await demo_pause(0.8)

        review_text = ""
        with _span(
            "router-agent",
            "router.stream_review",
            attributes={"stream.target": "release-reviewer"},
        ) as review_span:
            try:
                await emit_demo_timeline(
                    bus,
                    env,
                    "sse",
                    "stream_invoke release-reviewer with compact repo evidence",
                )
                chunk_count = 0
                async for event in await bus.stream_invoke(
                    "release-reviewer",
                    {"question": text, "evidence": evidence},
                ):
                    event_payload = event.payload_json()
                    if isinstance(event_payload, dict):
                        delta = event_payload.get("delta")
                        if isinstance(delta, str):
                            review_text += delta
                            chunk_count += 1
                            if chunk_count in {1, 3, 6, 9}:
                                await emit_demo_timeline(
                                    bus,
                                    env,
                                    "sse",
                                    f"release-reviewer streamed chunk {chunk_count}",
                                )
            except Exception as exc:
                if _otel_enabled():
                    review_span.record_exception(exc)
                    review_span.set_status(Status(StatusCode.ERROR, str(exc)))
                review_text = f"Streaming review failed: {exc}"
        await emit_demo_timeline(
            bus,
            env,
            "sse",
            "stream completed; router-agent prepares Matrix response",
        )
        await demo_pause(0.5)

        final_env = Envelope.new("matrix.message.send")
        final_env.payload = _payload(
            {"room_id": room_id, "text": final_reply_text(review_text)}
        )
        final_env.session_id = env.session_id
        final_env.conversation_id = env.conversation_id
        final_env.correlation_id = env.correlation_id
        await bus.publish(final_env)
        print(f"[router] published final matrix.message.send to {room_id}")


async def main() -> None:
    shutdown = init_tracer("router-agent") if _otel_enabled() else lambda: None
    agent_id = "router-agent"

    try:
        try:
            tp = await dial(WithNATSName(agent_id))
        except Exception as err:
            print(f"transport: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        bus = Bus.new(
            WithAgentID(agent_id),
            WithTransport(tp),
            WithSessionPropagation(True),
            *_otel_options(),
        )

        # Start the MCP tool bridge so repo tools become Bus invoke targets.
        repo_root = Path(__file__).resolve().parents[5] / "openagentio"
        server_script = (
            Path(__file__).resolve().parent.parent / "mcp_repo_server" / "main.py"
        )
        config = BridgeConfig.from_dict(
            {
                "version": "openagentio.bridge/v1",
                "bridges": [
                    {
                        "name": "mcp-repo",
                        "type": "mcp_tool",
                        "config": {
                            "transport": "stdio",
                            "command": sys.executable,
                            "args": [str(server_script)],
                            "env": {"REPO_ROOT": str(repo_root)},
                            "timeout": 30,
                        },
                        "mappings": {
                            "target_prefix": "mcp.repo",
                        },
                    }
                ],
            }
        )
        runner = BridgeRunner(bus, config, BUILTIN_FACTORIES)

        try:
            await runner.start()
            print("[router] MCP tool bridge started")

            await bus.subscribe(
                "matrix.message.received", lambda env: on_message(bus, env)
            )
            await wait_for_demo_transport(tp)
            print("[router] waiting for matrix.message.received events...")
            print("[router] press Ctrl+C to exit")

            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop.set)
            await stop.wait()
            print("[router] shutting down")
        finally:
            await runner.stop()
            await bus.close()
    finally:
        shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
