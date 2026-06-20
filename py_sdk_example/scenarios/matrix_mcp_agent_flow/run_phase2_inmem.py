"""Local InMemory runner for Phase 2 No-Matrix Core Flow + MCP tools.

This script runs the entire Phase 2 flow in a single process using the
InMemory transport, so no NATS server is required. It:

1. Starts the MCP repo tool bridge.
2. Subscribes to ``matrix.message.send`` (matrix sink).
3. Subscribes to ``matrix.message.received`` (router-agent).
4. Publishes a fake Matrix inbound event.
5. The router-agent calls MCP repo tools and publishes progress + final messages.

Run:

    cd /Users/gubaoer/boyle_lab/learning/openagentio_example
    py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/run_phase2_inmem.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from openagentio import (
    Bus,
    Envelope,
    InMemoryDriver,
    WithAgentID,
    WithSessionPropagation,
    WithTransport,
)
from openagentio.bridge import BUILTIN_FACTORIES, BridgeConfig
from openagentio.bridge.runner import BridgeRunner
from py_sdk_example.internal.common import wait_for_demo_transport


def _payload(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def compact_text(text: str, max_chars: int = 4000) -> str:
    """Truncate text to ``max_chars`` while preserving head and tail.

    Keeps each evidence item within the 2-4KB recommendation before it is
    passed to the streaming reviewer in Phase 3.
    """
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

    try:
        status = await bus.invoke("mcp.repo.git_status", {})
        evidence["git_status"] = await _text_from_result(status)
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
        try:
            result = await bus.invoke("mcp.repo.read_file", {"path": path})
            evidence[path] = compact_text(await _text_from_result(result), max_chars=3000)
        except Exception as exc:
            evidence[path] = f"failed: {exc}"

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


async def on_message(bus: Bus, env: Envelope) -> None:
    payload = env.payload_json()
    if not isinstance(payload, dict):
        return

    room_id = payload.get("room_id", "")
    sender = payload.get("sender", "")
    text = payload.get("text", "")

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

    await send_progress("Repo evidence collected. Running streaming review...")

    git_status = str(evidence.get("git_status", "unknown"))
    grep_lines = str(evidence.get("grep_envelope_md", "")).splitlines()
    summary = (
        "Release readiness: developer-preview ready.\n\n"
        "Evidence:\n"
        f"- Git status: {git_status}\n"
        "- Files inspected: README.md, prompts/overview.md, prompts/publicity.md, "
        "sdk/python/pyproject.toml, ROADMAP.md\n"
        f"- Grep 'Envelope' in *.md: {len(grep_lines)} line(s)\n\n"
        "Remaining:\n"
        "- Add SSE streaming reviewer (Phase 3)\n"
        "- Add real Matrix bridge (Phase 4)\n"
        "- Add OTel end-to-end trace (Phase 5)"
    )

    final_env = Envelope.new("matrix.message.send")
    final_env.payload = _payload({"room_id": room_id, "text": summary})
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
    bus = Bus.new(
        WithAgentID("phase2-local-runner"),
        WithTransport(InMemoryDriver()),
        WithSessionPropagation(True),
    )
    await bus.connect()

    # Start the MCP tool bridge.
    repo_root = Path(__file__).resolve().parents[4] / "openagentio"
    server_script = Path(__file__).resolve().parent / "mcp_repo_server" / "main.py"
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
    print("[phase2] MCP tool bridge started")

    try:
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
        print(f"[demo-prompt] published matrix.message.received event_id={event_id}")

        await wait_for_demo_transport(bus._transport)
        # Give handlers and MCP subprocess a moment to finish before exiting.
        await asyncio.sleep(1)
    finally:
        await runner.stop()
        await bus.close()


if __name__ == "__main__":
    asyncio.run(main())
