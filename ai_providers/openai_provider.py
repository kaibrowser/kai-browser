"""
OpenAI Provider
OpenAI GPT API with streaming
"""

import json
import requests
from .base_provider import AIProvider


class OpenAIProvider(AIProvider):

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
        if not self.api_key:
            callback(
                {
                    "type": "error",
                    "content": "No OpenAI API key set. Please add one in Settings.",
                }
            )
            return {"success": False, "error": "No API key"}

        try:
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

            print(f"OpenAI API Status: {response.status_code}")

            if response.status_code != 200:
                error_msg = self._parse_error(response.text, response.status_code)
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
            print(f"OpenAI error: {error_msg}")
            callback({"type": "error", "content": error_msg})
            return {"success": False, "error": error_msg}

    def _parse_error(self, error_text: str, status_code: int) -> str:
        """Parse OpenAI API error into user-friendly message"""
        try:
            data = json.loads(error_text)
            error = data.get("error", {})
            error_type = error.get("type", "")
            message = error.get("message", "")
            code = error.get("code", "")

            if status_code == 401 or code == "invalid_api_key":
                return "Invalid OpenAI API key. Please check your key in Settings."
            elif status_code == 429:
                if "quota" in message.lower() or code == "insufficient_quota":
                    return "OpenAI quota exceeded. Please check your billing at platform.openai.com."
                else:
                    return (
                        "OpenAI rate limit hit. Please wait a moment before retrying."
                    )
            elif status_code == 400 and "model" in message.lower():
                return f"Model not found: {self.model}. Please check your selected model in Settings."
            elif status_code == 500:
                return "OpenAI internal error. Retrying..."
            elif status_code == 503:
                return "OpenAI API temporarily unavailable. Retrying..."
            elif message:
                return message

        except (json.JSONDecodeError, KeyError):
            pass

        return f"OpenAI API error {status_code}: {error_text[:200]}"
