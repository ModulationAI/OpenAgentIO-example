# OTel Tracing with Jaeger

This scenario demonstrates distributed tracing across OpenAgentIO agents using OpenTelemetry and Jaeger.

## Architecture

```
client -> gateway-agent -> backend-agent
```

Each hop propagates the trace context through the envelope's `traceparent` field, so the entire call chain appears as a single trace in Jaeger.

## Prerequisites

- Go 1.26+
- Docker & Docker Compose
- NATS server running on `localhost:4222` (same as other scenarios)

## Run

### 1. Start infrastructure

From the `go_sdk_example/` directory:

```bash
docker compose -f scenarios/otel_tracing/docker-compose.yml up -d
```

This starts **Jaeger** UI on http://localhost:16686 (NATS is assumed to already be running locally).

### 2. Start agents

In separate terminals:

```bash
# Terminal 1
go run ./scenarios/otel_tracing/backend

# Terminal 2
go run ./scenarios/otel_tracing/gateway
```

### 3. Send a request

```bash
go run ./scenarios/otel_tracing/client
```

You should see output like:

```
[client] TraceID: a1b2c3d4e5f6...
[client] invoking gateway-agent with 14 add 3
[client] result=17 handled_by=gateway-agent -> backend-agent
[client] open http://localhost:16686 and search by TraceID to view the trace
```

### 4. View the trace

Open http://localhost:16686, paste the **TraceID** into the search box, and click **Find Traces**.

You will see a trace spanning three services:

| Service | Span |
|---------|------|
| `otel-client` | `client.calc-request` |
| `gateway-agent` | `acp.handle.MessageReceived` -> `gateway.delegate` |
| `backend-agent` | `acp.handle.MessageReceived` -> `backend.calculate` |

Click any span to inspect attributes such as `acp.event_type`, `acp.session_id`, `calc.a`, `calc.b`, etc.

## Key OTel Integration Points

### 1. Receive side — `otel.Trace()` middleware

`gateway` and `backend` register `otel.Trace()` in the middleware chain. On every inbound envelope it:

- Extracts the upstream `SpanContext` from `envelope.Traceparent`
- Starts a Consumer span named `acp.handle.<event_type>`
- Records errors and sets span status when the handler fails

### 2. Send side — `otel.EnvelopePreparer()`

All three programs (client, gateway, backend) configure the bus with `otel.EnvelopePreparer()`. Before any outbound envelope is published it injects the active span into `envelope.Traceparent`, ensuring the trace crosses process boundaries.

### 3. Manual spans inside handlers

The gateway creates an explicit `gateway.delegate` span around the `b.Invoke` call to the backend. The backend creates a `backend.calculate` span around the actual computation. These appear as nested children in Jaeger.

## Stop

```bash
# Stop agents with Ctrl+C in each terminal, then:
docker compose -f scenarios/otel_tracing/docker-compose.yml down
```
