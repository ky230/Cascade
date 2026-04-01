from __future__ import annotations
from enum import Enum
from typing import Optional, Callable, Awaitable
from cascade.tools.base import BaseTool


class PermissionMode(str, Enum):
    DEFAULT = "default"    # Always ask if ask_user is provided
    AUTO = "auto"          # Auto-allow if read_only, ask otherwise
    BYPASS = "bypass"      # Danger: Allow everything


class PermissionResult:
    def __init__(self, allowed: bool, reason: str = ""):
        self.allowed = allowed
        self.reason = reason


class PermissionEngine:
    def __init__(self, mode: PermissionMode = PermissionMode.DEFAULT):
        self.mode = mode
        self._always_allow: set[str] = set()
        self._always_deny: set[str] = set()

    async def check(
        self,
        tool: BaseTool,
        input: dict,
        ask_user: Optional[Callable[[str], Awaitable[bool]]] = None,
    ) -> PermissionResult:

        if tool.name in self._always_deny:
            return PermissionResult(False, "denied by rule")

        if tool.name in self._always_allow:
            return PermissionResult(True, "allowed by rule")

        if self.mode == PermissionMode.BYPASS:
            return PermissionResult(True, "bypass mode")

        if self.mode == PermissionMode.AUTO and tool.is_read_only:
            return PermissionResult(True, "auto-allowed safe tool")

        if ask_user:
            allowed = await ask_user(f"Allow {tool.user_facing_name(input)}? [y/N]")
            return PermissionResult(allowed, "user interactive decision")

        return PermissionResult(False, "no interactive prompt available")
