"""client is an optional low-level HTTP/SSE smoke test for the adapter.

The recommended browser demo lives in ts_sdk_example/scenarios/sse_client.
This command runs two protocol-level checks:

  - invoke_demo:  synchronous request-reply (POST /v1/agents/echo/invoke).
  - stream_demo:  SSE streaming (POST /v1/agents/count/stream).

Start the server first:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/http_sse/server.py

Then run the client:

    py_sdk_example/.venv/bin/python py_sdk_example/scenarios/http_sse/client.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


BASE_URL = "http://localhost:9080"


def main() -> None:
    print("=== Invoke Demo (POST /v1/agents/echo/invoke) ===")
    try:
        invoke_demo()
    except Exception as err:
        print(f"invoke failed: {err}", file=sys.stderr)

    print()
    print("=== Stream Demo (POST /v1/agents/count/stream) ===")
    try:
        stream_demo()
    except Exception as err:
        print(f"stream failed: {err}", file=sys.stderr)


def invoke_demo() -> None:
    payload = {"msg": "hello from SSE client"}
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    req = urllib.request.Request(
        BASE_URL + "/v1/agents/echo/invoke",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        print(f"HTTP {resp.status}")
        print(f"Response: {resp.read().decode('utf-8')}")


def stream_demo() -> None:
    payload = {"n": 3}
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    req = urllib.request.Request(
        BASE_URL + "/v1/agents/count/stream",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req)
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"unexpected status {err.code}") from err

    with resp:
        if resp.status != 200:
            raise RuntimeError(f"unexpected status {resp.status}")

        sse_event = ""
        sse_id = ""
        sse_data = ""
        frame_num = 0

        for raw in resp:
            line = raw.decode("utf-8").rstrip("\r\n")
            if line == "":
                if sse_event:
                    frame_num += 1
                    print(f"\nFrame #{frame_num}  [{sse_event}]  id={sse_id}")
                    print(f"  Data: {sse_data}")
                sse_event = ""
                sse_id = ""
                sse_data = ""
                continue

            if line.startswith("event: "):
                sse_event = line.removeprefix("event: ")
            elif line.startswith("id: "):
                sse_id = line.removeprefix("id: ")
            elif line.startswith("data: "):
                sse_data = line.removeprefix("data: ")

        print(f"\nTotal frames received: {frame_num}")


if __name__ == "__main__":
    main()
