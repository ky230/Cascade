from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """Abstract base class for all Cascade tools (Tool Wrapper Pattern)."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with the given arguments."""
        pass
