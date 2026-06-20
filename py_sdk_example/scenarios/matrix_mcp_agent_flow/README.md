# Matrix -> MCP -> SSE Demo

End-to-end demo showing how OpenAgentIO turns **Matrix events**, **MCP tools**,
and **SSE streaming agents** into one session-aware runtime bus.

## Phase 1: No-Matrix Core Flow

Phase 1 implements the smallest runnable version of the flow **without** a real
Matrix homeserver. A script called ``send_demo_prompt.py`` publishes a
Matrix-shaped ``matrix.message.received`` event directly to the Bus. The
``router_agent`` reacts to it and publishes a ``matrix.message.send`` event,
which ``matrix_sink`` prints to the terminal.

### Files

| File | Purpose |
| --- | --- |
| ``send_demo_prompt.py`` | Publishes a fake ``matrix.message.received`` event. |
| ``router_agent/main.py`` | Subscribes to inbound Matrix events and publishes placeholder replies. |
| ``matrix_sink/main.py`` | Subscribes to ``matrix.message.send`` and prints results. |
| ``run_phase1_inmem.py`` | Runs the entire Phase 1 flow in one process with the InMemory transport (no NATS required). |

### Quick local verification (InMemory)

```bash
cd /Users/gubaoer/boyle_lab/learning/openagentio_example
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/run_phase1_inmem.py
```

Expected output includes ``matrix.message.received`` being handled by the
router-agent and ``matrix.message.send`` being printed by matrix-sink.

### Distributed verification (NATS)

The standalone agent scripts use NATS so they can run as separate processes.
Start a local NATS server first, e.g.:

```bash
nats-server -p 4222
```

In separate terminals:

```bash
# Terminal 1
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/matrix_sink/main.py

# Terminal 2
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/router_agent/main.py

# Terminal 3
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/send_demo_prompt.py
```

``matrix_sink`` should print the final ``matrix.message.send`` payload.

### Event contract

The fake event payload matches ``MatrixEventBridge`` so the same router-agent
and matrix-sink can be reused once the real Matrix bridge is wired in.

**Inbound ``matrix.message.received`` payload:**

```python
{
    "text": "@openagentio inspect this repo and tell me whether it is ready for public release.",
    "html": None,
    "room_id": "!demo:localhost",
    "sender": "@admin:localhost",
    "event_id": "$<uuid>",
    "origin_server_ts": 0,
    "msgtype": "m.text",
}
```

**Outbound ``matrix.message.send`` payload:**

```python
{
    "room_id": "!demo:localhost",
    "text": "Received your message: ...",
}
```

## Phase 2: MCP repo tools

Phase 2 adds a local MCP stdio server that exposes repository tools, and wires
them into the No-Matrix Core Flow so the router-agent can collect release
readiness evidence.

### Files

| File | Purpose |
| --- | --- |
| ``mcp_repo_server/main.py`` | MCP stdio server exposing ``git_status``, ``read_file``, and ``grep``. |
| ``router_agent/main.py`` | Updated to start ``McpToolBridge`` and call ``mcp.repo.*`` tools. |
| ``smoke_test_phase2.py`` | Standalone smoke test that starts the server through ``McpToolBridge`` and invokes each tool via the Bus. |
| ``run_phase2_inmem.py`` | Runs the full Phase 2 flow in one process with the InMemory transport (no NATS required). |

### Quick local verification (InMemory)

```bash
cd /Users/gubaoer/boyle_lab/learning/openagentio_example
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/run_phase2_inmem.py
```

Expected output:

- MCP tool bridge starts.
- Two progress messages (``"Received. Inspecting repository..."`` and
  ``"Repo evidence collected. Running streaming review..."``).
- Final ``matrix.message.send`` containing git status, inspected file list, and
  grep results.

### Distributed verification (NATS)

The router-agent now starts the MCP tool bridge internally, so only the
router-agent and matrix-sink processes are needed besides the prompt sender.
Start NATS, then run:

```bash
# Terminal 1
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/matrix_sink/main.py

# Terminal 2
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/router_agent/main.py

# Terminal 3
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/send_demo_prompt.py
```

### Run Phase 2 smoke test

```bash
cd /Users/gubaoer/boyle_lab/learning/openagentio_example
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/smoke_test_phase2.py
```

Expected output includes:

- ``git_status`` returning ``"clean"`` (or the current git status of the OpenAgentIO repo).
- ``read_file`` returning the first 400 characters of ``README.md``.
- ``grep Envelope *.md`` returning matching lines.

### Repository root

By default the server reads from the OpenAgentIO main repository located next to
this example checkout:

```text
.../learning/openagentio
.../learning/openagentio_example/py_sdk_example/scenarios/matrix_mcp_agent_flow/...
```

