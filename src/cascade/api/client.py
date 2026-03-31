class ModelClient:
    """Abstract interface layer for LLM routing."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name

    async def generate(self, prompt: str) -> str:
        """Generate response (stub implementation)."""
        return f"Stub response for: {prompt}"
