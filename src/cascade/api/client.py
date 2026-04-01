from litellm import acompletion
from cascade.api.config import get_litellm_kwargs
from typing import List, Dict

class ModelClient:
    """Universal interface layer for all LLMs using LiteLLM."""
    
    def __init__(self, provider: str, model_name: str):
        self.provider = provider
        self.model_name = model_name

    async def generate(self, messages: List[Dict[str, str]]) -> str:
        """Call universal LLM endpoint asynchronously with full message history."""
        kwargs = get_litellm_kwargs(self.provider, self.model_name)
        
        response = await acompletion(
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
