"""
Extension Builder __init__.py - Fixed Runtime Error Loading
Now properly loads pending errors into AI tab
"""

from PyQt6.QtWidgets import QDialog, QTabWidget, QVBoxLayout, QLabel, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from pathlib import Path
from kai_base import KaiModule
import sys

try:
    from ai_providers import AIProviderManager

    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

from .ai_tab import AIBuilderTab
from .code_tab import CodeEditorTab
from .manage_tab import ManageTab
from .settings_tab import SettingsTab


class ExtensionBuilderModule(KaiModule):
    """Extension Builder with runtime error detection"""

    def __init__(self):
        super().__init__()
        self.module_type = self.MODULE_TYPE_UI
        self.modules_dir = None
        self.builder_dialog = None

    def setup(self):
        """Add Extension Builder button"""
        builder_action = QAction("✨ ", self.browser_core)
        builder_action.setToolTip("Extension Builder")
        builder_action.triggered.connect(self.show_builder)
        self.add_toolbar_action(builder_action)

        if getattr(sys, "frozen", False):
            self.modules_dir = Path(sys.executable).parent / "modules"
        else:
            self.modules_dir = Path(__file__).parent.parent / "modules"

        self.modules_dir.mkdir(exist_ok=True)

        status_msg = "👷 Extension Builder ready"
        if AI_AVAILABLE:
            status_msg += " - Chat with AI to build extensions!"
        self.browser_core.show_status(status_msg, 3000)

    def show_builder(self):
        """Show Extension Builder - check for first-time warning"""
        if not self.enabled:
            return

        # TESTING: Uncomment line below to always show warning
        # self.browser_core.preferences.set_module_setting("ExtensionBuilder", "safety_warning_shown", False)

        # ⚠️ SHOW EXTENSION SAFETY WARNING (first time only)
        if not self.browser_core.preferences.get_module_setting(
            "ExtensionBuilder", "safety_warning_shown", False
        ):
            if not self.show_extension_safety_warning():
                # User clicked Cancel - don't open builder
                return

        # Check for pending runtime error
        pending_error = None
        if hasattr(self.browser_core, "_pending_runtime_error"):
            pending_error = self.browser_core._pending_runtime_error

        # If dialog already exists and is visible
        if self.builder_dialog and self.builder_dialog.isVisible():
            # Load error into existing dialog
            if pending_error:
                self.builder_dialog.load_runtime_error_into_ai_tab(pending_error)
                # Clear pending error
                self.browser_core._pending_runtime_error = None
            # Just bring to front
            self.builder_dialog.raise_()
            self.builder_dialog.activateWindow()
        else:
            # Create new dialog
            self.builder_dialog = ModuleBuilderDialog(
                self.browser_core, self.modules_dir, pending_error=pending_error
            )

            # Clear pending error after loading
            if pending_error:
                self.browser_core._pending_runtime_error = None

    def show_extension_safety_warning(self):
        """Show detailed extension safety warning - returns True if user accepts"""
        from PyQt6.QtWidgets import QMessageBox, QCheckBox

        msg = QMessageBox(self.browser_core)
        msg.setWindowTitle("Extension Builder Safety")
        msg.setIcon(QMessageBox.Icon.Warning)

        msg.setText(
            """
        <h3>Extension Builder Safety Notice</h3>
        
        <p>You can create browser extensions using AI or write them yourself.</p>
        
        <p><b>IMPORTANT - Extensions have full browser permissions and can:</b></p>
        <ul>
        <li>Access all web pages you visit</li>
        <li>Modify web content and behavior</li>
        <li>Store data locally on your computer</li>
        <li>Make network requests</li>
        <li>Execute arbitrary code</li>
        </ul>
        
        <p><b>Safety Guidelines:</b></p>
        <ul>
        <li>Always review generated/downloaded code before installing</li>
        <li>Never include passwords or API keys in AI prompts</li>
        <li>Only install extensions you understand and trust</li>
        <li>AI can make mistakes - always verify the code</li>
        <li>User-created extensions are NOT reviewed by KaiBrowser</li>
        </ul>
        
        <p><b>You create and install extensions at your own risk.</b></p>
        
        <p>KaiBrowser is not responsible for extension behavior, bugs, or damages.</p>
        """
        )

        # Add checkbox for "don't show again"
        checkbox = QCheckBox("Don't show this again")
        msg.setCheckBox(checkbox)

        msg.setStandardButtons(
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )

        result = msg.exec()

        # Only save "don't show again" if user clicked OK AND checked the box
        if result == QMessageBox.StandardButton.Ok and checkbox.isChecked():
            self.browser_core.preferences.set_module_setting(
                "ExtensionBuilder", "safety_warning_shown", True
            )

        return result == QMessageBox.StandardButton.Ok


