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
        kwargs["model"] = f"zhipu/{model_name}"
        kwargs["api_key"] = os.getenv("ZHIPUAI_API_KEY")
    elif provider == "deepseek":
        kwargs["model"] = f"deepseek/{model_name}"
        kwargs["api_base"] = "https://api.deepseek.com"
        kwargs["api_key"] = os.getenv("DEEPSEEK_API_KEY")
    elif provider == "kimi":
        kwargs["model"] = f"moonshot/{model_name}"
        kwargs["api_base"] = "https://api.moonshot.cn/v1"
        kwargs["api_key"] = os.getenv("MOONSHOT_API_KEY")

    return kwargs
