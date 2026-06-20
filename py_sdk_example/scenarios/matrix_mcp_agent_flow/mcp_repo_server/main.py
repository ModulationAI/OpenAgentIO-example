"""Minimal MCP stdio server exposing repository tools for the Matrix/MCP demo.

Run directly for manual testing:

    REPO_ROOT=/path/to/openagentio \
        /Users/gubaoer/boyle_lab/learning/openagentio_example/py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/mcp_repo_server/main.py

The server reads the repository rooted at ``REPO_ROOT`` (defaulting to the
OpenAgentIO main repository next to this example repo).

In Phase 4 OpenTelemetry tracing is added. The server initializes its own
``mcp-repo-server`` tracer and extracts the W3C ``traceparent`` from the
JSON-RPC ``_meta`` field so MCP tool spans join the same trace as the
OpenAgentIO router-agent.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

server = Server("openagentio-demo-repo-server")


def _otel_enabled() -> bool:
    """Return True when the user explicitly enables OTel tracing."""
    return os.getenv("OTEL_ENABLED", "") == "1" or bool(
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    )


def init_tracer() -> TracerProvider:
    """Initialize the MCP repo server tracer."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider = TracerProvider(
        resource=Resource.create({"service.name": "mcp-repo-server"})
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider


def maybe_init_tracer() -> TracerProvider | None:
    """Initialize tracer only when OTel is explicitly enabled."""
    if not _otel_enabled():
        return None
    return init_tracer()


def maybe_shutdown(provider: TracerProvider | None) -> None:
    if provider is not None:
        shutdown(provider)


def shutdown(provider: TracerProvider) -> None:
    provider.force_flush()
    provider.shutdown()


def current_trace_context():
    """Extract W3C trace context from the MCP request _meta, if present."""
    try:
        meta = server.request_context.meta
    except LookupError:
        return None
    if meta is None:
        return None
    meta_dict = meta.model_dump()
    traceparent = meta_dict.get("traceparent")
    if not traceparent:
        return None
    return TraceContextTextMapPropagator().extract({"traceparent": traceparent})


def repo_root() -> Path:
    """Return the resolved repository root used by all repo tools."""
    # main.py is inside mcp_repo_server/, so parents[5] reaches .../learning.
    default = Path(__file__).resolve().parents[5] / "openagentio"
    return Path(os.getenv("REPO_ROOT", default)).resolve()


def run_git(
    *args: str,
    cwd: Path | None = None,
    ok_rc: set[int] | None = None,
) -> str:
    """Run a git command in the repo and return stripped stdout."""
    accepted = ok_rc if ok_rc is not None else {0}
    result = subprocess.run(
        ["git", *args],
        cwd=cwd or repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in accepted:
        stderr = result.stderr.strip()
        raise RuntimeError(
            f"git {' '.join(args)} failed with rc={result.returncode}: {stderr}"
        )
    return result.stdout.strip()


def read_repo_file(path: str) -> str:
    """Read a text file inside the repo root, rejecting path traversal."""
    root = repo_root()
    target = (root / path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path escapes repo root: {path}") from exc
    if not target.exists():
        raise FileNotFoundError(f"No such file in repo: {path}")
    return target.read_text(encoding="utf-8", errors="replace")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="git_status",
            description="Return 'git status --short' for the repository",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="read_file",
            description="Read a text file relative to the repository root",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Repository-relative file path",
                    }
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="grep",
            description="Run 'git grep -n <pattern>' with an optional pathspec",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Grep pattern",
                    },
                    "pathspec": {
                        "type": "string",
                        "description": "Optional pathspec, e.g. '*.go' or '*.md'",
                    },
                },
                "required": ["pattern"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, object]
) -> list[types.TextContent]:
    tracer = trace.get_tracer("mcp-repo-server")
    ctx = current_trace_context()

    if name == "git_status":
        with tracer.start_as_current_span(
            "mcp.repo.git_status",
            context=ctx,
            attributes={"mcp.tool": "repo.git_status"},
        ):
            status = run_git("status", "--short")
            return [types.TextContent(type="text", text=status or "clean")]

    if name == "read_file":
        path = str(arguments.get("path", ""))
        with tracer.start_as_current_span(
            "mcp.repo.read_file",
            context=ctx,
            attributes={"mcp.tool": "repo.read_file", "file.path": path},
        ):
            content = read_repo_file(path)
            return [types.TextContent(type="text", text=content)]

    if name == "grep":
        pattern = str(arguments.get("pattern", ""))
        pathspec = str(arguments.get("pathspec", ""))
        args = ["grep", "-n", pattern]
        if pathspec:
            args.extend(["--", pathspec])
        with tracer.start_as_current_span(
            "mcp.repo.grep",
            context=ctx,
            attributes={
                "mcp.tool": "repo.grep",
                "grep.pattern": pattern,
                "grep.pathspec": pathspec,
            },
        ):
            output = run_git(*args, ok_rc={0, 1})
            return [types.TextContent(type="text", text=output or "(no matches)")]

    raise ValueError(f"Unknown tool: {name}")


async def main() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="openagentio-demo-repo-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    provider = maybe_init_tracer()
    try:
        asyncio.run(main())
    finally:
        maybe_shutdown(provider)
