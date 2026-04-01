from typing import List, Dict
from cascade.api.client import ModelClient

class Agent:
    """Core conversational agent with multi-turn memory."""
    
    def __init__(self, provider: str, model_name: str, system_prompt: str = "You are a helpful Cascade Agent."):
        self.client = ModelClient(provider=provider, model_name=model_name)
        self.memory: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

    async def chat(self, user_message: str) -> str:
        """Process a single conversational turn with memory."""
        self.memory.append({"role": "user", "content": user_message})
        response = await self.client.generate(self.memory)
        self.memory.append({"role": "assistant", "content": response})
        return response
