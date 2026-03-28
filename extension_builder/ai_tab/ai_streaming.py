"""
AI Streaming Module
Handles streaming from AI providers with section parsing
"""

from PyQt6.QtCore import QThread, pyqtSignal
import time
import threading
import re


NO_RETRY_KEYWORDS = [
    "api key",
    "invalid",
    "unauthorized",
    "credit balance",
    "billing",
    "permission",
    "not found",
    "too large",
    "too low",
    "daily request limit",
    "quota exceeded",
]


class ResponseParser:
    """Parses [CHAT], [CODE], [REQUIREMENTS] sections from streaming response"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.raw_response = ""
        self.chat_text = ""
        self.code_text = ""
        self.requirements_text = ""
        self.current_section = None
        self.sections_found = set()

    def add_chunk(self, chunk):
        self.raw_response += chunk
        return self._parse_current()

    def _parse_current(self):
        result = {
            "chat": None,
            "code_chunk": None,
            "requirements": None,
            "section_changed": False,
        }

        response = self.raw_response

        chat_start = response.find("[CHAT]")
        chat_end = response.find("[/CHAT]")
        code_start = response.find("[CODE]")
        code_end = response.find("[/CODE]")
        req_start = response.find("[REQUIREMENTS]")
        req_end = response.find("[/REQUIREMENTS]")

        if chat_start != -1 and chat_end != -1 and "chat" not in self.sections_found:
            self.chat_text = response[chat_start + 6 : chat_end].strip()
            self.sections_found.add("chat")
            result["chat"] = self.chat_text
            result["section_changed"] = True

        if (
            req_start != -1
            and req_end != -1
            and "requirements" not in self.sections_found
        ):
            self.requirements_text = response[req_start + 14 : req_end].strip()
            self.sections_found.add("requirements")
            result["requirements"] = self.requirements_text
            result["section_changed"] = True

        if code_start != -1:
            if "code_started" not in self.sections_found:
                self.sections_found.add("code_started")
                result["section_changed"] = True

            code_content_start = code_start + 6

            if code_end != -1:
                new_code = response[code_content_start:code_end].strip()
            else:
                new_code = self._clean_partial_tags(
                    response[code_content_start:].strip()
                )

            if len(new_code) > len(self.code_text):
                result["code_chunk"] = new_code[len(self.code_text) :]
                self.code_text = new_code

            if code_end != -1 and "code" not in self.sections_found:
                self.sections_found.add("code")

        return result

    def _clean_partial_tags(self, code):
        if not code:
            return code
        code = code.rstrip()
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
        changed = True
        while changed:
            changed = False
            for pattern in end_patterns:
                if code.rstrip().endswith(pattern):
                    code = code.rstrip()[: -len(pattern)].rstrip()
                    changed = True
                    break
        return code

    def get_final_result(self):
        self._parse_current()
        if not self.sections_found:
            self.code_text = self._clean_code(self.raw_response)
        else:
            self.code_text = self._clean_code(self.code_text)

        return {
            "chat": self.chat_text,
            "code": self.code_text,
            "requirements": self.requirements_text,
            "packages_to_install": self._parse_packages(self.requirements_text),
            "sections_found": list(self.sections_found),
        }

    def _parse_packages(self, requirements_text):
        if not requirements_text:
            return []
        packages = []
        packages += re.findall(
            r"📦\s*pip\s+install\s+([a-zA-Z0-9_-]+)", requirements_text
        )
        packages += re.findall(r"pip\s+install\s+([a-zA-Z0-9_-]+)", requirements_text)
        skip = {
            "no",
            "none",
            "only",
            "uses",
            "needed",
            "required",
            "install",
            "installation",
        }
        seen, result = set(), []
        for pkg in packages:
            pl = pkg.lower().strip()
            if pl not in seen and pl not in skip:
                seen.add(pl)
                result.append(pkg)
        return result

    def _clean_code(self, code):
        if not code:
            return ""
        code = re.sub(r"^```python\s*\n", "", code, flags=re.MULTILINE)
        code = re.sub(r"^```\s*\n", "", code, flags=re.MULTILINE)
        code = re.sub(r"\n```\s*$", "", code, flags=re.MULTILINE)
        code = re.sub(r"```\s*$", "", code)
        code = re.sub(r"\[/?CODE\]?", "", code, flags=re.IGNORECASE)
        code = re.sub(r"\[/?CHAT\]?", "", code, flags=re.IGNORECASE)
        code = re.sub(r"\[/?REQUIREMENTS?\]?", "", code, flags=re.IGNORECASE)
        code = re.sub(r"\[\\/?CODE\]?", "", code, flags=re.IGNORECASE)
        code = re.sub(r"\[\\/?CHAT\]?", "", code, flags=re.IGNORECASE)
        code = re.sub(r"\[\\/?REQUIREMENTS?\]?", "", code, flags=re.IGNORECASE)
        code = re.sub(r"\[\s*$", "", code)
        code = re.sub(r"\[/?\s*$", "", code)
        code = re.sub(r"\[\\?\s*$", "", code)
        return code.strip()


class AIStreamingThread(QThread):
    """Streaming thread with section parsing and simple retry logic"""

    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)
    chunk = pyqtSignal(str)
    chat_message = pyqtSignal(str)
    error = pyqtSignal(str, str, bool)
    retry_attempt = pyqtSignal(int, int)

    def __init__(self, provider, prompt, context, timeout=10, max_retries=3):
        super().__init__()
        self.provider = provider
        self.prompt = prompt
        self.context = context
        self.timeout = timeout  # max silence before giving up entirely
        self.max_retries = max_retries
        self.current_retry = 0
        self.parser = ResponseParser()
        self.last_chunk_time = 0
        self.is_streaming = False
        self.total_tokens = 0
        self.stall_threshold = 20  # warn user after 20s silence
        self.should_stop = False
        self.generation_stopped = False

    def run(self):
        while self.current_retry <= self.max_retries and not self.should_stop:
            if self.current_retry > 0:
                self.retry_attempt.emit(self.current_retry, self.max_retries)
                self.progress.emit(f"Retry {self.current_retry}/{self.max_retries}...")
                time.sleep(2)

            success = self._attempt_generation()

            if success or self.should_stop:
                return

            self.current_retry += 1

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
        result_container = {"result": None, "exception": None, "completed": False}
        try:
            self.progress.emit("Connecting to AI...")
            self.last_chunk_time = time.time()
            self.parser.reset()
            self.generation_stopped = False
            self.chat_sent = False

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
                    parsed = self.parser.add_chunk(content)

                    if parsed["chat"] and not self.chat_sent:
                        self.chat_message.emit(parsed["chat"])
                        self.chat_sent = True
                        self.progress.emit("Generating code...")

                    if parsed["code_chunk"]:
                        if (
                            parsed["section_changed"]
                            and "code_started" in self.parser.sections_found
                        ):
                            self.chunk.emit("__CLEAR__")
                        self.chunk.emit(parsed["code_chunk"])

                elif event_type == "done":
                    self.is_streaming = False
                    self.progress.emit("Complete!")

                elif event_type == "error":
                    self.is_streaming = False
                    self._handle_error(content)

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

            self._gen_thread = threading.Thread(target=run_generation, daemon=True)
            self._gen_thread.start()

            while not result_container["completed"] and not self.should_stop:
                time.sleep(0.1)
                if self.is_streaming:
                    elapsed = time.time() - self.last_chunk_time
                    if elapsed > self.stall_threshold:
                        self.progress.emit(f"⚠️ Connection slow ({int(elapsed)}s)...")
                    if elapsed > self.timeout:
                        self.generation_stopped = True
                        self.is_streaming = False
                        self._handle_error(f"No response for {self.timeout}s")
                        return False

            if self.should_stop:
                self.generation_stopped = True
                self.is_streaming = False
                return True

            if result_container["exception"]:
                raise result_container["exception"]

            result = result_container["result"]

            if result and result.get("success"):
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
            self._handle_error(str(e))
            return False

    def _handle_error(self, error_msg: str):
        print(f"Error received: {error_msg}")
        can_retry = self.current_retry < self.max_retries and not any(
            kw in error_msg.lower() for kw in NO_RETRY_KEYWORDS
        )
        self.error.emit("error", error_msg, can_retry)
        if can_retry:
            self.progress.emit("Retrying...")
        else:
            self.progress.emit(error_msg)
            self.finished.emit({"success": False, "error": error_msg, "code": ""})

    def stop(self):
        self.should_stop = True
        self.is_streaming = False
        # Give the inner gen_thread 3s to finish cleanly, then abandon it.
        # It's a daemon thread so it won't block process exit.
        if hasattr(self, "_gen_thread") and self._gen_thread.is_alive():
            self._gen_thread.join(timeout=3)

    def get_stats(self):
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
