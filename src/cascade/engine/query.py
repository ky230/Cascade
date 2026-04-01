from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable
from cascade.services.api_client import ModelClient


@dataclass
class QueryEngineConfig:
    max_turns: int = 25
    max_tool_rounds: int = 10


@dataclass
class TurnResult:
    output: str
    tool_uses: list
    stop_reason: str
    input_tokens: int = 0
    output_tokens: int = 0


class QueryEngine:
    """Core query engine — multi-turn tool-use loop."""

    def __init__(
        self,
        client: ModelClient,
        config: QueryEngineConfig | None = None,
    ):
        self.client = client
        self.config = config or QueryEngineConfig()
        self.messages: List[Dict[str, str]] = []

    def set_system_prompt(self, prompt: str) -> None:
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0] = {"role": "system", "content": prompt}
        else:
            self.messages.insert(0, {"role": "system", "content": prompt})

    async def submit(
        self,
        user_input: str,
        on_token: Callable[[str], None] | None = None,
    ) -> TurnResult:
        """Process a user message through the query loop."""
        self.messages.append({"role": "user", "content": user_input})

        for round_idx in range(self.config.max_tool_rounds):
            full_response = ""
            async for token in self.client.stream(self.messages):
                full_response += token
                if on_token:
                    on_token(token)

            self.messages.append({"role": "assistant", "content": full_response})

            tool_calls = self._extract_tool_calls(full_response)
            if not tool_calls:
                return TurnResult(
                    output=full_response,
                    tool_uses=[],
                    stop_reason="end_turn",
                )

            # Placeholder for tool execution (Phase 4)
            for call in tool_calls:
                self.messages.append({
                    "role": "user",
                    "content": f"Tool execution not yet implemented for {call['name']}"
                })

        return TurnResult(
            output="Max tool rounds reached",
            tool_uses=[],
            stop_reason="max_rounds",
        )

    def _extract_tool_calls(self, response: str) -> list:
        """Extract tool_use blocks. Placeholder for Phase 4."""
        return []
