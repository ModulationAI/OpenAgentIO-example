# OpenAgentIO Promo Video

HyperFrames source for a short promotional video built from lightweight MP4 proxies of the recorded demo GIFs:

- `assets/matrix_mcp_chat.mp4`
- `assets/observability.mp4`

Narrative:

```text
OpenAgentIO connects different agents into one observable workflow.

Matrix -> OpenAgentIO -> MCP -> SSE -> Matrix
One message. Multiple participants. One trace.
```

## Files

| File | Purpose |
| --- | --- |
| `DESIGN.md` | Visual identity and motion rules. |
| `index.html` | Main 1920x1080 HyperFrames composition. |

## Preview

From this directory:

```bash
cd /Users/gubaoer/boyle_lab/learning/openagentio_example/promo_video
hyperframes preview index.html
```

If your local HyperFrames CLI uses a project command, run the equivalent preview command against `index.html`.

## Render

```bash
hyperframes render index.html --output openagentio-promo.mp4
```

Recommended export:

- 1920x1080
- 30 fps
- MP4 for X / LinkedIn
- Keep the first frame readable as a thumbnail

## Timing

The composition is about 60 seconds. The two recorded demo clips are allowed to play through before the next scene starts:

| Time | Scene |
| --- | --- |
| 0-4s | Positioning hook. |
| 4-8s | Problem: heterogeneous agent runtime. |
| 8-29s | Full Matrix + director console demo recording. |
| 29-35s | Protocol chain emphasis. |
| 35-57s | Full Jaeger trace proof recording. |
| 57-60s | Closing slogan. |

## Accuracy Boundary

This video should say:

- OpenAgentIO connects Matrix events, MCP tools, and SSE streaming agents through one runtime bus.
- Session and trace can be preserved across the flow.
- The project is developer preview.

It should not say:

- OpenAgentIO replaces MCP, Matrix, or SSE.
- OpenAgentIO is production-grade service mesh.
- Matrix is used as an SSE streaming bridge.
