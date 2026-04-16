"""Rough token estimation for LLM messages.

Reference: claude-code tokenEstimation.ts L203-435
Aligned with Claude Code's block-aware estimation logic:
- string content: len(text) / 4
- list content: sum of per-block estimates
- text block: len(block["text"]) / 4
- tool_use block: name + json.dumps(input)
- tool_result block: recursive over nested content
- image/document block: fixed 2000 tokens
- thinking block: len(block["thinking"]) / 4
- fallback: json.dumps(block) / 4
"""
import json


def rough_token_estimate(text: str) -> int:
    """Estimate tokens for a plain text string (~4 bytes per token)."""
    if not text:
        return 0
    return round(len(text.encode("utf-8")) / 4)


def _estimate_block_tokens(block: dict) -> int:
    """Estimate tokens for a single content block."""
    block_type = block.get("type", "")

    if block_type == "text":
        return rough_token_estimate(block.get("text", ""))

    if block_type == "tool_use":
        name_tokens = rough_token_estimate(block.get("name", ""))
        try:
            input_str = json.dumps(block.get("input", {}))
        except (TypeError, ValueError):
            input_str = str(block.get("input", ""))
        return name_tokens + rough_token_estimate(input_str)

    if block_type == "tool_result":
        # Recursive: tool_result can contain nested content blocks
        nested = block.get("content", "")
        if isinstance(nested, str):
            return rough_token_estimate(nested)
        if isinstance(nested, list):
            return sum(_estimate_block_tokens(b) for b in nested if isinstance(b, dict))
        return 1

    if block_type in ("image", "document"):
        # Fixed estimate for binary/base64 content
        return 2000

    if block_type == "thinking":
        return rough_token_estimate(block.get("thinking", ""))

    if block_type == "redacted_thinking":
        return rough_token_estimate(block.get("data", ""))

    # Fallback: serialize the whole block
    try:
        return rough_token_estimate(json.dumps(block))
    except (TypeError, ValueError):
        return rough_token_estimate(str(block))


def estimate_message_tokens(messages: list[dict]) -> int:
    """Estimate total tokens across a list of LLM messages.

    Handles both string and block-list content formats.
    """
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += rough_token_estimate(content)
        elif isinstance(content, list):
            total += sum(
                _estimate_block_tokens(b) for b in content
                if isinstance(b, dict)
            )
        else:
            total += rough_token_estimate(str(content))
    return total
