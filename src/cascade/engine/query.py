from __future__ import annotations
import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable, Any
from cascade.services.api_client import ModelClient, StreamResult
from cascade.tools.registry import ToolRegistry
from cascade.tools.base import ToolResult


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
        registry: ToolRegistry | None = None,
    ):
        self.client = client
        self.config = config or QueryEngineConfig()
        self.messages: List[Dict] = []
        self.registry = registry

    def set_system_prompt(self, prompt: str) -> None:
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0] = {"role": "system", "content": prompt}
        else:
            self.messages.insert(0, {"role": "system", "content": prompt})

    async def submit(
        self,
        user_input: str,
        on_token: Callable[[str], None] | None = None,
        on_tool_start: Callable[[str, dict], None] | None = None,
        on_tool_end: Callable[[str, ToolResult], None] | None = None,
    ) -> TurnResult:
        """Process a user message through the agentic tool loop."""
        self.messages.append({"role": "user", "content": user_input})

        tool_schemas = self.registry.get_tool_schemas() if self.registry else None
        all_tool_uses = []

        for round_idx in range(self.config.max_tool_rounds):
            # Stream the LLM response
            result: StreamResult = await self.client.stream_full(
                self.messages,
                tools=tool_schemas if tool_schemas else None,
                on_token=on_token,
            )

            # Build the assistant message for the transcript
            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": result.text or ""}
            if result.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]),
                        }
                    }
                    for tc in result.tool_calls
                ]
            self.messages.append(assistant_msg)

            # If no tool calls, we're done
            if not result.tool_calls:
                return TurnResult(
                    output=result.text,
                    tool_uses=all_tool_uses,
                    stop_reason="end_turn",
                )

            # Execute each tool call
            for tc in result.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_id = tc["id"]

                if on_tool_start:
                    on_tool_start(tool_name, tool_args)

                if self.registry:
                    tool_result = await self.registry.execute(tool_name, tool_args)
                else:
                    tool_result = ToolResult(output=f"No registry for {tool_name}", is_error=True)

                if on_tool_end:
                    on_tool_end(tool_name, tool_result)

                all_tool_uses.append({
                    "name": tool_name,
                    "input": tool_args,
                    "result": tool_result.output,
                    "is_error": tool_result.is_error,
                })

                # Feed tool result back to the model
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": tool_result.output,
                })

        return TurnResult(
            output="Max tool rounds reached",
            tool_uses=all_tool_uses,
            stop_reason="max_rounds",
        )