class ModuleBuilderDialog(QDialog):
    """Main dialog with runtime error support"""

    def __init__(self, parent, modules_dir, pending_error=None):
        super().__init__(parent)
        self.modules_dir = modules_dir
        self.browser_core = parent
        self.ai_manager = None
        self.pending_error = pending_error

        if AI_AVAILABLE:
            self.ai_manager = AIProviderManager(self.browser_core.preferences)

        self.setWindowTitle("Extension Builder")
        self.setModal(False)
        self.setWindowFlags(Qt.WindowType.Window)
        self.setMinimumSize(800, 600)
        self.resize(900, 650)

        self.setup_ui()

        # Load pending error AFTER UI is set up
        if pending_error:
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(
                100, lambda: self.load_runtime_error_into_ai_tab(pending_error)
            )

        self.show()

    def setup_ui(self):
        """Set up UI"""
        layout = QVBoxLayout()

        # header = QLabel("Extension Builder")
        # header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        # layout.addWidget(header)

        self.tabs = QTabWidget()

        # AI Chat Tab
        if AI_AVAILABLE and self.ai_manager:
            self.ai_tab = AIBuilderTab(
                self.browser_core, self.modules_dir, self.ai_manager
            )
            self.tabs.addTab(self.ai_tab, "✨ AI")

        # Code Editor Tab
        self.code_tab = CodeEditorTab(self.browser_core, self.modules_dir)
        self.tabs.addTab(self.code_tab, "Code Editor")

        # Manage Tab
        self.manage_tab = ManageTab(self.browser_core, self.modules_dir)
        self.tabs.addTab(self.manage_tab, "Manage")

        # Settings Tab
        if AI_AVAILABLE and self.ai_manager:
            self.settings_tab = SettingsTab(self.browser_core, self.ai_manager)
            self.settings_tab.settings_changed.connect(self.ai_tab.update_api_status)
            self.tabs.addTab(self.settings_tab, "API Settings")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def load_runtime_error_into_ai_tab(self, error_context):
        """Load runtime error into AI tab with full context"""
        if not hasattr(self, "ai_tab"):
            QMessageBox.warning(
                self,
                "AI Not Available",
                "AI chat is not available. Cannot auto-fix runtime errors.",
            )
            return

        # Extract error info
        module_name = error_context.get("module_name", "Unknown")
        module_file = error_context.get("module_file", "")
        error_info = error_context.get("error_info", {})
        source_code = error_context.get("source_code", "")

        print(f"\n{'='*60}")
        print(f"📤 Loading runtime error into AI tab")
        print(f"{'='*60}")
        print(f"Module: {module_name}")
        print(f"File: {module_file}")
        print(
            f"Error: {error_info.get('error_type', 'Unknown')}: {error_info.get('error_message', 'Unknown')}"
        )
        print(f"Has source code: {bool(source_code)}")
        print(f"{'='*60}\n")

        # Switch to AI tab
        self.tabs.setCurrentWidget(self.ai_tab)

        # Show banner about runtime error
        banner_text = f"🔧 Runtime Error Detected in {module_name}"
        self.ai_tab.add_assistant_message(banner_text)

        # Load source code into preview if available
        if source_code:
            self.ai_tab.code_preview.setPlainText(source_code)
            self.ai_tab.current_code = source_code
            self.ai_tab.save_btn.setEnabled(True)
        else:
            # Try to load from file
            if module_file:
                try:
                    module_path = self.modules_dir / f"{module_file}.py"
                    if module_path.exists():
                        with open(module_path, "r") as f:
                            source_code = f.read()
                        self.ai_tab.code_preview.setPlainText(source_code)
                        self.ai_tab.current_code = source_code
                        self.ai_tab.save_btn.setEnabled(True)
                        print(f"✓ Loaded source from file: {module_path}")
                except Exception as e:
                    print(f"Failed to load source file: {e}")

        # Build error message for AI
        error_type = error_info.get("error_type", "Unknown")
        error_message = error_info.get("error_message", "Unknown error")
        error_traceback = error_info.get("traceback", "")

        # Extract the key part of the traceback (last few lines)
        traceback_lines = error_traceback.split("\n")
        key_traceback = (
            "\n".join(traceback_lines[-10:])
            if len(traceback_lines) > 10
            else error_traceback
        )

        # Create fix request message
        fix_request = f"""Runtime error detected:

Error Type: {error_type}
Message: {error_message}

Traceback:
{key_traceback}

Please fix this error in the code."""

        # Pre-fill the message input
        self.ai_tab.message_input.setPlainText(fix_request)

        # Add to conversation history
        self.ai_tab.conversation_history.append(
            {
                "role": "assistant",
                "status": f"⚠️ Runtime error in {module_name}: {error_message[:100]}",
            }
        )

        # Show helpful message
        QMessageBox.information(
            self,
            "Runtime Error Loaded",
            f"Runtime error from {module_name} has been loaded.\n\n"
            f"Error: {error_message}\n\n"
            f"The error details are in the AI chat.\n"
            f"Click 'Generate' to ask AI to fix it.",
        )

        print(f"✓ Runtime error loaded into AI tab successfully")
