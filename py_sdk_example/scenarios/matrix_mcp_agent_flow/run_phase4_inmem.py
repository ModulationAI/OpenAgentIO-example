"""Local InMemory runner for Phase 4 No-Matrix Core Flow + MCP + SSE + OTel.

This script runs the entire Phase 4 flow in a single process using the
InMemory transport, so no NATS server is required. It initializes an
OpenTelemetry tracer and sends spans to Jaeger (if running on
localhost:4317). Because everything runs in one process, the service name is
``phase4-local-runner``; use the distributed NATS setup to see separate
service names in Jaeger.

Run (Jaeger is optional for this local runner):

    cd /Users/gubaoer/boyle_lab/learning/openagentio_example
    py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/run_phase4_inmem.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from opentelemetry import trace

from openagentio import (
    Bus,
    Envelope,
    InMemoryDriver,
    OTelEnvelopePreparer,
    OTelTrace,
    StreamWriter,
    WithAgentID,
    WithEnvelopePreparer,
    WithMiddleware,
    WithSessionPropagation,
    WithTransport,
)
from openagentio.bridge import BUILTIN_FACTORIES, BridgeConfig
from openagentio.bridge.runner import BridgeRunner
from py_sdk_example.internal.common import wait_for_demo_transport
from py_sdk_example.internal.otel import init_tracer


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


async def _text_from_result(result: Envelope) -> str:
    payload = result.payload_json()
    if isinstance(payload, dict):
        return str(payload.get("text", ""))
    return str(payload or "")


async def collect_repo_evidence(bus: Bus) -> dict[str, object]:
    evidence: dict[str, object] = {}
    tracer = trace.get_tracer("mcp-tool-bridge")

    with tracer.start_as_current_span(
        "mcp.invoke", attributes={"mcp.tool": "repo.git_status"}
    ):
        try:
            status = await bus.invoke("mcp.repo.git_status", {})
            evidence["git_status"] = compact_text(
                await _text_from_result(status), max_chars=4000
            )
        except Exception as exc:
            evidence["git_status"] = f"failed: {exc}"

    files = [
        "README.md",
        "prompts/overview.md",
        "prompts/publicity.md",
        "sdk/python/pyproject.toml",
        "ROADMAP.md",
    ]
    for path in files:
        with tracer.start_as_current_span(
            "mcp.invoke",
            attributes={"mcp.tool": "repo.read_file", "file.path": path},
        ):
            try:
                result = await bus.invoke("mcp.repo.read_file", {"path": path})
                evidence[path] = compact_text(
                    await _text_from_result(result), max_chars=3000
                )
            except Exception as exc:
                evidence[path] = f"failed: {exc}"

    with tracer.start_as_current_span(
        "mcp.invoke",
        attributes={
            "mcp.tool": "repo.grep",
            "grep.pattern": "Envelope",
            "grep.pathspec": "*.md",
        },
    ):
        try:
            grep = await bus.invoke(
                "mcp.repo.grep", {"pattern": "Envelope", "pathspec": "*.md"}
            )
            evidence["grep_envelope_md"] = compact_text(
                await _text_from_result(grep), max_chars=4000
            )
        except Exception as exc:
            evidence["grep_envelope_md"] = f"failed: {exc}"

    return evidence


async def reviewer(env: Envelope, writer: StreamWriter) -> None:
    """Mock-backed streaming reviewer with OTel span."""
    tracer = trace.get_tracer("sse-reviewer")
    with tracer.start_as_current_span(
        "sse-reviewer.generate",
        attributes={
            "stream.target": "release-reviewer",
            "acp.session_id": env.session_id,
            "acp.conversation_id": env.conversation_id,
        },
    ):
        payload = env.payload_json()
        if not isinstance(payload, dict):
            await writer.error({"message": "expected JSON object payload"})
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


async def on_message(bus: Bus, env: Envelope) -> None:
    payload = env.payload_json()
    if not isinstance(payload, dict):
        return

    room_id = payload.get("room_id", "")
    sender = payload.get("sender", "")
    text = payload.get("text", "")

    tracer = trace.get_tracer("router-agent")
    with tracer.start_as_current_span(
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

        evidence = await collect_repo_evidence(bus)

        await send_progress(
            "Repo evidence collected. Running streaming review..."
        )

        review_text = ""
        with tracer.start_as_current_span(
            "router.stream_review",
            attributes={"stream.target": "release-reviewer"},
        ):
            try:
                async for event in await bus.stream_invoke(
                    "release-reviewer",
                    {"question": text, "evidence": evidence},
                ):
                    event_payload = event.payload_json()
                    if isinstance(event_payload, dict):
                        delta = event_payload.get("delta")
                        if isinstance(delta, str):
                            review_text += delta
            except Exception as exc:
                review_text = f"Streaming review failed: {exc}"

        final_env = Envelope.new("matrix.message.send")
        final_env.payload = _payload(
            {"room_id": room_id, "text": review_text or "(empty review)"}
        )
        final_env.session_id = env.session_id
        final_env.conversation_id = env.conversation_id
        final_env.correlation_id = env.correlation_id
        await bus.publish(final_env)
        print(f"[router] published final matrix.message.send to {room_id}")


async def on_sink(env: Envelope) -> None:
    payload = env.payload_json()
    if not isinstance(payload, dict):
        return
    print("[matrix_sink] --- matrix.message.send ---")
    print(f"[matrix_sink] room_id={payload.get('room_id', '')}")
    print(f"[matrix_sink] text={payload.get('text', '')!r}")
    print(f"[matrix_sink] session_id={env.session_id}")
    print(f"[matrix_sink] conversation_id={env.conversation_id}")
    print(f"[matrix_sink] correlation_id={env.correlation_id}")


async def main() -> None:
    # Phase 4 is explicitly about OTel tracing, so enable it by default.
    # Users can still override the endpoint via OTEL_EXPORTER_OTLP_ENDPOINT.
    os.environ.setdefault("OTEL_ENABLED", "1")
    shutdown = init_tracer("phase4-local-runner")

    try:
        bus = Bus.new(
            WithAgentID("phase4-local-runner"),
            WithTransport(InMemoryDriver()),
            WithMiddleware(
                OTelTrace(),
            ),
            WithEnvelopePreparer(
                OTelEnvelopePreparer(),
            ),
            WithSessionPropagation(True),
        )
        await bus.connect()

        # Start the MCP tool bridge.
        repo_root = Path(__file__).resolve().parents[4] / "openagentio"
        server_script = (
            Path(__file__).resolve().parent / "mcp_repo_server" / "main.py"
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
        await runner.start()
        print("[phase4] MCP tool bridge started")

        try:
            await bus.handle_stream("release-reviewer", reviewer)
            await bus.subscribe("matrix.message.send", on_sink)
            await bus.subscribe(
                "matrix.message.received", lambda env: on_message(bus, env)
            )

            room_id = "!demo:localhost"
            sender = "@admin:localhost"
            event_id = f"${uuid.uuid4()}"
            prompt = (
                "@openagentio inspect this repo and tell me whether it is ready "
                "for public release."
            )

            tracer = trace.get_tracer("send-demo-prompt")
            with tracer.start_as_current_span(
                "send_demo_prompt.publish",
                attributes={
                    "matrix.room_id": room_id,
                    "matrix.sender": sender,
                    "matrix.event_id": event_id,
                },
            ) as span:
                prompt_env = Envelope.new("matrix.message.received")
                prompt_env.payload = _payload(
                    {
                        "text": prompt,
                        "html": None,
                        "room_id": room_id,
                        "sender": sender,
                        "event_id": event_id,
                        "origin_server_ts": 0,
                        "msgtype": "m.text",
                    }
                )
                prompt_env.session_id = room_id
                prompt_env.conversation_id = room_id
                prompt_env.correlation_id = event_id
                await bus.publish(prompt_env)
                trace_id = span.get_span_context().trace_id
                print(
                    f"[demo-prompt] published matrix.message.received "
                    f"event_id={event_id} trace_id={trace_id:032x}"
                )

            await wait_for_demo_transport(bus._transport)
            # Give the streaming reviewer time to emit all deltas.
            await asyncio.sleep(8)
        finally:
            await runner.stop()
            await bus.close()
    finally:
        shutdown()


if __name__ == "__main__":
    asyncio.run(main())
