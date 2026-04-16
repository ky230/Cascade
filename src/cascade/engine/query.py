from __future__ import annotations
import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable, Any, Awaitable
from cascade.services.api_client import ModelClient, StreamResult
from cascade.tools.registry import ToolRegistry
from cascade.tools.base import ToolResult
from cascade.permissions.engine import PermissionEngine


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
        permissions: PermissionEngine | None = None,
    ):
        self.client = client
        self.config = config or QueryEngineConfig()
        self.messages: List[Dict] = []
        self.registry = registry
        self.permissions = permissions
        # Session-level token counters (accumulated from API usage responses)
        self.session_input_tokens: int = 0
        self.session_output_tokens: int = 0
        # Most recent API call's token counts (overwritten each call)
        self.last_input_tokens: int = 0
        self.last_output_tokens: int = 0

    def set_system_prompt(self, prompt: str) -> None:
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0] = {"role": "system", "content": prompt}
        else:
            self.messages.insert(0, {"role": "system", "content": prompt})

    async def submit(
        self,
        user_input: str,
        on_token: Callable[[str], None] | None = None,
        on_tool_start: Callable[[str, dict], Awaitable[None]] | None = None,
        on_tool_end: Callable[[str, ToolResult], Awaitable[None]] | None = None,
        ask_user: Callable[[str], Awaitable[bool]] | None = None,
    ) -> TurnResult:
        """Process a user message through the agentic tool loop."""
        self.messages.append({"role": "user", "content": user_input})

        tool_schemas = self.registry.get_tool_schemas() if self.registry else None
        all_tool_uses = []
        total_input_tokens = 0
        total_output_tokens = 0

        for round_idx in range(self.config.max_tool_rounds):
            # Stream the LLM response
            result: StreamResult = await self.client.stream_full(
                self.messages,
                tools=tool_schemas if tool_schemas else None,
                on_token=on_token,
            )

            # Accumulate token usage from API response
            total_input_tokens += result.input_tokens
            total_output_tokens += result.output_tokens
            # Track the most recent call (for context window display)
            self.last_input_tokens = result.input_tokens
            self.last_output_tokens = result.output_tokens

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
                self.session_input_tokens += total_input_tokens
                self.session_output_tokens += total_output_tokens
                return TurnResult(
                    output=result.text,
                    tool_uses=all_tool_uses,
                    stop_reason="end_turn",
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )

            # Execute each tool call
            abort_remaining = False

            for tc in result.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_id = tc["id"]

                if abort_remaining:
                    # Silently fill remaining tool IDs so message history stays valid
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": "Cancelled: user denied a previous tool call.",
                    })
                    continue

                # Notify UI of tool start BEFORE asking for permission
                if on_tool_start:
                    await on_tool_start(tool_name, tool_args)

                # Permission check
                if self.permissions and self.registry:
                    tool_obj = self.registry.get(tool_name)
                    if tool_obj:
                        perm = await self.permissions.check(tool_obj, tool_args, ask_user=ask_user)
                        if not perm.allowed:
                            tool_result = ToolResult(
                                output=f"Permission denied: {perm.reason}",
                                is_error=True,
                            )
                            if on_tool_end:
                                await on_tool_end(tool_name, tool_result)
                            all_tool_uses.append({
                                "name": tool_name,
                                "input": tool_args,
                                "result": tool_result.output,
                                "is_error": tool_result.is_error,
                            })
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "content": tool_result.output,
                            })
                            abort_remaining = True
                            continue

                if self.registry:
                    tool_result = await self.registry.execute(tool_name, tool_args)
                else:
                    tool_result = ToolResult(output=f"No registry for {tool_name}", is_error=True)

                if on_tool_end:
                    await on_tool_end(tool_name, tool_result)

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

            # Hard stop: user denied → no more LLM calls, return to prompt
            if abort_remaining:
                self.session_input_tokens += total_input_tokens
                self.session_output_tokens += total_output_tokens
                return TurnResult(
                    output="",
                    tool_uses=all_tool_uses,
                    stop_reason="user_denied",
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )

        self.session_input_tokens += total_input_tokens
        self.session_output_tokens += total_output_tokens
        return TurnResult(
            output="Max tool rounds reached",
            tool_uses=all_tool_uses,
            stop_reason="max_rounds",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )
