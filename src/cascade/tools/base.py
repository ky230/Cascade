from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    output: str
    is_error: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    def aliases(self) -> list[str]: return []

    @property
    def is_read_only(self) -> bool: return False

    @property
    def is_destructive(self) -> bool: return False

    def is_enabled(self) -> bool: return True

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult: ...

    @abstractmethod
    def get_input_schema(self) -> dict: ...

    async def check_permissions(self, **kwargs: Any) -> bool: return True

    def user_facing_name(self, input: dict | None = None) -> str: return self.name
