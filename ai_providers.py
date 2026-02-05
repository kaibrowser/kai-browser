"""
AI Providers - Real Streaming Support
Consolidated version - duplicate code moved to base class
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

    # CONSOLIDATED: Non-streaming fallback (was duplicated in all 3 providers)
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

    # CONSOLIDATED: Fallback prompt builder (was duplicated in all 3 providers)
    def _build_fallback_prompt(self, prompt: str, context: dict) -> str:
        """Build basic prompt when AIExamples not available"""
        base_prompt = f"User request: {prompt}\n\n"
        if context.get("current_code"):
            base_prompt += f"MODIFY THIS EXISTING CODE:\n```python\n{context['current_code']}\n```\n\n"
        return base_prompt

    # CONSOLIDATED: Prompt building logic (was duplicated)
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

            # Build prompt using consolidated method
            full_prompt = self._build_prompt(prompt, module_context)

            # Streaming endpoint
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

            # Stream response
            response = requests.post(
                url, json=payload, stream=True, timeout=self.timeout
            )

            if response.status_code != 200:
                error_msg = f"API error: {response.status_code}"
                callback({"type": "error", "content": error_msg})
                return {"success": False, "error": error_msg}

            full_code = ""

            # Process SSE stream
            for line in response.iter_lines():
                if line:
                    line_text = line.decode("utf-8")

                    # Skip SSE formatting
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


class ClaudeProvider(AIProvider):
    """Anthropic Claude API with streaming"""

    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key=None, model="claude-sonnet-4-5-20250929"):
        super().__init__(api_key)
        self.model = model

    def get_provider_name(self) -> str:
        return "Claude"

    def get_available_models(self) -> list:
        return [
            ("claude-opus-4-5-20251101", "Claude Opus 4.5"),
            ("claude-sonnet-4-5-20250929", "Claude Sonnet 4.5"),
            ("claude-haiku-4-5-20251001", "Claude 4.5 Haiku"),
        ]

    def generate_module_stream(self, prompt: str, module_context: dict, callback):
        """Stream generation with real-time chunks"""
        try:
            if not self.api_key:
                callback({"type": "error", "content": "No API key"})
                return {"success": False, "error": "No API key"}

            # Build prompt using consolidated method
            full_prompt = self._build_prompt(prompt, module_context)

            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }

            payload = {
                "model": self.model,
                "max_tokens": 32000,
                "messages": [{"role": "user", "content": full_prompt}],
                "stream": True,
            }

            callback({"type": "start", "content": ""})

            # Stream response
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                stream=True,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                error_msg = f"API error: {response.status_code}"
                callback({"type": "error", "content": error_msg})
                return {"success": False, "error": error_msg}

            full_code = ""

            # Process SSE stream
            for line in response.iter_lines():
                if line:
                    line_text = line.decode("utf-8")

                    # Skip SSE formatting
                    if line_text.startswith("data: "):
                        data_json = line_text[6:]

                        # Skip ping events
                        if data_json.strip() == "[DONE]":
                            continue

                        try:
                            data = json.loads(data_json)

                            # Handle different event types
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    chunk = delta.get("text", "")
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


class OpenAIProvider(AIProvider):
    """OpenAI GPT API with streaming"""

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key=None, model="gpt-4.1"):
        super().__init__(api_key)
        self.model = model

    def get_provider_name(self) -> str:
        return "OpenAI"

    def get_available_models(self) -> list:
        return [
            ("gpt-4.1", "GPT-4.1"),
        ]

    def generate_module_stream(self, prompt: str, module_context: dict, callback):
        """Stream generation with real-time chunks"""
        try:
            if not self.api_key:
                callback({"type": "error", "content": "No API key"})
                return {"success": False, "error": "No API key"}

            # Build prompt using consolidated method
            full_prompt = self._build_prompt(prompt, module_context)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": full_prompt}],
                "temperature": 0.7,
                "max_tokens": 8192,
                "stream": True,
            }

            callback({"type": "start", "content": ""})

            # Stream response
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                stream=True,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                error_msg = f"API error: {response.status_code}"
                callback({"type": "error", "content": error_msg})
                return {"success": False, "error": error_msg}

            full_code = ""

            # Process SSE stream
            for line in response.iter_lines():
                if line:
                    line_text = line.decode("utf-8")

                    # Skip SSE formatting
                    if line_text.startswith("data: "):
                        data_json = line_text[6:]

                        # Skip done marker
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
