"""
AI Providers - Real Streaming Support
Fixed: Removed response.text calls that broke streaming
"""

import requests
from abc import ABC, abstractmethod
import time
import json
import re

try:
    from ai_examples import AIExamples

    EXAMPLES_AVAILABLE = True
except ImportError:
    EXAMPLES_AVAILABLE = False


class AIProvider(ABC):
    """Base class for AI providers with shared functionality"""

    def __init__(self, api_key=None):
        self.api_key = api_key
        self.timeout = 120
        self.max_retries = 2

    @abstractmethod
    def generate_module_stream(self, prompt: str, module_context: dict, callback):
        """Generate module with streaming - callback receives chunks"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name for UI display"""
        pass

    @abstractmethod
    def get_available_models(self) -> list:
        """Return list of available models for this provider"""
        pass

    def generate_module(self, prompt: str, module_context: dict) -> dict:
        """Non-streaming fallback - collects chunks from streaming"""
        chunks = []

        def collect_chunks(data):
            if data["type"] == "chunk":
                chunks.append(data["content"])

        result = self.generate_module_stream(prompt, module_context, collect_chunks)

        if result["success"]:
            result["code"] = "".join(chunks)

        return result

    def _build_fallback_prompt(self, prompt: str, context: dict) -> str:
        """Build basic prompt when AIExamples not available"""
        base_prompt = f"User request: {prompt}\n\n"
        if context.get("current_code"):
            base_prompt += f"MODIFY THIS EXISTING CODE:\n```python\n{context['current_code']}\n```\n\n"
        return base_prompt

    def _build_prompt(self, prompt: str, module_context: dict) -> str:
        """Build full prompt using AIExamples if available, fallback otherwise"""
        if EXAMPLES_AVAILABLE:
            return AIExamples.build_prompt(prompt, module_context)
        else:
            return self._build_fallback_prompt(prompt, module_context)


class GeminiProvider(AIProvider):
    """Google Gemini API with streaming"""

    API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key=None, model="gemini-2.5-flash"):
        super().__init__(api_key)
        self.model = model

    def get_provider_name(self) -> str:
        return "Gemini"

    def get_available_models(self) -> list:
        return [
            ("gemini-2.5-flash", "Gemini 2.5 Flash"),
        ]

    def generate_module_stream(self, prompt: str, module_context: dict, callback):
        """Stream generation with real-time chunks"""
        try:
            if not self.api_key:
                callback({"type": "error", "content": "No API key"})
                return {"success": False, "error": "No API key"}

            full_prompt = self._build_prompt(prompt, module_context)

            url = f"{self.API_URL}/{self.model}:streamGenerateContent?key={self.api_key}&alt=sse"

            payload = {
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 8192,
                    "topP": 0.95,
                },
            }

            callback({"type": "start", "content": ""})

            response = requests.post(url, json=payload, stream=True, timeout=(10, 30))

            # FIXED: Only log status code, don't consume stream
            print(f"Gemini API Status: {response.status_code}")

            if response.status_code != 200:
                # Only read response body on error
                error_text = response.text
                error_msg = f"API error: {response.status_code} - {error_text}"
                callback({"type": "error", "content": error_msg})
                return {"success": False, "error": error_msg}

            full_code = ""

            for line in response.iter_lines():
                if line:
                    line_text = line.decode("utf-8")

                    if line_text.startswith("data: "):
                        data_json = line_text[6:]

                        try:
                            data = json.loads(data_json)

                            if "candidates" in data and data["candidates"]:
                                content = data["candidates"][0].get("content", {})
                                parts = content.get("parts", [])

                                if parts and "text" in parts[0]:
                                    chunk = parts[0]["text"]
                                    full_code += chunk
                                    callback({"type": "chunk", "content": chunk})

                        except json.JSONDecodeError:
                            continue

            callback({"type": "done", "content": ""})
            return {"success": True, "code": full_code}

        except Exception as e:
            error_msg = str(e)
            callback({"type": "error", "content": error_msg})
            return {"success": False, "error": error_msg}


########################
## Claude provider class new uses official SDK for better streaming support and reliability.08:35 14/03/26
########################
class ClaudeProvider(AIProvider):
    """Anthropic Claude API using official SDK - reliable streaming"""

    def __init__(self, api_key=None, model="claude-sonnet-4-6"):
        super().__init__(api_key)
        self.model = model

    def get_provider_name(self) -> str:
        return "Claude"

    def get_available_models(self) -> list:
        return [
            ("claude-opus-4-6", "Claude Opus 4.6"),
            ("claude-sonnet-4-6", "Claude Sonnet 4.6"),
            ("claude-opus-4-5-20251101", "Claude Opus 4.5"),
            ("claude-sonnet-4-5-20250929", "Claude Sonnet 4.5"),
            ("claude-haiku-4-5-20251001", "Claude Haiku 4.5"),
        ]

    def generate_module_stream(self, prompt: str, module_context: dict, callback):
        try:
            import anthropic
        except ImportError:
            callback(
                {
                    "type": "error",
                    "content": "anthropic SDK not installed. Run: pip install anthropic",
                }
            )
            return {"success": False, "error": "anthropic SDK not installed"}

        if not self.api_key:
            callback({"type": "error", "content": "No API key"})
            return {"success": False, "error": "No API key"}

        try:
            full_prompt = self._build_prompt(prompt, module_context)
            client = anthropic.Anthropic(api_key=self.api_key)

            callback({"type": "start", "content": ""})

            full_code = ""

            with client.messages.stream(
                model=self.model,
                max_tokens=64000,
                messages=[{"role": "user", "content": full_prompt}],
            ) as stream:
                for text in stream.text_stream:
                    full_code += text
                    callback({"type": "chunk", "content": text})

            callback({"type": "done", "content": ""})
            return {"success": True, "code": full_code}

        except Exception as e:
            error_msg = str(e)
            print(f"Claude SDK error: {error_msg}")
            callback({"type": "error", "content": error_msg})
            return {"success": False, "error": error_msg}


