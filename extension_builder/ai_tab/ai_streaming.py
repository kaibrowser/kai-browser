"""
Enhanced AI Streaming Module
Now parses [CHAT], [CODE], [REQUIREMENTS] sections from AI response
Updated: Extracts pip install packages for automatic installation
"""

from PyQt6.QtCore import QThread, pyqtSignal, QTimer
import time
import threading
import re


# Human-friendly error messages
ERROR_MESSAGES = {
    "timeout": {
        "title": "Connection Timeout",
        "message": "The AI took too long to respond. This usually means the server is busy.",
        "retry": True,
        "user_action": "Retrying automatically...",
    },
    "rate_limit": {
        "title": "Rate Limit Reached",
        "message": "You've made too many requests. The API has temporary limits.",
        "retry": True,
        "user_action": "Waiting 30 seconds before retry...",
    },
    "api_unavailable": {
        "title": "API Unavailable",
        "message": "The AI service is currently unavailable or experiencing issues.",
        "retry": True,
        "user_action": "Retrying in a moment...",
    },
    "network_error": {
        "title": "Network Error",
        "message": "Cannot connect to the AI service. Check your internet connection.",
        "retry": True,
        "user_action": "Retrying connection...",
    },
    "invalid_api_key": {
        "title": "Invalid API Key",
        "message": "Your API key is invalid or has expired. Please update it in Settings.",
        "retry": False,
        "user_action": "Please check your API key in Settings.",
    },
    "token_limit": {
        "title": "Token Limit Exceeded",
        "message": "The request is too large. Try a shorter prompt or clear conversation history.",
        "retry": False,
        "user_action": "Try simplifying your request or clearing history.",
    },
    "server_error": {
        "title": "Server Error",
        "message": "The AI service encountered an internal error.",
        "retry": True,
        "user_action": "Retrying automatically...",
    },
    "stalled": {
        "title": "Connection Stalled",
        "message": "The response stopped unexpectedly. The connection may have dropped.",
        "retry": True,
        "user_action": "Retrying connection...",
    },
    "stopped": {
        "title": "Stopped",
        "message": "Generation stopped by user.",
        "retry": False,
        "user_action": "Ready for new request.",
    },
    "unknown": {
        "title": "Unexpected Error",
        "message": "Something went wrong. This might be a temporary issue.",
        "retry": True,
        "user_action": "Retrying automatically...",
    },
}


# Packages bundled with KaiBrowser - don't need installation
BUNDLED_PACKAGES = {
    # # PyQt6
    # "pyqt6",
    # "pyqt6-qt6",
    # "pyqt6-sip",
    # # Web/Network
    # "requests",
    # "urllib3",
    # "certifi",
    # "charset-normalizer",
    # "charset_normalizer",
    # "chardet",
    # "idna",
    # "pysocks",
    # "socks",
    # "websockets",
    # "brotli",
    # # HTML/Parsing
    # "bs4",
    # "beautifulsoup4",
    # "lxml",
    # "soupsieve",
    # "html2text",
    # # Images
    # "pil",
    # "pillow",
    # # "qrcode",
    # "pypng",
    # # Media
    # "yt-dlp",
    # "yt_dlp",
    # "mutagen",
    # "eyed3",
    # # Screenshots
    # "mss",
    # # Crypto/Security
    # "cryptography",
    # "pynacl",
    # "nacl",
    # "keyring",
    # # System
    # "psutil",
    # "netifaces",
    # "ifaddr",
    # "pynput",
    # # Data formats
    # "yaml",
    # "pyyaml",
    # "markdown",
    # "pygments",
    # # CLI/Output
    # "rich",
    # "click",
    # "colorama",
    # # Utilities
    # "filetype",
    # "packaging",
    # "platformdirs",
    # "typing-extensions",
    # "typing_extensions",
    # "six",
}