Override with the ``REPO_ROOT`` environment variable:

```bash
REPO_ROOT=/path/to/repo py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/mcp_repo_server/main.py
```

## Phase 3: streaming reviewer

Phase 3 adds a mock-backed SSE streaming reviewer. The router-agent now calls
``bus.stream_invoke("release-reviewer", payload)`` after collecting repo
evidence, and the reviewer emits a stable, chunked analysis.

### Files

| File | Purpose |
| --- | --- |
| ``sse_agent/main.py`` | Mock-backed streaming reviewer exposing ``release-reviewer``. |
| ``router_agent/main.py`` | Updated to stream-invoke ``release-reviewer`` and publish its output as ``matrix.message.send``. |
| ``run_phase3_inmem.py`` | Runs the full Phase 3 flow in one process with the InMemory transport. |

### Quick local verification (InMemory)

```bash
cd /Users/gubaoer/boyle_lab/learning/openagentio_example
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/run_phase3_inmem.py
```

Expected output:

- MCP tool bridge starts.
- Two progress messages.
- Final ``matrix.message.send`` contains the streaming reviewer's text, mentioning
  Matrix, MCP, SSE, session, and trace.

### Distributed verification (NATS)

Start NATS, then run in separate terminals:

```bash
# Terminal 1
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/matrix_sink/main.py

# Terminal 2
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/sse_agent/main.py

# Terminal 3
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/router_agent/main.py

# Terminal 4
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/send_demo_prompt.py
```

``matrix_sink`` should print the progress messages and the final review.

## Phase 4: OTel trace for No-Matrix flow

Phase 4 adds OpenTelemetry tracing so Jaeger can display the end-to-end trace
across ``send_demo_prompt`` -> router-agent -> MCP tool bridge -> MCP repo
server -> SSE reviewer -> ``matrix.message.send``.

### Files

| File | Purpose |
| --- | --- |
| ``send_demo_prompt.py`` | Initializes ``send-demo-prompt`` tracer and starts the trace. |
| ``router_agent/main.py`` | Initializes ``router-agent`` tracer; creates spans around message handling, MCP invokes, and stream review. |
| ``sse_agent/main.py`` | Initializes ``sse-reviewer`` tracer; creates span around review generation. |
| ``matrix_sink/main.py`` | Initializes ``matrix-sink`` tracer and consumes traced outbound events. |
| ``mcp_repo_server/main.py`` | Initializes ``mcp-repo-server`` tracer; extracts ``traceparent`` from JSON-RPC ``_meta`` to join the trace. |
| ``docker-compose.yml`` | Starts Jaeger on http://localhost:16686 with OTLP gRPC on 4317. |
| ``run_phase4_inmem.py`` | Runs the full Phase 4 flow in one process with the InMemory transport and sends spans to Jaeger. |

### Prerequisites

Install the OpenTelemetry dependencies in the example virtual environment:

```bash
cd /Users/gubaoer/boyle_lab/learning/openagentio_example
py_sdk_example/.venv/bin/python -m pip install \
    opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc
```

### Quick local verification (InMemory + Jaeger)

Phase 4 tracing is **opt-in** via ``OTEL_ENABLED=1`` or
``OTEL_EXPORTER_OTLP_ENDPOINT``. The ``run_phase4_inmem.py`` script enables
OTel automatically; for the standalone agent scripts you must export the flag
before running them.

Start Jaeger:

```bash
cd /Users/gubaoer/boyle_lab/learning/openagentio_example
docker compose -f py_sdk_example/scenarios/matrix_mcp_agent_flow/docker-compose.yml up -d
```

Run the Phase 4 flow:

```bash
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/run_phase4_inmem.py
```

The console prints the trace ID, e.g.:

```text
[demo-prompt] published matrix.message.received event_id=$... trace_id=...
```

Open http://localhost:16686, paste the **TraceID** into the search box, and
click **Find Traces**. You should see one trace spanning:

- ``send_demo_prompt.publish``
- ``router.handle_matrix_message``
- ``mcp.invoke`` (MCP tool bridge)
- ``mcp.repo.git_status`` / ``mcp.repo.read_file`` / ``mcp.repo.grep`` (MCP repo server)
- ``router.stream_review``
- ``sse-reviewer.generate``
- ``acp.handle.matrix.message.send``

### Distributed verification (NATS)

Start NATS and Jaeger, then run in separate terminals with ``OTEL_ENABLED=1``:

```bash
# Terminal 1
OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/matrix_sink/main.py

# Terminal 2
OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/sse_agent/main.py

# Terminal 3
OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/router_agent/main.py

# Terminal 4
OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/send_demo_prompt.py
```