############################################


class OpenAIProvider(AIProvider):
    """OpenAI GPT API with streaming"""

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key=None, model="gpt-5.2"):
        super().__init__(api_key)
        self.model = model

    def get_provider_name(self) -> str:
        return "OpenAI"

    def get_available_models(self) -> list:
        return [
            ("gpt-5.2", "GPT-5.2"),
            ("gpt-5-nano-2025-08-07", "GPT-5 Nano"),
            ("gpt-4.1", "GPT-4.1"),
        ]

    def generate_module_stream(self, prompt: str, module_context: dict, callback):
        """Stream generation with real-time chunks"""
        try:
            if not self.api_key:
                callback({"type": "error", "content": "No API key"})
                return {"success": False, "error": "No API key"}

            full_prompt = self._build_prompt(prompt, module_context)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": full_prompt}],
                "stream": True,
            }

            new_models = ("gpt-5", "o1", "o3", "o4")
            if self.model.startswith(new_models):
                payload["max_completion_tokens"] = 8192
            else:
                payload["max_tokens"] = 8192
                payload["temperature"] = 0.7

            callback({"type": "start", "content": ""})

            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                stream=True,
                timeout=(10, 30),
            )

            # FIXED: Only log status code, don't consume stream
            print(f"OpenAI API Status: {response.status_code}")

            if response.status_code != 200:
                # Only read response body on error
                error_text = response.text
                error_msg = f"API error: {response.status_code} - {error_text}"
                callback({"type": "error", "content": error_msg})
                return {"success": False, "error": error_msg}

            full_code = ""

            for line in response.iter_lines():
                if line:
                    line_text = line.decode("utf-8")

                    if line_text.startswith("data: "):
                        data_json = line_text[6:]

                        if data_json.strip() == "[DONE]":
                            continue

                        try:
                            data = json.loads(data_json)

                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                if "content" in delta:
                                    chunk = delta["content"]
                                    full_code += chunk
                                    callback({"type": "chunk", "content": chunk})

                        except json.JSONDecodeError:
                            continue

            callback({"type": "done", "content": ""})
            return {"success": True, "code": full_code}

        except Exception as e:
            error_msg = str(e)
            callback({"type": "error", "content": error_msg})
            return {"success": False, "error": error_msg}


class AIProviderManager:
    """Manages AI provider selection"""

    def __init__(self, preferences_manager):
        self.preferences = preferences_manager
        self.providers = {}
        self._init_providers()

    def _init_providers(self):
        """Initialize providers"""
        gemini_key = self.preferences.get_module_setting("AIProviders", "gemini_key")
        claude_key = self.preferences.get_module_setting("AIProviders", "claude_key")
        openai_key = self.preferences.get_module_setting("AIProviders", "openai_key")

        gemini_model = self.preferences.get_module_setting(
            "AIProviders", "gemini_model", "gemini-2.5-flash"
        )
        claude_model = self.preferences.get_module_setting(
            "AIProviders", "claude_model", "claude-sonnet-4-5-20250929"
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

    def get_provider(self, provider_name: str = None) -> AIProvider:
        """Get AI provider"""
        if not provider_name:
            selected = self.preferences.get_module_setting(
                "AIProviders", "selected_provider", "gemini"
            )
            provider_name = selected

        if provider_name in self.providers:
            return self.providers[provider_name]

        if self.providers:
            return list(self.providers.values())[0]

        return None

    def get_available_providers(self) -> list:
        """Get list of available provider names"""
        return list(self.providers.keys())

    def set_api_key(self, provider: str, api_key: str):
        """Save API key for a provider"""
        self.preferences.set_module_setting("AIProviders", f"{provider}_key", api_key)
        self._init_providers()

    def set_selected_provider(self, provider: str):
        """Set the user's preferred provider"""
        self.preferences.set_module_setting(
            "AIProviders", "selected_provider", provider
        )

    def set_model(self, provider: str, model: str):
        """Set the model for a specific provider"""
        self.preferences.set_module_setting("AIProviders", f"{provider}_model", model)
        self._init_providers()
