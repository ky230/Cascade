import os
from dotenv import load_dotenv

load_dotenv()

CUSTOM_PROVIDERS = {
    "glm": {
        "prefix": "zhipu/",
        "env_key": "GLM_API_KEY",
        "base_url": None
    },
    "deepseek": {
        "prefix": "deepseek/",
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": None
    },
    "kimi": {
        "prefix": "moonshot/",
        "env_key": "MOONSHOT_API_KEY",
        "base_url": None
    }
}

def get_litellm_kwargs(provider_name: str, model_name: str) -> dict:
    """Resolve LiteLLM kwargs depending on whether it's native or custom."""
    if provider_name in CUSTOM_PROVIDERS:
        cfg = CUSTOM_PROVIDERS[provider_name]
        kwargs = {"model": f"{cfg['prefix']}{model_name}"}
        
        # Explicitly pass api key for custom ones
        api_key = os.getenv(cfg["env_key"])
        if api_key:
            kwargs["api_key"] = api_key
        return kwargs
    
    # For OpenAI/Anthropic/Gemini, litellm natively identifies the model and grabs os.environ
    return {"model": model_name}
