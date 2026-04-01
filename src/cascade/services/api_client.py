from litellm import acompletion
from cascade.services.api_config import get_litellm_kwargs
from typing import List, Dict, AsyncIterator, Optional, Callable
import json
import os
import aiohttp
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

    async def _handle_xai_image(self, messages: List[Dict[str, str]]) -> str:
        """Bypass for xAI image generation model.
        
        Extracts any file path from the user prompt, generates the image,
        and downloads it to the specified path (or CWD if none given).
        """
        import re
        import time
        
        # Find the last user message to use as the prompt
        raw_prompt = ""
        for m in reversed(messages):
            if m["role"] == "user":
                raw_prompt = m["content"]
                break
        if not raw_prompt:
            return "Error: No user prompt found for image generation."
        
        # Extract path from prompt (absolute paths like /Users/... or ~/...)
        save_dir = None
        save_filename = None
        
        # Match absolute paths or ~/paths 
        path_pattern = r'(?:到|to|save|保存|下载)\s*((?:/|~/)[^\s,，。!！?？]+)'
        path_match = re.search(path_pattern, raw_prompt, re.IGNORECASE)
        if path_match:
            target_path = path_match.group(1).strip()
            target_path = os.path.expanduser(target_path)
            
            # Check if it looks like a file path (has extension)
            if os.path.splitext(target_path)[1]:
                save_dir = os.path.dirname(target_path)
                save_filename = os.path.basename(target_path)
            else:
                save_dir = target_path
            
            # Strip the path portion from the prompt for cleaner image gen
            clean_prompt = raw_prompt[:path_match.start()] + raw_prompt[path_match.end():]
            clean_prompt = re.sub(r'\s+', ' ', clean_prompt).strip()
        else:
            clean_prompt = raw_prompt
        
        # Default save location
        if not save_dir:
            save_dir = os.getcwd()
        if not save_filename:
            ts = int(time.time())
            save_filename = f"grok_image_{ts}.jpeg"
        
        # Ensure directory exists
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, save_filename)
            
        api_key = os.environ.get("XAI_API_KEY")
        if not api_key:
            return "Error: XAI_API_KEY is missing."
            
        url = "https://api.x.ai/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "prompt": clean_prompt if clean_prompt else raw_prompt,
            "n": 1,
            "response_format": "url"
        }
        
        async with aiohttp.ClientSession() as session:
            # Step 1: Generate image
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return f"Error from xAI Image API: {resp.status} - {error_text}"
                data = await resp.json()
                
                if "data" not in data or len(data["data"]) == 0:
                    return f"Unexpected response format: {json.dumps(data)}"
                    
                img_url = data["data"][0].get("url")
            
            # Step 2: Download image to local path
            async with session.get(img_url) as img_resp:
                if img_resp.status != 200:
                    return f"Image generated but download failed (HTTP {img_resp.status}).\nURL: {img_url}"
                img_data = await img_resp.read()
                with open(save_path, "wb") as f:
                    f.write(img_data)
        
        size_kb = len(img_data) / 1024
        return (
            f"**Image saved!** `{save_path}` ({size_kb:.0f} KB)\n\n"
            f"![Generated Image]({img_url})"
        )

    async def _handle_gemini_image(self, messages: List[Dict[str, str]]) -> str:
        """Bypass for Gemini image generation model.
        
        Extracts any file path from the user prompt, generates the image
        via Gemini REST API with responseModalities=[IMAGE], and saves locally.
        Uses aiohttp to avoid blocking the event loop (keeps spinner alive).
        """
        import re
        import time
        import base64
        
        # Find the last user message
        raw_prompt = ""
        for m in reversed(messages):
            if m["role"] == "user":
                raw_prompt = m["content"]
                break
        if not raw_prompt:
            return "Error: No user prompt found for image generation."
        
        # Extract path from prompt (same logic as Grok)
        save_dir = None
        save_filename = None
        
        path_pattern = r'(?:到|to|save|保存|下载)\s*((?:/|~/)[^\s,，。!！?？]+)'
        path_match = re.search(path_pattern, raw_prompt, re.IGNORECASE)
        if path_match:
            target_path = path_match.group(1).strip()
            target_path = os.path.expanduser(target_path)
            if os.path.splitext(target_path)[1]:
                save_dir = os.path.dirname(target_path)
                save_filename = os.path.basename(target_path)
            else:
                save_dir = target_path
            clean_prompt = raw_prompt[:path_match.start()] + raw_prompt[path_match.end():]
            clean_prompt = re.sub(r'\s+', ' ', clean_prompt).strip()
        else:
            clean_prompt = raw_prompt
        
        if not save_dir:
            save_dir = os.getcwd()
        if not save_filename:
            ts = int(time.time())
            save_filename = f"gemini_image_{ts}.jpeg"
        
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, save_filename)
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return "Error: GEMINI_API_KEY is missing."
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": clean_prompt or raw_prompt}]}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "maxOutputTokens": 4096
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status != 200:
                    error_body = await resp.text()
                    return f"Error from Gemini Image API: {resp.status} - {error_body[:500]}"
                result = await resp.json()
        
        # Extract image and text from response
        candidates = result.get("candidates", [])
        if not candidates:
            return "Error: No candidates returned from Gemini."
        
        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = []
        image_saved = False
        
        for p in parts:
            if "text" in p:
                text_parts.append(p["text"])
            if "inlineData" in p:
                img_b64 = p["inlineData"].get("data", "")
                if img_b64:
                    img_bytes = base64.b64decode(img_b64)
                    with open(save_path, "wb") as f:
                        f.write(img_bytes)
                    image_saved = True
        
        if not image_saved:
            return "Error: Gemini returned no image data. " + " ".join(text_parts)
        
        size_kb = os.path.getsize(save_path) / 1024
        response_text = f"**Image saved!** `{save_path}` ({size_kb:.0f} KB)"
        if text_parts:
            response_text += f"\n\n{' '.join(text_parts)}"
        return response_text

    async def _handle_xai_responses(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """Bypass for xAI Responses API (Multi-Agent)."""
        api_key = os.environ.get("XAI_API_KEY")
        if not api_key:
            yield "Error: XAI_API_KEY is missing."
            return
            
        url = "https://api.x.ai/v1/responses"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # Responses API uses 'input' instead of 'messages'
        payload = {
            "model": self.model_name,
            "input": messages,
            "stream": True,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    yield f"Error from xAI Responses API: {resp.status} - {error_text}"
                    return
                
                # SSE parser for Responses API format
                # Events come as pairs: "event: <type>\n" then "data: <json>\n"
                async for line in resp.content:
                    decoded = line.decode('utf-8').strip()
                    if not decoded.startswith("data: "):
                        continue
                    data_str = decoded[6:]
                    try:
                        data = json.loads(data_str)
                        event_type = data.get("type", "")
                        if event_type == "response.output_text.delta":
                            delta_text = data.get("delta", "")
                            if delta_text:
                                yield delta_text
                    except json.JSONDecodeError:
                        pass

    async def _handle_minimax_stream(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """Bypass litellm for MiniMax streaming — direct SSE via aiohttp.
        
        LiteLLM buffers MiniMax responses instead of streaming them,
        which freezes the spinner. This handler does true SSE streaming
        and strips <think> tags from output.
        """
        import re
        api_key = os.environ.get("MINIMAX_API_KEY")
        if not api_key:
            yield "Error: MINIMAX_API_KEY is missing."
            return
        
        url = "https://api.minimaxi.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    yield f"Error from MiniMax API: {resp.status} - {error_text[:500]}"
                    return
                
                in_think = False
                async for line in resp.content:
                    decoded = line.decode('utf-8').strip()
                    if not decoded.startswith("data: "):
                        continue
                    data_str = decoded[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if not content:
                            continue
                        # Strip <think> blocks
                        if "<think>" in content:
                            in_think = True
                            content = content.split("<think>")[0]
                        if "</think>" in content:
                            in_think = False
                            content = content.split("</think>")[-1]
                            continue
                        if in_think:
                            continue
                        if content.strip():
                            yield content
                    except json.JSONDecodeError:
                        pass

    async def generate(self, messages: List[Dict[str, str]]) -> str:
        if self.provider == "grok" and "imagine" in self.model_name:
            return await self._handle_xai_image(messages)

        if self.provider == "gemini" and "image" in self.model_name:
            return await self._handle_gemini_image(messages)
            
        if self.provider == "grok" and "multi-agent" in self.model_name:
            result = []
            async for chunk in self._handle_xai_responses(messages):
                result.append(chunk)
            return "".join(result)

        if self.provider == "minimax":
            result = []
            async for chunk in self._handle_minimax_stream(messages):
                result.append(chunk)
            return "".join(result)

        kwargs = get_litellm_kwargs(self.provider, self.model_name)
        response = await acompletion(messages=messages, **kwargs)
        return response.choices[0].message.content

    async def stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
    ) -> AsyncIterator[str]:
        """Stream tokens as they arrive."""
        if self.provider == "grok" and "imagine" in self.model_name:
            result = await self._handle_xai_image(messages)
            yield result
            return

        if self.provider == "gemini" and "image" in self.model_name:
            result = await self._handle_gemini_image(messages)
            yield result
            return
            
        if self.provider == "grok" and "multi-agent" in self.model_name:
            async for chunk in self._handle_xai_responses(messages):
                yield chunk
            return

        if self.provider == "minimax":
            async for chunk in self._handle_minimax_stream(messages):
                yield chunk
            return

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
        """Stream a response, accumulating both text and tool_calls."""
        
        if self.provider == "grok" and "imagine" in self.model_name:
            result = await self._handle_xai_image(messages)
            if on_token:
                on_token(result)
            return StreamResult(text=result, finish_reason="stop")

        if self.provider == "gemini" and "image" in self.model_name:
            result = await self._handle_gemini_image(messages)
            if on_token:
                on_token(result)
            return StreamResult(text=result, finish_reason="stop")
            
        if self.provider == "grok" and "multi-agent" in self.model_name:
            text_parts = []
            async for chunk in self._handle_xai_responses(messages):
                text_parts.append(chunk)
                if on_token:
                    on_token(chunk)
            return StreamResult(text="".join(text_parts), finish_reason="stop")

        if self.provider == "minimax":
            text_parts = []
            async for chunk in self._handle_minimax_stream(messages):
                text_parts.append(chunk)
                if on_token:
                    on_token(chunk)
            return StreamResult(text="".join(text_parts), finish_reason="stop")

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