Because each process uses its own ``init_tracer(service_name)``, Jaeger shows
separate services: ``send-demo-prompt``, ``router-agent``, ``mcp-repo-server``,
``sse-reviewer``, and ``matrix-sink``.

## Phase 5: real Matrix bridge

Phase 5 replaces the fake ``send_demo_prompt.py`` publisher with a real
``MatrixEventBridge`` that listens in a local Synapse room and writes
``matrix.message.send`` events back to Matrix.

### Files

| File | Purpose |
| --- | --- |
| ``docker-compose.yml`` | Starts NATS, Jaeger, Synapse, and Element Web. |
| ``element-web/config.json`` | Element Web configuration pointing at local Synapse. |
| ``seed_synapse.py`` | Generates Synapse config, registers users, creates demo room, writes ``.env``. |
| ``matrix_bridge.yaml`` | ``MatrixEventBridge`` config template (uses ``.env``). |
| ``matrix_bridge/main.py`` | Loads ``.env`` and runs ``MatrixEventBridge``. |

### Prerequisites

Docker must be able to pull ``matrixdotorg/synapse`` and ``vectorim/element-web``
images. Make sure Docker can reach the registry.

Install the OpenTelemetry dependencies if you plan to enable tracing in Phase 5/6:

```bash
cd /Users/gubaoer/boyle_lab/learning/openagentio_example
py_sdk_example/.venv/bin/python -m pip install \
    opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc
```

Make sure the example virtual environment has the OpenAgentIO MCP/bridge extras
installed:

```bash
py_sdk_example/.venv/bin/python -m pip install -e \
    '/Users/gubaoer/boyle_lab/learning/openagentio/sdk/python[mcp,bridge]'
```

### Setup

```bash
cd /Users/gubaoer/boyle_lab/learning/openagentio_example
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/seed_synapse.py
```

This:

1. Generates ``synapse-data/homeserver.yaml``.
2. Enables open registration for local testing.
3. Starts Synapse and Element Web via docker compose.
4. Registers ``@admin:localhost`` and ``@openagentio-bot:localhost``.
5. Sets ``@admin:localhost`` display name to ``Boyle Gu``.
6. Creates ``#demo:localhost`` room.
7. Invites the bot and makes it join.
8. Writes ``py_sdk_example/scenarios/matrix_mcp_agent_flow/.env``:

```text
MATRIX_HOMESERVER_URL=http://localhost:8008
MATRIX_ROOM_ID=!...
MATRIX_BOT_USER_ID=@openagentio-bot:localhost
MATRIX_ACCESS_TOKEN=...
```

### Run the real Matrix flow

In separate terminals (start NATS/Synapse first):

```bash
# Terminal 1: matrix sink
OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/matrix_sink/main.py

# Terminal 2: streaming reviewer
OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/sse_agent/main.py

# Terminal 3: router agent
OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/router_agent/main.py

# Terminal 4: real Matrix bridge
OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/matrix_bridge/main.py
```

Open Element Web at http://localhost:8080, log in as ``@admin:localhost``
(password ``OpenAgentIO-Demo-2026``), open the ``#demo:localhost`` room, and
send:

```text
@openagentio inspect this repo and tell me whether it is ready for public release.
```

The bot should reply with progress messages and the final streaming review in
the Matrix room.

## Phase 6: OTel trace for the real Matrix flow

Phase 6 makes the real Matrix flow observable in Jaeger:

```text
Element Web -> Synapse -> MatrixEventBridge -> NATS Bus
  -> router-agent -> MCP repo server -> sse-reviewer
  -> MatrixEventBridge -> Synapse -> Element Web
```

Matrix user messages do not normally carry W3C ``traceparent``. For the demo,
``matrix_bridge/main.py`` starts a root ``matrix.bridge.receive`` span when a
real ``matrix.message.received`` event enters the Bus and injects that span's
``traceparent`` into the Envelope. The router, MCP tool bridge, MCP stdio
server, streaming reviewer, and outbound Matrix send then continue the same
trace.

### Run with tracing

Start the seeded infrastructure first:

```bash
cd /Users/gubaoer/boyle_lab/learning/openagentio_example
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/seed_synapse.py
```

Then run the agents in separate terminals:

```bash
# Terminal 1: streaming reviewer
OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/sse_agent/main.py

# Terminal 2: router agent
OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/router_agent/main.py

# Terminal 3: real Matrix bridge
OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/matrix_bridge/main.py
```

``matrix_sink/main.py`` is optional in Phase 6. Leave it off for the cleanest
recording because the real Matrix bridge already sends ``matrix.message.send``
events back to the Matrix room.

Open http://localhost:8080, log in as ``@admin:localhost`` with password
``OpenAgentIO-Demo-2026``, open ``#demo:localhost``, and send:

