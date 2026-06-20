"""matrix_bridge runs MatrixEventBridge for the real Matrix Phase 5 demo.

It loads credentials from ``.env`` (written by ``seed_synapse.py``), substitutes
them into ``matrix_bridge.yaml``, and starts the bridge so real Matrix room
messages become ``matrix.message.received`` events and ``matrix.message.send``
events are written back to the Matrix room.

Run (requires NATS and the seeded Synapse environment):

    cd /Users/gubaoer/boyle_lab/learning/openagentio_example
    py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/matrix_bridge/main.py
"""

from __future__ import annotations

import asyncio
import os
import re
import signal
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from opentelemetry import propagate, trace
from opentelemetry.trace import SpanKind

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from openagentio import (
    Bus,
    OTelEnvelopePreparer,
    OTelTrace,
    Recover,
    WithAgentID,
    WithEnvelopePreparer,
    WithMiddleware,
    WithNATSName,
    WithTransport,
    dial,
)
from openagentio.bridge import BUILTIN_FACTORIES, BridgeConfig
from openagentio.bridge.runner import BridgeRunner
from openagentio.event.envelope import Envelope
from openagentio.middleware.otel.carrier import EnvelopeCarrier, EnvelopeSetter
from py_sdk_example.internal.common import wait_for_demo_transport
from py_sdk_example.internal.otel import init_tracer


def _otel_enabled() -> bool:
    return os.getenv("OTEL_ENABLED", "") == "1" or bool(
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    )


def _otel_options():
    if not _otel_enabled():
        return []
    return [
        WithMiddleware(
            Recover(),
            OTelTrace(),
        ),
        WithEnvelopePreparer(
            _matrix_inbound_root_trace_preparer(),
            OTelEnvelopePreparer(),
        ),
    ]


def _matrix_inbound_root_trace_preparer():
    """Start a demo trace when a real Matrix message enters the Bus.

    Matrix room messages sent from Element do not carry W3C trace context by
    default. The generic OTel envelope preparer only injects when a span is
    already active, so the real Matrix flow needs an explicit root span at the
    bridge boundary. Downstream Bus handlers then continue this trace from the
    injected envelope ``traceparent``.
    """
    tracer = trace.get_tracer("matrix-bridge")
    setter = EnvelopeSetter()

    def preparer(env: Envelope) -> None:
        if env.event_type != "matrix.message.received" or env.traceparent:
            return

        metadata = env.metadata or {}
        with tracer.start_as_current_span(
            "matrix.bridge.receive",
            kind=SpanKind.CONSUMER,
            attributes={
                "messaging.system": "matrix",
                "messaging.destination.name": metadata.get("matrix.room_id", ""),
                "messaging.message.id": env.correlation_id,
                "matrix.room_id": metadata.get("matrix.room_id", ""),
                "matrix.sender": metadata.get("matrix.sender", ""),
                "matrix.event_id": metadata.get("matrix.event_id", ""),
                "acp.event_type": env.event_type,
                "acp.session_id": env.session_id,
                "acp.conversation_id": env.conversation_id,
            },
        ) as span:
            propagate.inject(EnvelopeCarrier(env), setter=setter)
            span_context = span.get_span_context()
            env.trace_id = f"{span_context.trace_id:032x}"
            env.span_id = f"{span_context.span_id:016x}"

    return preparer


def _load_config_with_env(path: Path) -> BridgeConfig:
    """Load bridge config, substituting ``${VAR}`` placeholders from the environment."""
    text = path.read_text(encoding="utf-8")

    def replacer(match: re.Match[str]) -> str:
        var = match.group(1)
        value = os.getenv(var)
        if value is None:
            raise ValueError(f"missing environment variable for bridge config: {var}")
        return value

    text = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replacer, text)
    data = yaml.safe_load(text)
    return BridgeConfig.from_dict(data)


async def main() -> None:
    # .env and matrix_bridge.yaml live in the scenario root, one directory up.
    scenario_root = Path(__file__).resolve().parent.parent
    env_path = scenario_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[matrix-bridge] loaded {env_path}")
    else:
        print(
            f"[matrix-bridge] {env_path} not found; using environment variables",
            file=sys.stderr,
        )

    config_path = scenario_root / "matrix_bridge.yaml"
    try:
        config = _load_config_with_env(config_path)
    except Exception as err:
        print(f"[matrix-bridge] config error: {err}", file=sys.stderr)
        raise SystemExit(1) from err

    shutdown = init_tracer("matrix-bridge") if _otel_enabled() else lambda: None

    try:
        try:
            tp = await dial(WithNATSName("matrix-bridge"))
        except Exception as err:
            print(f"transport: {err}", file=sys.stderr)
            raise SystemExit(1) from err

        bus = Bus.new(
            WithAgentID("matrix-bridge"),
            WithTransport(tp),
            *_otel_options(),
        )

        runner = BridgeRunner(bus, config, BUILTIN_FACTORIES)

        try:
            await runner.start()
            print("[matrix-bridge] started")
            await wait_for_demo_transport(tp)
            print("[matrix-bridge] press Ctrl+C to exit")

            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop.set)
            await stop.wait()
            print("[matrix-bridge] shutting down")
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
