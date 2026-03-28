"""
Claude Provider
Anthropic Claude API using official SDK
"""

import json
from .base_provider import AIProvider


class ClaudeProvider(AIProvider):

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
            callback(
                {
                    "type": "error",
                    "content": "No Claude API key set. Please add one in Settings.",
                }
            )
            return {"success": False, "error": "No API key"}

        try:
            full_prompt = self._build_prompt(prompt, module_context)
            client = anthropic.Anthropic(api_key=self.api_key)

            callback({"type": "start", "content": ""})
            full_code = ""

            with client.messages.stream(
                model=self.model,
                max_tokens=20000,
                messages=[{"role": "user", "content": full_prompt}],
            ) as stream:
                for text in stream.text_stream:
                    full_code += text
                    callback({"type": "chunk", "content": text})

            callback({"type": "done", "content": ""})
            return {"success": True, "code": full_code}

        except Exception as e:
            error_msg = self._parse_error(str(e))
            print(f"Claude error: {error_msg}")
            callback({"type": "error", "content": error_msg})
            return {"success": False, "error": error_msg}

    def _parse_error(self, error_msg: str) -> str:
        """Parse Claude SDK exception into user-friendly message"""
        msg_lower = error_msg.lower()

        if "credit balance" in msg_lower or "too low" in msg_lower:
            return "Your Anthropic credit balance is too low. Please add credits at console.anthropic.com."
        if "authentication_error" in msg_lower or "invalid_api_key" in msg_lower:
            return "Invalid Claude API key. Please check your key in Settings."
        if "rate_limit_error" in msg_lower:
            return "Claude rate limit hit. Please wait a moment before retrying."
        if "overloaded_error" in msg_lower:
            return "Anthropic API is temporarily overloaded. Retrying..."
        if "permission_error" in msg_lower:
            return "Your API key does not have permission for this model."
        if "not_found_error" in msg_lower:
            return "Model not found. Please check your selected model in Settings."
        if "request_too_large" in msg_lower:
            return "Request too large. Try clearing conversation history."
        if "api_error" in msg_lower:
            return "Anthropic internal error. Retrying..."

        # Connection drop — retryable, keep message clean
        if (
            "incomplete chunked read" in msg_lower
            or "peer closed connection" in msg_lower
        ):
            return "Connection dropped mid-stream. Retrying..."
        if (
            "connection" in msg_lower
            or "network" in msg_lower
            or "timeout" in msg_lower
        ):
            return "Connection issue. Retrying..."

        # Fallback — try to extract clean message from JSON
        try:
            json_start = error_msg.find("{")
            if json_start != -1:
                data = json.loads(error_msg[json_start:])
                message = data.get("error", {}).get("message", "")
                if message:
                    return message
        except (json.JSONDecodeError, KeyError):
            pass

        return error_msg
