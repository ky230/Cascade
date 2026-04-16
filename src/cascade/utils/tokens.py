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


def precise_token_count(messages: list[dict], litellm_model: str) -> int:
    """Precise token count via LiteLLM tokenizer.

    Args:
        messages: LLM message list
        litellm_model: LiteLLM model key (e.g. "gemini/gemini-3.1-flash-lite-preview")
    Falls back to estimate_message_tokens() on error.
    """
    try:
        from litellm import token_counter as litellm_token_counter
        return litellm_token_counter(model=litellm_model, messages=messages)
    except Exception:
        return estimate_message_tokens(messages)


def precise_token_count_by_role(messages: list[dict], litellm_model: str) -> dict:
    """Token count broken down by role, via LiteLLM tokenizer."""
    breakdown = {"system": 0, "user": 0, "assistant": 0, "tool": 0}
    for m in messages:
        role = m.get("role", "user")
        bucket = role if role in breakdown else "tool"
        try:
            from litellm import token_counter as litellm_token_counter
            tokens = litellm_token_counter(model=litellm_model, messages=[m])
        except Exception:
            content = m.get("content", "")
            tokens = rough_token_estimate(str(content))
        breakdown[bucket] += tokens
    return breakdown

