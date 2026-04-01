from __future__ import annotations
import os

def get_litellm_kwargs(provider: str, model_name: str) -> dict:
    """Return configured model mapping and API keys for LiteLLM."""
    kwargs = {"model": model_name}

    if provider == "openai":
        kwargs["model"] = f"openai/{model_name}"
    elif provider == "anthropic":
        kwargs["model"] = f"anthropic/{model_name}"
        kwargs["api_key"] = os.getenv("ANTHROPIC_API_KEY")
    elif provider == "glm":
        kwargs["model"] = f"openai/{model_name}"
        kwargs["api_base"] = "https://open.bigmodel.cn/api/paas/v4/"
        kwargs["api_key"] = os.getenv("ZHIPUAI_API_KEY") or os.getenv("GLM_API_KEY")
    elif provider == "deepseek":
        kwargs["model"] = f"deepseek/{model_name}"
        kwargs["api_base"] = "https://api.deepseek.com"
        kwargs["api_key"] = os.getenv("DEEPSEEK_API_KEY")
    elif provider == "kimi":
        kwargs["model"] = f"moonshot/{model_name}"
        kwargs["api_base"] = "https://api.moonshot.cn/v1"
        kwargs["api_key"] = os.getenv("MOONSHOT_API_KEY")
    elif provider == "gemini":
        kwargs["model"] = f"gemini/{model_name}"
        kwargs["api_key"] = os.getenv("GEMINI_API_KEY")
    elif provider == "qwen":
        kwargs["model"] = f"openai/{model_name}"
        kwargs["api_base"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        kwargs["api_key"] = os.getenv("DASHSCOPE_API_KEY")
    elif provider == "grok":
        kwargs["model"] = f"openai/{model_name}"
        kwargs["api_base"] = "https://api.x.ai/v1"
        kwargs["api_key"] = os.getenv("XAI_API_KEY")
    elif provider == "minimax":
        kwargs["model"] = f"openai/{model_name}"
        kwargs["api_base"] = "https://api.minimaxi.com/v1"
        kwargs["api_key"] = os.getenv("MINIMAX_API_KEY")

    return kwargs
