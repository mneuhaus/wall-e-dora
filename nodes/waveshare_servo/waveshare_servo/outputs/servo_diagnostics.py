"""Broadcaster for on-demand servo diagnostics."""

from __future__ import annotations

import traceback
from typing import Any

import pyarrow as pa


def broadcast_servo_diagnostics(node, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    """Broadcast one or more structured diagnostics payloads."""
    try:
        records = payload if isinstance(payload, list) else [payload]
        if not records:
            return
        node.send_output("servo_diagnostics", pa.array(records))
    except Exception as exc:
        print(f"Error broadcasting servo diagnostics: {exc}")
        traceback.print_exc()