```text
@openagentio inspect this repo and tell me whether it is ready for public release.
```

### Verify in Jaeger

Open http://localhost:16686 and search recent traces. The easiest service to
start from is ``matrix-bridge`` because it owns the real Matrix entry and exit.

Expected trace shape:

- ``matrix-bridge`` span ``matrix.bridge.receive``
- ``router-agent`` span ``acp.handle.matrix.message.received``
- ``router-agent`` span ``router.handle_matrix_message``
- ``router-agent`` spans for MCP invokes and stream review
- ``mcp-repo-server`` spans for ``repo.git_status``, ``repo.read_file``, and
  ``repo.grep``
- ``sse-reviewer`` span ``acp.stream.handle.release-reviewer`` or
  ``sse-reviewer.generate``
- ``matrix-bridge`` span ``acp.handle.matrix.message.send`` for outbound Matrix
  replies

If Jaeger shows separate traces instead of one trace, check:

- All three long-running processes were started with ``OTEL_ENABLED=1``.
- Jaeger is reachable on ``localhost:4317``.
- The ``matrix.bridge.receive`` span exists. If it is missing, the Matrix bridge
  is not creating the root trace for real inbound events.
- The MCP server process inherits ``OTEL_ENABLED=1`` from ``router_agent``; the
  router launches it through the MCP stdio bridge.

## Phase 7: recording mode

Phase 7 keeps the real Matrix/NATS/MCP/SSE/Jaeger flow unchanged, but adds a
recording-friendly view for GIF/video capture.

### What changes in recording mode

- ``DEMO_REPLY_MODE=short`` makes the final Matrix reply compact enough for a
  15-25 second GIF/video clip.
- ``DEMO_PACING=1`` slows only the visible recording path, so the protocol
  boundaries are readable on screen.
- ``director_console/main.py`` subscribes to Bus events and prints a concise
  read-only protocol map. The Matrix chat is not the main visual; the director
  console is the proof that one event crossed multiple runtimes:

```text
MATRIX   @admin:localhost -> !room:localhost
BUS      event=matrix.message.received transport=nats://127.0.0.1:4222
TRACE    trace_id=...
BUS      router-agent accepted Matrix event; preserving session + trace context
MCP      invoke mcp.repo.git_status
MCP      invoke mcp.repo.read_file path=README.md
MCP      invoke mcp.repo.grep pattern=Envelope pathspec=*.md
SSE      stream_invoke release-reviewer with compact repo evidence
SSE      release-reviewer streamed chunk 6
MATRIX   final review sent
RESULT   Release readiness: Developer Preview...
```

The director console does not publish events, call tools, or change runtime
behavior. It exists only to make the real flow easier to understand on screen.

### Run recording mode

Start infrastructure first:

```bash
cd /Users/gubaoer/boyle_lab/learning/openagentio_example
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/seed_synapse.py
```

Then run these in separate terminals:

```bash
# Terminal 1: director console
py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/director_console/main.py

# Terminal 2: streaming reviewer
OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/sse_agent/main.py

# Terminal 3: router agent with short Matrix replies and recording pacing
OTEL_ENABLED=1 DEMO_REPLY_MODE=short DEMO_PACING=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/router_agent/main.py

# Terminal 4: real Matrix bridge
OTEL_ENABLED=1 py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/matrix_bridge/main.py
```

Open Element Web at http://localhost:8080, log in as ``@admin:localhost``,
open ``#demo:localhost``, and send this recording prompt:

```text
@openagentio audit this repo using MCP tools, stream a release verdict, and keep the full trace visible.
```

Recommended 15-25 second recording rhythm:

```text
0-2s    Matrix prompt enters the room
2-4s    Director console shows MATRIX -> OpenAgentIO -> TRACE
4-9s    Director console shows MCP tool invocations
9-13s   Director console shows SSE streaming chunks
13-16s  Matrix final short reply
16-22s  Jaeger trace highlight across matrix-bridge, router-agent,
        mcp-repo-server, and sse-reviewer
```

Record the real screens with QuickTime, OBS, Screen Studio, or CleanShot.
HyperFrames can be used after capture for captions, zooms, highlight boxes,
and GIF/MP4 export.

### Using an existing Matrix homeserver

If you cannot run Docker locally, set the four environment variables manually
and run ``matrix_bridge/main.py``:

```bash
export MATRIX_HOMESERVER_URL=https://matrix.example.com
export MATRIX_ROOM_ID='!room:example.com'
export MATRIX_BOT_USER_ID='@bot:example.com'
export MATRIX_ACCESS_TOKEN='...'

py_sdk_example/.venv/bin/python \
    py_sdk_example/scenarios/matrix_mcp_agent_flow/matrix_bridge/main.py
```
