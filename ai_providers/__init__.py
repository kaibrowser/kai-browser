"""
AI Providers package
Drop a new _provider.py file in this folder to add a provider
Import: from ai_providers import AIProviderManager
"""

from .base_provider import AIProvider
from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider


class AIProviderManager:

    def __init__(self, preferences_manager):
        self.preferences = preferences_manager
        self.providers = {}
        self._init_providers()

    def _init_providers(self):
        gemini_key = self.preferences.get_module_setting("AIProviders", "gemini_key")
        claude_key = self.preferences.get_module_setting("AIProviders", "claude_key")
        openai_key = self.preferences.get_module_setting("AIProviders", "openai_key")

        gemini_model = self.preferences.get_module_setting(
            "AIProviders", "gemini_model", "gemini-2.5-flash"
        )
        claude_model = self.preferences.get_module_setting(
            "AIProviders", "claude_model", "claude-sonnet-4-6"
        )
        openai_model = self.preferences.get_module_setting(
            "AIProviders", "openai_model", "o3-mini"
        )

        if gemini_key:
            self.providers["gemini"] = GeminiProvider(gemini_key, gemini_model)
        if claude_key:
            self.providers["claude"] = ClaudeProvider(claude_key, claude_model)
        if openai_key:
            self.providers["openai"] = OpenAIProvider(openai_key, openai_model)

    def get_provider(self, provider_name: str = None):
        if not provider_name:
            provider_name = self.preferences.get_module_setting(
                "AIProviders", "selected_provider", "gemini"
            )
        if provider_name in self.providers:
            return self.providers[provider_name]
        if self.providers:
            return list(self.providers.values())[0]
        return None

    def get_available_providers(self) -> list:
        return list(self.providers.keys())

    def set_api_key(self, provider: str, api_key: str):
        self.preferences.set_module_setting("AIProviders", f"{provider}_key", api_key)
        self._init_providers()

    def set_selected_provider(self, provider: str):
        self.preferences.set_module_setting(
            "AIProviders", "selected_provider", provider
        )

    def set_model(self, provider: str, model: str):
        self.preferences.set_module_setting("AIProviders", f"{provider}_model", model)
        self._init_providers()


__all__ = [
    "AIProvider",
    "ClaudeProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "AIProviderManager",
]

__all__ = ["AIProvider", "ClaudeProvider", "GeminiProvider", "OpenAIProvider"]
