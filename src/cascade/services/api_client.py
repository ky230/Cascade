from litellm import acompletion
from cascade.services.api_config import get_litellm_kwargs
from typing import List, Dict, AsyncIterator, Optional, Callable
import json
from dataclasses import dataclass, field

@dataclass
class StreamResult:
    """Result of a full streaming call — text + any tool_calls."""
    text: str = ""
    tool_calls: list = field(default_factory=list)
    finish_reason: str = ""
    
class ModelClient:
    def __init__(self, provider: str, model_name: str):
        self.provider = provider
        self.model_name = model_name

    async def generate(self, messages: List[Dict[str, str]]) -> str:
        kwargs = get_litellm_kwargs(self.provider, self.model_name)
        response = await acompletion(messages=messages, **kwargs)
        return response.choices[0].message.content

    async def stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
    ) -> AsyncIterator[str]:
        """Stream tokens as they arrive."""
        kwargs = get_litellm_kwargs(self.provider, self.model_name)
        kwargs["stream"] = True
        if tools:
            kwargs["tools"] = tools
            
        response = await acompletion(messages=messages, **kwargs)
        async for chunk in response:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    yield delta.content

    async def stream_full(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> "StreamResult":
        """Stream a response, accumulating both text and tool_calls.
        
        Returns a StreamResult with the full text and parsed tool calls.
        """
        kwargs = get_litellm_kwargs(self.provider, self.model_name)
        kwargs["stream"] = True
        if tools:
            kwargs["tools"] = tools
        
        response = await acompletion(messages=messages, **kwargs)
        
        text_parts = []
        tool_call_accum: dict[int, dict] = {}  # index -> {id, name, arguments_str}
        finish_reason = ""
        
        async for chunk in response:
            if not hasattr(chunk, 'choices') or len(chunk.choices) == 0:
                continue
            delta = chunk.choices[0].delta
            finish_reason = getattr(chunk.choices[0], 'finish_reason', '') or finish_reason
            
            # Accumulate text
            if hasattr(delta, 'content') and delta.content:
                text_parts.append(delta.content)
                if on_token:
                    on_token(delta.content)
            
            # Accumulate tool calls
            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_call_accum:
                        tool_call_accum[idx] = {
                            "id": getattr(tc, 'id', None) or "",
                            "name": getattr(tc.function, 'name', None) or "",
                            "arguments_str": "",
                        }
                    entry = tool_call_accum[idx]
                    if getattr(tc, 'id', None):
                        entry["id"] = tc.id
                    if getattr(tc.function, 'name', None):
                        entry["name"] = tc.function.name
                    if getattr(tc.function, 'arguments', None):
                        entry["arguments_str"] += tc.function.arguments
        
        # Parse accumulated tool calls
        parsed_tool_calls = []
        for idx in sorted(tool_call_accum.keys()):
            entry = tool_call_accum[idx]
            try:
                args = json.loads(entry["arguments_str"]) if entry["arguments_str"] else {}
            except json.JSONDecodeError:
                args = {"_raw": entry["arguments_str"]}
            parsed_tool_calls.append({
                "id": entry["id"],
                "name": entry["name"],
                "arguments": args,
            })
        
        return StreamResult(
            text="".join(text_parts),
            tool_calls=parsed_tool_calls,
            finish_reason=finish_reason,
        )
