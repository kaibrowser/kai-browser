"""
Code Manager
Handles code validation, saving, loading, and module management
CONSOLIDATED: Uses shared build_ai_context from utils
"""

from PyQt6.QtWidgets import QMessageBox, QInputDialog
from PyQt6.QtCore import QTimer
import re
import json

# CONSOLIDATED: Import shared functions
from ..utils import validate_python_syntax, build_ai_context, ModuleLoader


class CodeManager:
    """Manages code validation, saving, and module loading"""

    def __init__(self, browser_core, modules_dir, loader):
        """
        Args:
            browser_core: Main browser core instance
            modules_dir: Path to modules directory
            loader: ModuleLoader instance
        """
        self.browser_core = browser_core
        self.modules_dir = modules_dir
        self.loader = loader
        self.current_code = ""
        self.conversation_history = []

    def load_session(self):
        """Load saved session from preferences"""
        saved_history = self.browser_core.preferences.get_module_setting(
            "ExtensionBuilder", "conversation_history", "[]"
        )
        saved_code = self.browser_core.preferences.get_module_setting(
            "ExtensionBuilder", "current_code", ""
        )

        try:
            self.conversation_history = json.loads(saved_history)
            self.current_code = saved_code
            return True
        except:
            self.conversation_history = []
            self.current_code = ""
            return False

    def save_session(self):
        """Save current session to preferences"""
        self.browser_core.preferences.set_module_setting(
            "ExtensionBuilder",
            "conversation_history",
            json.dumps(self.conversation_history[-10:]),
        )
        self.browser_core.preferences.set_module_setting(
            "ExtensionBuilder", "current_code", self.current_code
        )

    def validate_code(self, code):
        """
        Validate Python syntax
        Returns: (is_valid, error_message)
        """
        # CONSOLIDATED: Use shared validation function
        return validate_python_syntax(code)

    def suggest_filename(self, code):
        """Extract suggested filename from class name"""
        match = re.search(r"class (\w+)", code)
        if match:
            # CONSOLIDATED: Use ModuleLoader's method
            return ModuleLoader.class_to_filename(match.group(1))
        return ""

    def save_extension(self, code, parent_widget, on_success=None, on_error=None):
        """
        Save extension to file and load it

        Args:
            code: Python code to save
            parent_widget: Parent widget for dialogs
            on_success: Callback(filename) on successful load
            on_error: Callback(filename, error_info) on load failure
        """
        if not code:
            return

        # Validate syntax
        is_valid, error_msg = self.validate_code(code)
        if not is_valid:
            if on_error:
                on_error(
                    None, {"type": "SyntaxError", "message": error_msg, "traceback": ""}
                )
            return

        # Get filename
        suggested_name = self.suggest_filename(code)
        filename, ok = QInputDialog.getText(
            parent_widget,
            "Save Extension",
            "Filename (without .py):",
            text=suggested_name,
        )

        if not ok or not filename.strip():
            return

        filename = filename.strip()
        filepath = self.modules_dir / f"{filename}.py"

        # Check if exists
        if filepath.exists():
            reply = QMessageBox.question(
                parent_widget,
                "Overwrite?",
                f"'{filename}.py' exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

            # Unload existing module
            self._unload_existing_module(filename)

        # Save file
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)

            # Load module after short delay
            QTimer.singleShot(
                100,
                lambda: self._load_module(
                    filename, parent_widget, on_success, on_error
                ),
            )

        except Exception as e:
            QMessageBox.critical(parent_widget, "Error", f"Failed to save:\n{e}")

    def _unload_existing_module(self, filename):
        """Unload existing module if loaded"""
        for module in self.browser_core.modules[:]:
            if module.__class__.__module__ == f"modules.{filename}":
                self.loader.unload_module(module)
                break

    def _load_module(self, filename, parent_widget, on_success, on_error):
        """Load module and handle result"""
        success, error_info = self.loader.hot_load_module(filename)

        if success:
            self.loader.refresh_module_manager()
            if on_success:
                on_success(filename)
        else:
            if on_error:
                on_error(filename, error_info)

    def clear_session(self):
        """Clear conversation history and current code"""
        self.conversation_history = []
        self.current_code = ""
        self.save_session()

    def update_code(self, code):
        """Update current code"""
        self.current_code = code

    def get_code(self):
        """Get current code"""
        return self.current_code

    def add_to_history(self, role, message, **kwargs):
        """Add message to conversation history"""
        entry = {"role": role, "message": message}
        entry.update(kwargs)
        self.conversation_history.append(entry)

    def get_history(self):
        """Get conversation history"""
        return self.conversation_history

    def build_context(self, current_message):
        """
        Build AI context from history and current code
        CONSOLIDATED: Now uses shared build_ai_context function
        """
        return build_ai_context(
            current_message, self.conversation_history, self.current_code
        )
