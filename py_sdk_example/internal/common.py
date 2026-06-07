"""Shared utilities for the scene example demos."""
from __future__ import annotations

from typing import Any


async def wait_for_demo_transport(tp: Any) -> None:
    """Wait for asynchronous transport operations to reach the broker.

    Short-lived command-line demos use this synchronization point after
    registering handlers/subscriptions or publishing a final message.
    Long-running applications usually do not need it.
    """
    flush = getattr(tp, "flush", None)
    if flush is None:
        return
    await flush()
