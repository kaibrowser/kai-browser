"""
Gemini Provider
Google Gemini API with streaming
"""

import json
import requests
from .base_provider import AIProvider


class GeminiProvider(AIProvider):

    API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key=None, model="gemini-2.5-flash"):
        super().__init__(api_key)
        self.model = model

    def get_provider_name(self) -> str:
        return "Gemini"

    def get_available_models(self) -> list:
        return [
            ("gemini-2.5-flash", "Gemini 2.5 Flash"),
            ("gemini-3-flash-preview", "Gemini 3 Flash"),
        ]

    def generate_module_stream(self, prompt: str, module_context: dict, callback):
        if not self.api_key:
            callback(
                {
                    "type": "error",
                    "content": "No Gemini API key set. Please add one in Settings.",
                }
            )
            return {"success": False, "error": "No API key"}

        try:
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
            print(f"Gemini API Status: {response.status_code}")

            if response.status_code != 200:
                error_msg = self._parse_error(response.text)
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
            print(f"Gemini error: {error_msg}")
            callback({"type": "error", "content": error_msg})
            return {"success": False, "error": error_msg}

    def _parse_error(self, error_text: str) -> str:
        """Parse Gemini API error response into user-friendly message"""
        try:
            data = json.loads(error_text)
            error = data.get("error", {})
            details = error.get("details", [])

            quota_id = None
            quota_value = None
            model = None
            retry_delay = None

            for detail in details:
                if "violations" in detail:
                    v = detail["violations"][0]
                    quota_id = v.get("quotaId", "")
                    quota_value = v.get("quotaValue", "")
                    model = v.get("quotaDimensions", {}).get("model", "")
                if "retryDelay" in detail:
                    retry_delay = detail["retryDelay"].replace("s", "").split(".")[0]

            if quota_id:
                if "PerDay" in quota_id:
                    return (
                        f"Daily request limit reached ({quota_value} requests/day) "
                        f"for {model}. Resets at midnight UTC. "
                        f"Consider upgrading to a paid plan for higher limits."
                    )
                elif "PerMinute" in quota_id and "Token" in quota_id:
                    return (
                        f"Token rate limit hit for {model}. "
                        f"Please wait {retry_delay} seconds before retrying."
                    )
                elif "PerMinute" in quota_id:
                    return (
                        f"Request rate limit hit for {model} "
                        f"(free tier: 5 requests/minute). "
                        f"Please wait {retry_delay} seconds before retrying."
                    )

            return error.get("message", "Unknown API error").split("\n")[0]

        except (json.JSONDecodeError, KeyError, IndexError):
            return f"Gemini API error: {error_text[:200]}"