class ResponseParser:
    """Parses structured AI response into chat, code, and requirements sections"""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset parser state"""
        self.raw_response = ""
        self.chat_text = ""
        self.code_text = ""
        self.requirements_text = ""
        self.current_section = None
        self.sections_found = set()

    def add_chunk(self, chunk):
        """
        Add a chunk to the response and parse incrementally
        Returns: dict with any newly completed content
        """
        self.raw_response += chunk
        return self._parse_current()

    def _parse_current(self):
        """Parse current response and extract sections"""
        result = {
            "chat": None,
            "code_chunk": None,
            "requirements": None,
            "section_changed": False,
        }

        response = self.raw_response

        # Check for section markers
        chat_start = response.find("[CHAT]")
        chat_end = response.find("[/CHAT]")
        code_start = response.find("[CODE]")
        code_end = response.find("[/CODE]")
        req_start = response.find("[REQUIREMENTS]")
        req_end = response.find("[/REQUIREMENTS]")

        # Extract complete CHAT section
        if chat_start != -1 and chat_end != -1 and "chat" not in self.sections_found:
            self.chat_text = response[chat_start + 6 : chat_end].strip()
            self.sections_found.add("chat")
            result["chat"] = self.chat_text
            result["section_changed"] = True

        # Extract complete REQUIREMENTS section
        if (
            req_start != -1
            and req_end != -1
            and "requirements" not in self.sections_found
        ):
            self.requirements_text = response[req_start + 14 : req_end].strip()
            self.sections_found.add("requirements")
            result["requirements"] = self.requirements_text
            result["section_changed"] = True

        # Handle CODE section - stream incrementally
        if code_start != -1:
            if "code_started" not in self.sections_found:
                self.sections_found.add("code_started")
                result["section_changed"] = True

            # Get code content so far
            code_content_start = code_start + 6

            if code_end != -1:
                # Complete code section
                new_code = response[code_content_start:code_end].strip()
            else:
                # Still streaming code - clean partial tags from end
                new_code = response[code_content_start:].strip()
                new_code = self._clean_partial_tags(new_code)

            # Calculate new chunk (what we haven't sent yet)
            if len(new_code) > len(self.code_text):
                new_chunk = new_code[len(self.code_text) :]
                self.code_text = new_code
                result["code_chunk"] = new_chunk

            if code_end != -1 and "code" not in self.sections_found:
                self.sections_found.add("code")

        return result

    def _clean_partial_tags(self, code):
        """Remove partial/malformed tags from the end of streaming code"""
        if not code:
            return code

        code = code.rstrip()

        # Patterns to strip from end (order matters - check longer patterns first)
        end_patterns = [
            "[/CODE]",
            "[/CODE",
            "[/COD",
            "[/CO",
            "[/C",
            "[/",
            "[\\CODE]",
            "[\\CODE",
            "[\\COD",
            "[\\CO",
            "[\\C",
            "[\\",
            "[\\/CODE]",
            "[\\/CODE",
            "[\\/COD",
            "[\\/CO",
            "[\\/C",
            "[REQUIREMENTS]",
            "[REQUIREMENTS",
            "[REQUIREMENT",
            "[REQUIRE",
            "[REQ",
            "[/REQUIREMENTS",
            "[/REQUIREMENT",
            "[/REQUIRE",
            "[/REQ",
        ]

        # Keep cleaning until no more patterns found
        changed = True
        while changed:
            changed = False
            for pattern in end_patterns:
                if code.rstrip().endswith(pattern):
                    code = code.rstrip()[: -len(pattern)].rstrip()
                    changed = True
                    break

            # # Handle trailing '[' separately
            # if code.rstrip().endswith("["):
            #     code = code.rstrip()[:-1].rstrip()
            #     changed = True

        return code

    def get_final_result(self):
        """Get final parsed result after streaming completes"""
        # Try one more parse in case sections completed
        self._parse_current()

        # If no sections found, treat entire response as code (fallback)
        if not self.sections_found:
            self.code_text = self._clean_code(self.raw_response)
        else:
            self.code_text = self._clean_code(self.code_text)

        # Parse packages from requirements
        packages_to_install = self._parse_packages(self.requirements_text)

        return {
            "chat": self.chat_text,
            "code": self.code_text,
            "requirements": self.requirements_text,
            "packages_to_install": packages_to_install,
            "sections_found": list(self.sections_found),
        }

    def _parse_packages(self, requirements_text):
        """
        Extract package names that need pip install
        Returns list of package names (excluding bundled ones)
        """
        if not requirements_text:
            return []

        packages = []

        # Pattern 1: "📦 pip install package-name"
        pattern1 = re.findall(
            r"📦\s*pip\s+install\s+([a-zA-Z0-9_-]+)", requirements_text
        )
        packages.extend(pattern1)

        # Pattern 2: "pip install package-name" (without emoji)
        pattern2 = re.findall(r"pip\s+install\s+([a-zA-Z0-9_-]+)", requirements_text)
        packages.extend(pattern2)

        # Pattern 3: "• package-name" or "- package-name" that looks like a package
        pattern3 = re.findall(
            r"[•\-]\s*([a-zA-Z][a-zA-Z0-9_-]*)\s*(?:\(|$|\n)", requirements_text
        )
        # Only add if it looks like a package name (not a sentence)
        for pkg in pattern3:
            if len(pkg) < 30 and pkg.lower() not in [
                "no",
                "none",
                "requires",
                "internet",
                "connection",
            ]:
                packages.append(pkg)

        # Deduplicate and normalize
        seen = set()
        result = []
        for pkg in packages:
            pkg_lower = pkg.lower().strip()
            # Skip if already seen
            if pkg_lower in seen:
                continue
            # Skip if bundled
            if pkg_lower in BUNDLED_PACKAGES:
                continue
            # Skip common false positives
            if pkg_lower in [
                "no",
                "none",
                "only",
                "uses",
                "needed",
                "required",
                "install",
                "installation",
            ]:
                continue
            seen.add(pkg_lower)
            result.append(pkg)

        return result

    def _clean_code(self, code):
        """Clean code of markdown fences and any remaining tags"""
        if not code:
            return ""

        # Strip markdown fences
        code = re.sub(r"^```python\s*\n", "", code, flags=re.MULTILINE)
        code = re.sub(r"^```\s*\n", "", code, flags=re.MULTILINE)
        code = re.sub(r"\n```\s*$", "", code, flags=re.MULTILINE)
        code = re.sub(r"```\s*$", "", code)

        # Remove any section tags that leaked through (normal and malformed)
        code = re.sub(r"\[/?CODE\]?", "", code, flags=re.IGNORECASE)
        code = re.sub(r"\[/?CHAT\]?", "", code, flags=re.IGNORECASE)
        code = re.sub(r"\[/?REQUIREMENTS\]?", "", code, flags=re.IGNORECASE)

        # Remove malformed tags with backslash
        code = re.sub(r"\[\\/?CODE\]?", "", code, flags=re.IGNORECASE)
        code = re.sub(r"\[\\/?CHAT\]?", "", code, flags=re.IGNORECASE)
        code = re.sub(r"\[\\/?REQUIREMENTS\]?", "", code, flags=re.IGNORECASE)

        # Clean trailing brackets or partial tags
        code = re.sub(r"\[\s*$", "", code)
        code = re.sub(r"\[/?\s*$", "", code)
        code = re.sub(r"\[\\?\s*$", "", code)

        # Clean any remaining standalone brackets at end of lines
        # code = re.sub(r"\[\s*\n", "\n", code)

        return code.strip()


class AIStreamingThread(QThread):
    """Enhanced streaming thread with section parsing"""

    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)
    chunk = pyqtSignal(str)  # Code chunks
    chat_message = pyqtSignal(str)  # Chat messages from AI
    error = pyqtSignal(str, str, bool)  # error_type, message, can_retry
    retry_attempt = pyqtSignal(int, int)  # current_attempt, max_attempts

    def __init__(self, provider, prompt, context, timeout=10, max_retries=3):
        super().__init__()
        self.provider = provider
        self.prompt = prompt
        self.context = context
        self.timeout = timeout
        self.max_retries = max_retries
        self.current_retry = 0

        self.parser = ResponseParser()
        self.last_chunk_time = 0
        self.is_streaming = False
        self.total_tokens = 0
        self.stall_threshold = 5
        self.should_stop = False
        self.generation_stopped = False

    def run(self):
        """Main execution with retry logic"""
        while self.current_retry <= self.max_retries and not self.should_stop:
            if self.current_retry > 0:
                self.retry_attempt.emit(self.current_retry, self.max_retries)
                self.progress.emit(f"Retry {self.current_retry}/{self.max_retries}...")
                time.sleep(2)

            success = self._attempt_generation()

            if success or self.should_stop:
                return

            self.current_retry += 1

        # All retries exhausted or stopped
        if self.should_stop:
            self.finished.emit(
                {
                    "success": False,
                    "error": "Stopped by user",
                    "code": "",
                    "stopped": True,
                }
            )
        else:
            self.finished.emit(
                {
                    "success": False,
                    "error": "Maximum retry attempts reached",
                    "code": "",
                }
            )

    def _attempt_generation(self):
        """Single generation attempt with section parsing"""
        try:
            self.progress.emit("Connecting to AI...")
            self.last_chunk_time = time.time()
            self.parser.reset()
            self.generation_stopped = False
            self.chat_sent = False

            # timeout_timer = QTimer()
            # timeout_timer.timeout.connect(self._check_timeout)
            # timeout_timer.start(1000)

            def handle_stream_event(event):
                if self.should_stop:
                    self.generation_stopped = True
                    return

                event_type = event.get("type")
                content = event.get("content", "")

                if event_type == "start":
                    self.is_streaming = True
                    self.progress.emit("AI is thinking...")
                    self.last_chunk_time = time.time()

                elif event_type == "chunk":
                    self.last_chunk_time = time.time()

                    # Parse the chunk
                    parsed = self.parser.add_chunk(content)

                    # Emit chat message when complete
                    if parsed["chat"] and not self.chat_sent:
                        self.chat_message.emit(parsed["chat"])
                        self.chat_sent = True
                        self.progress.emit("Generating code...")

                    # Emit code chunks for live preview
                    if parsed["code_chunk"]:
                        if (
                            parsed["section_changed"]
                            and "code_started" in self.parser.sections_found
                        ):
                            # Clear preview when code section starts
                            self.chunk.emit("__CLEAR__")
                        self.chunk.emit(parsed["code_chunk"])

                elif event_type == "done":
                    self.is_streaming = False
                    self.progress.emit("Complete!")
                    # timeout_timer.stop()

                elif event_type == "error":
                    self.is_streaming = False
                    error_type = self._categorize_error(content)
                    self._handle_error(error_type, content)
                    # timeout_timer.stop()

                if "tokens" in event:
                    self.total_tokens = event["tokens"]

            # Run generation in background thread
            result_container = {"result": None, "exception": None, "completed": False}

            def run_generation():
                try:
                    result = self.provider.generate_module_stream(
                        self.prompt, self.context, handle_stream_event
                    )
                    result_container["result"] = result
                except Exception as e:
                    result_container["exception"] = e
                finally:
                    result_container["completed"] = True

            gen_thread = threading.Thread(target=run_generation, daemon=True)
            gen_thread.start()

            # Monitor for completion or stop signal
            while not result_container["completed"] and not self.should_stop:
                time.sleep(0.1)

            # timeout_timer.stop()

            if self.should_stop:
                self.generation_stopped = True
                self.is_streaming = False
                return True

            if result_container["exception"]:
                raise result_container["exception"]

            result = result_container["result"]

            if result and result.get("success"):
                # Get final parsed result
                final = self.parser.get_final_result()

                result["code"] = final["code"]
                result["chat"] = final["chat"]
                result["requirements"] = final["requirements"]
                result["packages_to_install"] = final["packages_to_install"]
                result["tokens"] = self.total_tokens

                self.finished.emit(result)
                return True

            return False

        except Exception as e:
            self.is_streaming = False
            error_msg = str(e)
            error_type = self._categorize_error(error_msg)
            return self._handle_error(error_type, error_msg)

    def _categorize_error(self, error_msg):
        """Categorize error from message content"""
        error_lower = error_msg.lower()

        if "timeout" in error_lower:
            return "timeout"
        elif "rate limit" in error_lower or "too many requests" in error_lower:
            return "rate_limit"
        elif (
            "api key" in error_lower
            or "unauthorized" in error_lower
            or "401" in error_lower
        ):
            return "invalid_api_key"
        elif "token" in error_lower and "limit" in error_lower:
            return "token_limit"
        elif "network" in error_lower or "connection" in error_lower:
            return "network_error"
        elif (
            "503" in error_lower or "502" in error_lower or "unavailable" in error_lower
        ):
            return "api_unavailable"
        elif "500" in error_lower or "internal" in error_lower:
            return "server_error"
        else:
            return "unknown"

    def _handle_error(self, error_type, error_msg):
        """Handle error with human-friendly message"""
        error_info = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"])

        friendly_msg = f"{error_info['title']}: {error_info['message']}"
        can_retry = error_info["retry"] and self.current_retry < self.max_retries

        self.error.emit(error_type, friendly_msg, can_retry)

        if can_retry:
            self.progress.emit(error_info["user_action"])
            return False
        else:
            self.progress.emit(error_info["user_action"])
            self.finished.emit(
                {
                    "success": False,
                    "error": friendly_msg,
                    "code": "",
                    "error_type": error_type,
                }
            )
            return True

    def _check_timeout(self):
        """Check for timeout, stall, or stop signal"""
        if self.should_stop:
            self.is_streaming = False
            self.quit()
            return

        # if not self.is_streaming:
        #     return

        # elapsed = time.time() - self.last_chunk_time

        # if elapsed > self.stall_threshold and elapsed < self.timeout:
        #     self.progress.emit(f"Connection slow ({int(elapsed)}s)...")

        # if elapsed > self.timeout:
        #     self.is_streaming = False
        #     self._handle_error("timeout", f"No response for {self.timeout}s")
        #     self.quit()

    def stop(self):
        """Stop thread gracefully"""
        self.should_stop = True
        self.is_streaming = False

    def get_stats(self):
        """Get generation statistics"""
        return {
            "total_tokens": self.total_tokens,
            "code_length": len(self.parser.code_text),
            "retry_count": self.current_retry,
            "streaming_time": (
                time.time() - self.last_chunk_time if self.is_streaming else 0
            ),
            "was_stopped": self.generation_stopped,
            "sections_found": list(self.parser.sections_found),
        }
