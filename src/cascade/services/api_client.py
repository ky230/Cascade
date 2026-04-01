from litellm import acompletion
from cascade.services.api_config import get_litellm_kwargs
from typing import List, Dict, AsyncIterator, Optional

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
