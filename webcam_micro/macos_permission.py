"""macOS camera-permission helpers for the camera backend."""

from __future__ import annotations

import sys
from typing import Any


def wrap_completion_handler(handler: Any) -> Any:
    """Return a macOS Objective-C block when the platform needs one."""

    if sys.platform != "darwin":
        return handler
    try:
        from rubicon.objc import Block
    except ModuleNotFoundError:
        return handler
    return Block(handler)
