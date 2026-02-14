"""
AI Tab - Main Widget
Updated with chat messages, requirements display, package installation, and animated progress
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QPlainTextEdit,
    QFrame,
    QMessageBox,
    QScrollArea,
    QCheckBox,
    QDialog,
    QProgressBar,
)
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from pathlib import Path
import subprocess
import sys
import time

from .ai_streaming import AIStreamingThread
from .chat_display import ChatDisplayManager
from .code_manager import CodeManager
from .error_handler import ErrorHandler
from ..utils import ModuleLoader, build_ai_context
from .ai_performance_monitor import AIPerformanceMonitor


class PipInstallThread(QThread):
    """Background thread for pip install"""

    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, packages, dependencies_dir):
        super().__init__()
        self.packages = packages
        self.dependencies_dir = dependencies_dir

    def run(self):
        """Run pip install for each package"""
        failed = []
        succeeded = []

        for package in self.packages:
            self.progress.emit(f"Installing {package}...")

            try:
                # Try pip3 first, fall back to pip
                pip_cmd = "pip3"
                try:
                    subprocess.run(
                        [pip_cmd, "--version"], capture_output=True, timeout=5
                    )
                except FileNotFoundError:
                    pip_cmd = "pip"

                result = subprocess.run(
                    [
                        pip_cmd,
                        "install",
                        "--target",
                        str(self.dependencies_dir),
                        package,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if result.returncode == 0:
                    succeeded.append(package)
                    self.progress.emit(f"✅ Installed {package}")
                else:
                    failed.append(package)
                    self.progress.emit(f"❌ Failed to install {package}")

            except subprocess.TimeoutExpired:
                failed.append(package)
                self.progress.emit(f"❌ Timeout installing {package}")
            except FileNotFoundError:
                self.finished.emit(
                    False, "pip not found. Please install Python/pip on your system."
                )
                return
            except Exception as e:
                failed.append(package)
                self.progress.emit(f"❌ Error installing {package}: {str(e)}")

        if failed:
            self.finished.emit(False, f"Failed to install: {', '.join(failed)}")
        else:
            self.finished.emit(True, f"Successfully installed: {', '.join(succeeded)}")


class InstallPackagesDialog(QDialog):
    """Dialog for installing required packages"""

    def __init__(self, packages, dependencies_dir, parent=None):
        super().__init__(parent)
        self.packages = packages
        self.dependencies_dir = dependencies_dir
        self.install_thread = None
        self.install_accepted = False

        self.setWindowTitle("Install Required Packages")
        self.setMinimumWidth(450)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(16)

        # Header
        header = QLabel("📦 Additional Packages Required")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        # Package list
        packages_text = "\n".join([f"  • {pkg}" for pkg in self.packages])
        packages_label = QLabel(f"This extension needs:\n\n{packages_text}")
        packages_label.setStyleSheet(
            "font-size: 13px; padding: 10px; background-color: #f5f5f5; border-radius: 6px;"
        )
        layout.addWidget(packages_label)

        # Warning
        warning = QLabel(
            "⚠️ Install at your own risk.\n"
            "KaiBrowser is not responsible for third-party packages."
        )
        warning.setStyleSheet("font-size: 11px; color: #666; padding: 8px;")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        # Progress area (hidden initially)
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_frame)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Preparing...")
        self.progress_label.setStyleSheet("font-size: 11px; color: #666;")
        progress_layout.addWidget(self.progress_label)

        layout.addWidget(self.progress_frame)

        # Buttons
        button_layout = QHBoxLayout()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f1f5f9;
                color: #0f172a;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """
        )
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.skip_btn = QPushButton("Skip - Save Anyway")
        self.skip_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f1f5f9;
                color: #0f172a;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """
        )
        self.skip_btn.clicked.connect(self.skip_install)
        button_layout.addWidget(self.skip_btn)

        self.install_btn = QPushButton("Install && Continue")
        self.install_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #7c3aed;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6d28d9;
            }
        """
        )
        self.install_btn.clicked.connect(self.start_install)
        button_layout.addWidget(self.install_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def skip_install(self):
        """Skip installation but continue with save"""
        self.install_accepted = False
        self.accept()

    def start_install(self):
        """Start package installation"""
        self.install_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.cancel_btn.setText("Cancel Install")
        self.progress_frame.setVisible(True)

        self.install_thread = PipInstallThread(self.packages, self.dependencies_dir)
        self.install_thread.progress.connect(self.on_progress)
        self.install_thread.finished.connect(self.on_install_finished)
        self.install_thread.start()

    def on_progress(self, message):
        """Update progress label"""
        self.progress_label.setText(message)

    def on_install_finished(self, success, message):
        """Handle installation complete"""
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)

        if success:
            self.progress_label.setText(f"✅ {message}")
            self.install_accepted = True
            QTimer.singleShot(1000, self.accept)
        else:
            self.progress_label.setText(f"❌ {message}")
            self.install_btn.setEnabled(True)
            self.install_btn.setText("Retry Install")
            self.skip_btn.setEnabled(True)
            self.cancel_btn.setText("Cancel")

    def reject(self):
        """Cancel dialog"""
        if self.install_thread and self.install_thread.isRunning():
            self.install_thread.terminate()
            self.install_thread.wait()
        super().reject()


class AnimatedProgressTimer:
    """Creates animated dots for progress indication"""

    def __init__(self, label, base_message="Generating code"):
        self.label = label
        self.base_message = base_message
        self.dot_count = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_dots)

    def start(self, message=None):
        """Start animated dots"""
        if message:
            self.base_message = message
        self.dot_count = 0
        self.timer.start(500)
        self._update_dots()

    def stop(self):
        """Stop animation"""
        self.timer.stop()

    def _update_dots(self):
        """Cycle through dot patterns"""
        dots = [".", "..", "..."]
        current_dots = dots[self.dot_count % 3]
        self.label.setText(f"⚡ {self.base_message}{current_dots}")
        self.dot_count += 1


class AIBuilderTab(QWidget):
    """Main AI builder interface with chat support and package installation"""

    def __init__(self, browser_core, modules_dir, ai_manager):
        super().__init__()
        self.browser_core = browser_core
        self.modules_dir = modules_dir
        self.ai_manager = ai_manager
        self.ai_thread = None

        # Initialize performance monitor
        try:
            self.performance_monitor = AIPerformanceMonitor(browser_core)
        except Exception as e:
            print(f"Failed to load performance monitor: {e}")
            self.performance_monitor = None

        # Get dependencies directory from browser or create default
        if hasattr(browser_core, "dependencies_dir"):
            self.dependencies_dir = browser_core.dependencies_dir
        else:
            # Fallback
            if getattr(sys, "frozen", False):
                self.dependencies_dir = Path(sys.executable).parent / "dependencies"
            else:
                self.dependencies_dir = (
                    Path(__file__).parent.parent.parent / "dependencies"
                )
            self.dependencies_dir.mkdir(exist_ok=True)

        # Store pending packages for installation
        self.pending_packages = []

        # Initialize managers
        self.loader = ModuleLoader(browser_core, modules_dir)
        self.code_manager = CodeManager(browser_core, modules_dir, self.loader)
        self.error_handler = ErrorHandler(self, max_attempts=3)

        self.chat_display = None
        self.progress_animation = None
        self.code_manager.load_session()

        self.setup_ui()

    def setup_ui(self):
        """Set up UI"""
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        header = self._create_header()
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: white; }")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(20, 20, 20, 20)

        self.chat_container = QVBoxLayout()
        self.chat_container.setSpacing(16)
        content_layout.addLayout(self.chat_container)

        self.chat_display = ChatDisplayManager(self.chat_container)

        code_frame = self._create_code_section()
        content_layout.addWidget(code_frame)
        content_layout.addStretch()

        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)

        input_frame = self._create_input_section()
        layout.addWidget(input_frame)

        self.setLayout(layout)

        self.progress_animation = AnimatedProgressTimer(self.status_label)

        if self.code_manager.get_code():
            self.code_preview.setPlainText(self.code_manager.get_code())
            self.save_btn.setEnabled(True)
        if self.code_manager.get_history():
            self.chat_display.rebuild_display(self.code_manager.get_history())

        self.update_api_status()

    def _create_header(self):
        """Create header"""
        header = QFrame()
        header.setStyleSheet(
            """
            QFrame {
                background-color: #f8f9fa;
                border-bottom: 1px solid #e0e0e0;
                padding: 8px 16px;
            }
        """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.api_status_label = QLabel()
        self.api_status_label.setStyleSheet("font-size: 11px; color: #666;")
        header_layout.addWidget(self.api_status_label)

        self.autofix_checkbox = QCheckBox("Auto-fix errors")
        self.autofix_checkbox.setChecked(self.error_handler.auto_fix_enabled)
        self.autofix_checkbox.toggled.connect(self.toggle_autofix)
        self.autofix_checkbox.setStyleSheet(
            """
            QCheckBox {
                font-size: 11px;
                color: #666;
                padding: 0 8px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }
        """
        )
        header_layout.addWidget(self.autofix_checkbox)

        header_layout.addStretch()

        clear_btn = QPushButton("↻ Clear")
        clear_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
                color: #666;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """
        )
        clear_btn.clicked.connect(self.clear_conversation)
        header_layout.addWidget(clear_btn)

        return header

    def _create_code_section(self):
        """Create code preview"""
        code_frame = QFrame()
        code_frame.setStyleSheet(
            """
            QFrame {
                background-color: #1e1e1e;
                border-radius: 8px;
                padding: 0;
            }
        """
        )
        code_layout = QVBoxLayout(code_frame)
        code_layout.setContentsMargins(0, 0, 0, 0)
        code_layout.setSpacing(0)

        code_header = QFrame()
        code_header.setStyleSheet(
            """
            QFrame {
                background-color: #2d2d2d;
                border-radius: 8px 8px 0 0;
                padding: 8px 12px;
            }
        """
        )
        code_header_layout = QHBoxLayout(code_header)
        code_header_layout.setContentsMargins(0, 0, 0, 0)

        code_label = QLabel("Generated Code")
        code_label.setStyleSheet("color: #d4d4d4; font-size: 11px; font-weight: bold;")
        code_header_layout.addWidget(code_label)
        code_header_layout.addStretch()

        self.save_btn = QPushButton("Add Extension")
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #7c3aed;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6d28d9;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """
        )
        self.save_btn.clicked.connect(self.save_extension)
        code_header_layout.addWidget(self.save_btn)

        code_layout.addWidget(code_header)

        self.code_preview = QTextEdit()
        self.code_preview.setFont(QFont("Monospace", 10))
        self.code_preview.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                border-radius: 0 0 8px 8px;
                padding: 12px;
            }
        """
        )
        self.code_preview.setMinimumHeight(300)
        code_layout.addWidget(self.code_preview)

        return code_frame

    def _create_input_section(self):
        """Create input area"""
        input_frame = QFrame()
        input_frame.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border-top: none;
                padding: 16px;
            }
        """
        )
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 11px; color: #666; padding: 0 4px;")
        input_layout.addWidget(self.status_label)

        input_container = QHBoxLayout()
        input_container.setSpacing(8)

        self.message_input = QPlainTextEdit()
        self.message_input.setPlaceholderText(
            "Describe your extension or ask a question..."
        )
        self.message_input.setMaximumHeight(80)
        self.message_input.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QPlainTextEdit:focus {
                border: 1px solid #7c3aed;
                background-color: white;
            }
        """
        )
        input_container.addWidget(self.message_input, 1)

        self.send_btn = QPushButton("→")
        self.send_btn.clicked.connect(self.handle_send_button)
        self.send_btn.setProperty("mode", "send")
        self.send_btn.setStyleSheet(
            """
            QPushButton {
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 18px;
                font-weight: bold;
                min-width: 50px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #38bdf8, stop:1 #8b5cf6
                );
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #60a5fa, stop:1 #a78bfa
                );
            }
            QPushButton:pressed {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2563eb, stop:1 #7c3aed
                );
            }
            QPushButton:disabled {
                background: #c7c7c7;
                color: #666;
            }
        """
        )

        input_container.addWidget(self.send_btn)
        input_layout.addLayout(input_container)

        return input_frame

    def handle_send_button(self):
        """Handle send button click - either send or stop"""
        if self.send_btn.property("mode") == "send":
            self.send_message()
        else:
            self.stop_generation()

    def stop_generation(self):
        """Stop AI generation"""
        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.stop()
            self.ai_thread.wait()

        self.progress_animation.stop()
        self.status_label.setText("⏹️ Stopped")
        self.set_send_button_mode("send")

    def set_send_button_mode(self, mode):
        """Switch button between send and stop modes"""
        if mode == "send":
            self.send_btn.setText("→")
            self.send_btn.setProperty("mode", "send")
            self.send_btn.setEnabled(True)
            self.send_btn.setStyleSheet(
                """
                QPushButton {
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 20px;
                    font-size: 18px;
                    font-weight: bold;
                    min-width: 50px;
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 #38bdf8, stop:1 #8b5cf6
                    );
                }
                QPushButton:hover {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 #60a5fa, stop:1 #a78bfa
                    );
                }
                QPushButton:pressed {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 #2563eb, stop:1 #7c3aed
                    );
                }
                QPushButton:disabled {
                    background: #c7c7c7;
                    color: #666;
                }
            """
            )
        else:
            self.send_btn.setText("■")
            self.send_btn.setProperty("mode", "stop")
            self.send_btn.setEnabled(True)
            self.send_btn.setStyleSheet(
                """
                QPushButton {
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 20px;
                    font-size: 18px;
                    font-weight: bold;
                    min-width: 50px;
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 #ef4444, stop:1 #dc2626
                    );
                }
                QPushButton:hover {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 #f87171, stop:1 #ef4444
                    );
                }
                QPushButton:pressed {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 #dc2626, stop:1 #b91c1c
                    );
                }
            """
            )

    def toggle_autofix(self, checked):
        """Toggle auto-fix"""
        self.error_handler.set_auto_fix_enabled(checked)

    def send_message(self):
        """Send message with chat support"""
        message = self.message_input.toPlainText().strip()

        if not message:
            return

        provider = self.ai_manager.get_provider()
        if not provider:
            QMessageBox.warning(
                self, "No API Key", "Please add an API key in Settings."
            )
            return

        # Add user message to history and display
        self.code_manager.add_to_history("user", message)
        self.chat_display.add_user_message(message)
        self.code_manager.save_session()

        # Track start time and request BEFORE clearing input
        self.generation_start_time = time.time()
        self.current_request = message  # ← Save it here

        self.message_input.clear()
        self.set_send_button_mode("stop")
        self.progress_animation.start("AI is thinking")
        self.generation_start_time = time.time()

        context = build_ai_context(
            message, self.code_manager.get_history(), self.code_manager.get_code()
        )

        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.stop()
            self.ai_thread.wait()

        # Create thread
        self.ai_thread = AIStreamingThread(
            provider, message, context, timeout=30, max_retries=3
        )

        # Connect signals
        self.ai_thread.progress.connect(self.on_progress_update)
        self.ai_thread.chunk.connect(self.on_code_chunk)
        self.ai_thread.chat_message.connect(self.on_chat_message)
        self.ai_thread.finished.connect(self.on_generation_complete)
        self.ai_thread.error.connect(self.on_ai_error)
        self.ai_thread.retry_attempt.connect(self.on_retry_attempt)

        self.ai_thread.start()

    def on_chat_message(self, message):
        """Handle chat message from AI"""
        self.chat_display.add_assistant_message(message)

        # Add to history
        self.code_manager.add_to_history(
            "assistant", message, status=message, type="chat"
        )

        # Scroll chat to bottom
        self._scroll_chat_to_bottom()

    def _scroll_chat_to_bottom(self):
        """Scroll chat area to bottom"""
        parent = self.chat_container.parent()
        while parent:
            if isinstance(parent, QScrollArea):
                scrollbar = parent.verticalScrollBar()
                QTimer.singleShot(100, lambda: scrollbar.setValue(scrollbar.maximum()))
                break
            parent = parent.parent() if hasattr(parent, "parent") else None

    def on_progress_update(self, message):
        """Handle progress updates with animation"""
        if message == "Generating code...":
            self.progress_animation.start("Generating code")
        elif message == "AI is thinking...":
            self.progress_animation.start("AI is thinking")
        elif message == "Connecting to AI...":
            self.progress_animation.start("Connecting to AI")
        elif message.startswith("Retry"):
            self.progress_animation.start(message.rstrip("."))
        elif "Complete!" in message or "Done!" in message or "Error" in message:
            self.progress_animation.stop()
            self.status_label.setText(f"⚡ {message}")
        elif message.startswith("Connection slow"):
            self.progress_animation.base_message = message.rstrip(".")
        else:
            self.progress_animation.stop()
            self.status_label.setText(f"⚡ {message}")

    def on_code_chunk(self, chunk):
        """Handle code chunks"""
        if chunk == "__CLEAR__":
            self.code_preview.clear()
            return

        cursor = self.code_preview.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.code_preview.setTextCursor(cursor)

        scrollbar = self.code_preview.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_ai_error(self, error_type, friendly_message, can_retry):
        """Handle AI errors with user-friendly messages"""
        self.progress_animation.stop()
        self.status_label.setText(f"⚠️ {friendly_message}")

        # Log the error
        if self.performance_monitor:
            duration = time.time() - getattr(self, "generation_start_time", time.time())
            user_request = getattr(self, "current_request", "Unknown")

            self.performance_monitor.log_generation(
                request_text=user_request,
                success=False,
                duration_seconds=duration,
                error=Exception(f"{error_type}: {friendly_message}"),
                code_length=0,
                prompt_size=0,
            )

        if not can_retry:
            QMessageBox.warning(self, "Cannot Continue", friendly_message)

    def on_retry_attempt(self, current, maximum):
        """Handle retry attempts"""
        retry_msg = f"🔄 Retrying ({current}/{maximum})"
        self.progress_animation.start(retry_msg)

    def on_generation_complete(self, result):
        """Handle generation completion"""
        self.progress_animation.stop()
        self.set_send_button_mode("send")

        # Log performance data
        if self.performance_monitor and self.ai_thread:
            stats = self.ai_thread.get_stats()

            # Calculate actual duration
            duration = time.time() - getattr(self, "generation_start_time", time.time())

            # Get user's original request from message input or history
            user_request = getattr(self, "current_request", "Unknown")

            self.performance_monitor.log_generation(
                request_text=user_request or "Unknown",
                success=result.get("success", False),
                duration_seconds=duration,
                error=(
                    None
                    if result.get("success")
                    else Exception(result.get("error", "Unknown error"))
                ),
                code_length=len(result.get("code", "")),
                prompt_size=(
                    len(str(self.ai_thread.context))
                    if hasattr(self.ai_thread, "context")
                    else 0
                ),
            )

        if result.get("code"):
            clean_code = result["code"]
            self.code_manager.update_code(clean_code)
            self.code_preview.setPlainText(clean_code)
            self.save_btn.setEnabled(True)
            self.status_label.setText("✅ Done!")

            # Store pending packages for installation
            self.pending_packages = result.get("packages_to_install", [])

            # Add code generation to history
            self.code_manager.add_to_history(
                "assistant",
                "Code generated",
                status="✅ Extension ready!",
                code=clean_code,
                type="code",
            )

            # Show completion indicator in chat if no chat message was received
            if not result.get("chat"):
                self.chat_display.add_assistant_message(
                    "✅ Code generated successfully!"
                )

            # Show requirements info in chat
            if result.get("requirements"):
                # Format based on whether packages need installing
                if self.pending_packages:
                    req_text = f"📦 **Packages to install:**\n"
                    for pkg in self.pending_packages:
                        req_text += f"  • {pkg}\n"
                    req_text += "\nClick 'Add Extension' to install and activate."
                else:
                    req_text = "✅ **Ready to use!** No additional packages needed."

                self.chat_display.add_assistant_message(req_text)
                self.code_manager.add_to_history(
                    "assistant",
                    req_text,
                    status=req_text,
                    type="requirements",
                )
        else:
            error_msg = result.get("error", "Unknown error")
            self.status_label.setText(f"❌ {error_msg}")

        self.code_manager.save_session()
        self._scroll_chat_to_bottom()

    def save_extension(self):
        """Save extension - check for packages first"""
        code = self.code_preview.toPlainText()

        if not code:
            return

        # Check if packages need installing
        if self.pending_packages:
            dialog = InstallPackagesDialog(
                self.pending_packages, self.dependencies_dir, self
            )
            result = dialog.exec()

            if result == QDialog.DialogCode.Rejected:
                # User cancelled completely
                return

            # User clicked Skip or Install completed
            if dialog.install_accepted:
                # Installation succeeded - show message
                self.chat_display.add_assistant_message(
                    f"✅ Installed: {', '.join(self.pending_packages)}"
                )

            # Clear pending packages
            self.pending_packages = []

        # Continue with save
        self.code_manager.save_extension(
            code, self, on_success=self.on_save_success, on_error=self.on_save_error
        )

    def on_save_success(self, filename):
        """Handle successful save"""
        self.status_label.setText(f"✅ {filename} loaded!")

        success_msg = f"✅ Extension **{filename}** is now active!"
        self.chat_display.add_assistant_message(success_msg)
        self.code_manager.add_to_history(
            "assistant", success_msg, status=success_msg, type="success"
        )

        self.error_handler.reset_attempts()
        self._scroll_chat_to_bottom()

    def on_save_error(self, filename, error_info):
        """Handle save error"""
        if filename is None:
            self.error_handler.handle_syntax_error(
                error_info["message"],
                self.code_preview.toPlainText(),
                on_fix_request=self.request_ai_fix,
            )
        else:
            self.error_handler.handle_load_error(
                filename,
                error_info,
                self.code_preview.toPlainText(),
                on_fix_request=self.request_ai_fix,
                on_retry_save=self.save_extension,
            )

    def request_ai_fix(self, error_context, failed_code, on_complete=None):
        """Request AI fix with chat support"""
        self.set_send_button_mode("stop")

        status_msg = self.error_handler.get_status_message()
        if status_msg:
            self.progress_animation.start(status_msg.rstrip("."))
        else:
            self.progress_animation.start("AI is fixing the error")

        # Show fixing message in chat
        self.chat_display.add_assistant_message(
            "🔧 I found an error. Let me fix that for you..."
        )

        fix_prompt = f"Fix this error:\n\n{error_context[:500]}"

        context = build_ai_context(
            fix_prompt,
            self.code_manager.get_history()[-5:],
            failed_code,
        )

        context["is_fix_request"] = True
        context["error_context"] = error_context
        context["failed_code"] = failed_code

        provider = self.ai_manager.get_provider()
        if not provider:
            self.progress_animation.stop()
            self.set_send_button_mode("send")
            return

        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.stop()
            self.ai_thread.wait()

        self.ai_thread = AIStreamingThread(
            provider, fix_prompt, context, timeout=30, max_retries=3
        )
        self.ai_thread.progress.connect(self.on_progress_update)
        self.ai_thread.chunk.connect(self.on_code_chunk)
        self.ai_thread.chat_message.connect(self.on_chat_message)
        self.ai_thread.error.connect(self.on_ai_error)
        self.ai_thread.retry_attempt.connect(self.on_retry_attempt)
        self.ai_thread.finished.connect(
            lambda result: self.on_fix_complete(result, on_complete)
        )
        self.ai_thread.start()

    def on_fix_complete(self, result, on_complete=None):
        """Fix complete - retry save"""
        if result.get("success") and result.get("code") and on_complete:
            self.progress_animation.start("Retrying with fixed code")
            QTimer.singleShot(100, lambda: self.on_generation_complete(result))
            QTimer.singleShot(1000, on_complete)
        else:
            self.on_generation_complete(result)

    def clear_conversation(self):
        """Clear conversation"""
        reply = QMessageBox.question(
            self,
            "Clear?",
            "Clear conversation and code?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.code_manager.clear_session()
            self.code_preview.clear()
            self.save_btn.setEnabled(False)
            self.chat_display.clear_display()
            self.progress_animation.stop()
            self.status_label.setText("")
            self.pending_packages = []

    def update_api_status(self):
        """Update API status"""
        current_provider = self.browser_core.preferences.get_module_setting(
            "AIProviders", "selected_provider", "gemini"
        )
        provider_key = self.browser_core.preferences.get_module_setting(
            "AIProviders", f"{current_provider}_key"
        )

        if provider_key:
            self.api_status_label.setText(f"● {current_provider.title()}")
            self.api_status_label.setStyleSheet("color: #28a745; font-size: 11px;")
            self.send_btn.setEnabled(True)
        else:
            self.api_status_label.setText("⚠️ No API Key")
            self.api_status_label.setStyleSheet("color: #dc3545; font-size: 11px;")
            self.send_btn.setEnabled(False)

    # Wrapper methods for compatibility
    def add_user_message(self, text):
        if self.chat_display:
            self.chat_display.add_user_message(text)

    def add_assistant_message(self, text):
        if self.chat_display:
            self.chat_display.add_assistant_message(text)

    def rebuild_chat_display(self):
        if self.chat_display:
            self.chat_display.rebuild_display(self.code_manager.get_history())

    @property
    def conversation_history(self):
        return self.code_manager.get_history()

    @conversation_history.setter
    def conversation_history(self, value):
        self.code_manager.conversation_history = value

    @property
    def current_code(self):
        return self.code_manager.get_code()

    @current_code.setter
    def current_code(self, value):
        self.code_manager.update_code(value)
