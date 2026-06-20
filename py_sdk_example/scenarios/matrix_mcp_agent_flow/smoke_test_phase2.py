"""Phase 2 smoke test: drive the demo repo MCP server through McpToolBridge.

Run from the repository root:

    py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/smoke_test_phase2.py

This test relies on ``openagentio`` being installed in editable mode in the
example virtual environment (see the scenario README for install instructions).

This test:
1. Starts the local MCP repo server as a stdio subprocess.
2. Registers its tools as OpenAgentIO invoke targets via McpToolBridge.
3. Calls repo.git_status, repo.read_file, and repo.grep.
4. Prints the payloads and exits.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from openagentio import Bus, InMemoryDriver
from openagentio.bridge import BUILTIN_FACTORIES, BridgeConfig
from openagentio.bridge.runner import BridgeRunner


async def main() -> None:
    # smoke_test_phase1.py is directly inside matrix_mcp_agent_flow/, so
    # parents[4] reaches .../learning where openagentio/ lives next to
    # openagentio_example/.
    repo_root = Path(__file__).resolve().parents[4] / "openagentio"
    server_script = Path(__file__).resolve().parent / "mcp_repo_server" / "main.py"

    bus = Bus(agent_id="phase1-smoke", transport=InMemoryDriver())
    await bus.connect()

    config = BridgeConfig.from_dict(
        {
            "version": "openagentio.bridge/v1",
            "bridges": [
                {
                    "name": "demo-repo",
                    "type": "mcp_tool",
                    "config": {
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": [str(server_script)],
                        "env": {"REPO_ROOT": str(repo_root)},
                        "timeout": 30,
                    },
                    "mappings": {
                        "target_prefix": "demo.repo",
                    },
                }
            ],
        }
    )

    runner = BridgeRunner(bus, config, BUILTIN_FACTORIES)
    await runner.start()

    try:
        print("--- repo.git_status ---")
        status = await bus.invoke("demo.repo.git_status", {})
        print(status.payload_json())

        print("\n--- repo.read_file README.md ---")
        readme = await bus.invoke("demo.repo.read_file", {"path": "README.md"})
        payload = readme.payload_json()
        text = payload.get("text", "") if isinstance(payload, dict) else ""
        print(text[:400] + ("..." if len(text) > 400 else ""))

        print("\n--- repo.grep Envelope *.md ---")
        grep = await bus.invoke(
            "demo.repo.grep", {"pattern": "Envelope", "pathspec": "*.md"}
        )
        print(grep.payload_json())
    finally:
        await runner.stop()
        await bus.close()


if __name__ == "__main__":
    asyncio.run(main())
