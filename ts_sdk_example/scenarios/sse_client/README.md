# OpenAgentIO SSE Chat Example

This is a minimal browser client for `go_sdk_example/scenarios/http_sse`.
It uses `@openagentio/client` to call the Go HTTP/SSE adapter.

## Run

Terminal 1:

```bash
cd go_sdk_example/scenarios/http_sse
go run -tags=server .
```

Terminal 2:

```bash
cd ts_sdk_example/scenarios/sse_client
npm install
npm run dev
```

Open the Vite URL in your browser, then send a chat message.

The browser sends:

```ts
client.streamInvoke("assistant", {
  message: "How does OpenAgentIO streaming work?",
  delay_ms: 140,
});
```

Each `agent.response.delta` frame appends text to the assistant message bubble.

The Vite dev server proxies `/api` to `http://localhost:9080`, so the browser
does not need extra CORS configuration.
