"""
Base AI Provider
All providers inherit from this class
"""

from abc import ABC, abstractmethod

try:
    from ai_examples import AIExamples

    EXAMPLES_AVAILABLE = True
except ImportError:
    EXAMPLES_AVAILABLE = False


class AIProvider(ABC):
    """Base class for all AI providers"""

    def __init__(self, api_key=None):
        self.api_key = api_key

    @abstractmethod
    def generate_module_stream(self, prompt: str, module_context: dict, callback):
        """
        Stream generation - callback receives event dicts:
        {"type": "start"}
        {"type": "chunk", "content": "..."}
        {"type": "done"}
        {"type": "error", "content": "user-friendly message"}
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Display name shown in UI"""
        pass

    @abstractmethod
    def get_available_models(self) -> list:
        """List of (model_id, display_name) tuples"""
        pass

    def generate_module(self, prompt: str, module_context: dict) -> dict:
        """Non-streaming fallback - collects all chunks"""
        chunks = []

        def collect(event):
            if event["type"] == "chunk":
                chunks.append(event["content"])

        result = self.generate_module_stream(prompt, module_context, collect)
        if result["success"]:
            result["code"] = "".join(chunks)
        return result

    def _build_prompt(self, prompt: str, module_context: dict) -> str:
        """Build full prompt using AIExamples if available"""
        if EXAMPLES_AVAILABLE:
            return AIExamples.build_prompt(prompt, module_context)
        base = f"User request: {prompt}\n\n"
        if module_context.get("current_code"):
            base += f"MODIFY THIS CODE:\n```python\n{module_context['current_code']}\n```\n\n"
        return base
