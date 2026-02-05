"""
Error Handler
Manages error handling, auto-fix, and error recovery
Now with matching code editor dialog style and package install support
CONSOLIDATED: Uses shared error_dialogs module
"""

from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import QTimer, Qt
from pathlib import Path
import sys

# Import from consolidated error_dialogs module
from ..error_dialogs import (
    extract_missing_package,
    install_package,
    get_friendly_error_message,
    extract_system_lib_name,
    get_system_lib_commands,
)


class ClosableMessageBox(QMessageBox):
    def closeEvent(self, event):
        """Override close event to force accept"""
        self.accept()
        event.accept()


class ErrorHandler:
    """Handles errors and auto-fix functionality"""

    def __init__(self, parent_widget, max_attempts=3):
        """
        Args:
            parent_widget: Parent widget for dialogs
            max_attempts: Maximum auto-fix attempts
        """
        self.parent_widget = parent_widget
        self.max_attempts = max_attempts
        self.auto_fix_enabled = False
        self.auto_fix_attempts = 0
        self.last_error = None

        # Get dependencies directory
        browser_core = getattr(parent_widget, "browser_core", None)
        if browser_core and hasattr(browser_core, "dependencies_dir"):
            self.dependencies_dir = browser_core.dependencies_dir
        else:
            if getattr(sys, "frozen", False):
                self.dependencies_dir = Path(sys.executable).parent / "dependencies"
            else:
                self.dependencies_dir = (
                    Path(__file__).parent.parent.parent / "dependencies"
                )
            self.dependencies_dir.mkdir(exist_ok=True)

    def set_auto_fix_enabled(self, enabled):
        """Enable/disable auto-fix"""
        self.auto_fix_enabled = enabled
        if enabled:
            self.auto_fix_attempts = 0

    def handle_syntax_error(self, error_msg, code, on_fix_request=None):
        """
        Handle syntax error - show dialog or auto-request fix

        Args:
            error_msg: Error message
            code: Code that failed
            on_fix_request: Callback(error_context, failed_code) to request fix
        """
        if self.auto_fix_enabled and on_fix_request:
            on_fix_request(f"Syntax error: {error_msg}", code)
        else:
            reply = QMessageBox.critical(
                self.parent_widget,
                "Syntax Error",
                f"Code has syntax errors:\n\n{error_msg}\n\n"
                "Would you like the AI to fix this?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes and on_fix_request:
                on_fix_request(f"Syntax error: {error_msg}", code)

    def handle_load_error(
        self, module_name, error_info, code, on_fix_request=None, on_retry_save=None
    ):
        """
        Handle module load error with auto-fix support and package installation
        NOW MATCHES CODE EDITOR DIALOG STYLE

        Args:
            module_name: Name of module that failed
            error_info: Dict with type, message, traceback
            code: Code that failed to load
            on_fix_request: Callback(error_context, failed_code) to request fix
            on_retry_save: Callback() to retry saving after fix
        """
        self.last_error = {
            "module_name": module_name,
            "type": error_info["type"],
            "message": error_info["message"],
            "traceback": error_info.get("traceback", ""),
            "code": code,
        }

        # Auto-fix if enabled and attempts remaining
        if (
            self.auto_fix_enabled
            and self.auto_fix_attempts < self.max_attempts
            and on_fix_request
        ):
            self.auto_fix_attempts += 1

            full_error = error_info.get(
                "traceback", f"{error_info['type']}: {error_info['message']}"
            )

            # Delay slightly for UI update
            QTimer.singleShot(
                500,
                lambda: self._request_fix_and_retry(
                    full_error, code, on_fix_request, on_retry_save
                ),
            )
        else:
            # Show error dialog with package detection
            if self.auto_fix_attempts >= self.max_attempts:
                QMessageBox.critical(
                    self.parent_widget,
                    "Auto-Fix Failed",
                    f"Failed to load after {self.max_attempts} attempts:\n\n"
                    f"{error_info['message']}",
                )
            else:
                # Show dialog matching code editor style
                self._show_load_error_dialog(
                    module_name, error_info, code, on_fix_request, on_retry_save
                )

    def _show_load_error_dialog(
        self, module_name, error_info, code, on_fix_request, on_retry_save
    ):
        """
        Show load error dialog - MATCHES CODE EDITOR STYLE
        Detects import errors and shows Install Package button
        """
        print(f"\n🔍 ERROR HANDLER - LOAD ERROR DIALOG:")
        print(f"   Module: {module_name}")
        print(f"   Error Type: {error_info['type']}")
        print(f"   Error Message: {error_info['message'][:200]}")

        # Check if this is an import error (DEFINE THESE FIRST)
        error_type = error_info["type"]
        is_import_error = error_type in ["ModuleNotFoundError", "ImportError"]
        print(f"   Is Import Error: {is_import_error}")

        # NOW define full_error and check for missing package
        full_error = error_info.get("traceback", "") + "\n" + error_info["message"]
        missing_package = None
        if is_import_error:
            missing_package = extract_missing_package(full_error)
            print(f"   Missing Package: {missing_package}")

        # Create message box
        msg = ClosableMessageBox(self.parent_widget)
        msg.setWindowTitle("Extension Error")
        msg.setIcon(QMessageBox.Icon.Warning)

        # Check for system library errors
        is_system_lib_error = any(
            keyword in full_error.lower()
            for keyword in [
                "shared library",
                "libzbar",
                "libgl",
                "cannot open shared object",
            ]
        )

        # Build message based on error type
        if is_system_lib_error:
            print(f"   ✅ SHOWING SYSTEM LIBRARY INSTRUCTIONS")
            system_lib_name = extract_system_lib_name(full_error)
            install_cmds = get_system_lib_commands(system_lib_name)
            msg.setText(
                f"<b>{module_name} failed to load</b>\n\n"
                f"This extension requires system libraries.\n\n"
                f"Pip cannot install these. Please install manually:\n\n"
                f"{install_cmds}\n\n"
                f"Then restart KaiBrowser."
            )
        elif missing_package:
            print(f"   ✅ SHOWING INSTALL PACKAGE DIALOG")
            msg.setText(
                f"<b>{module_name} failed to load</b>\n\n"
                f"This extension requires the <b>{missing_package}</b> package.\n\n"
                f"Would you like to install it now?"
            )
        else:
            print(f"   ✅ SHOWING FIX WITH AI DIALOG")
            friendly_message = get_friendly_error_message(
                error_type, error_info["message"]
            )
            msg.setText(
                f"<b>{module_name} failed to load</b>\n\n"
                f"{friendly_message}\n\n"
                "You can fix this manually or let AI help."
            )

        # Technical details
        full_error = error_info.get(
            "traceback", f"{error_info['type']}: {error_info['message']}"
        )
        msg.setDetailedText(f"Technical Details:\n{full_error}")

        # Add appropriate button
        install_btn = None
        fix_with_ai_btn = None

        if is_system_lib_error:
            # No action button for system libs
            print(f"   ℹ️ SYSTEM LIBRARY ERROR - NO ACTION BUTTON")
        elif missing_package:
            install_btn = msg.addButton(
                "📦 Install Package", QMessageBox.ButtonRole.ActionRole
            )
        else:
            fix_with_ai_btn = msg.addButton(
                "Fix with AI", QMessageBox.ButtonRole.ActionRole
            )

        msg.addButton(QMessageBox.StandardButton.Ok)
        msg.exec()

        clicked = msg.clickedButton()
        print(f"   User clicked: {clicked.text() if clicked else 'None'}")

        # Handle button clicks
        if is_system_lib_error:
            # No action for system lib errors
            print(f"   ℹ️ System library error - user must install manually")
        elif missing_package and install_btn and clicked == install_btn:
            print(f"   🔄 Starting package installation")
            self._handle_package_install(missing_package, on_retry_save)
        elif not missing_package and fix_with_ai_btn and clicked == fix_with_ai_btn:
            print(f"   🔄 Sending to AI for fix")
            full_error = error_info.get(
                "traceback", f"{error_info['type']}: {error_info['message']}"
            )
            self._request_fix_and_retry(full_error, code, on_fix_request, on_retry_save)

    def _handle_package_install(self, package_name, on_retry_save):
        """Install package and retry loading extension"""
        print(f"\n📦 ERROR HANDLER - INSTALLING PACKAGE: {package_name}")

        # Show progress dialog
        progress = QProgressDialog(
            f"Installing {package_name}...\nThis may take a moment.",
            None,
            0,
            0,
            self.parent_widget,
        )
        progress.setWindowTitle("Installing Package")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        # Process events to show dialog
        from PyQt6.QtWidgets import QApplication

        QApplication.processEvents()

        # Install package (now using consolidated function)
        success, error = install_package(package_name, self.dependencies_dir)

        # Close progress
        progress.close()

        if success:
            print(f"   ✅ Installation successful, retrying load")
            QMessageBox.information(
                self.parent_widget,
                "Package Installed",
                f"Successfully installed {package_name}!\n\n"
                f"The extension will be reloaded now.",
            )

            # Retry loading
            if on_retry_save:
                QTimer.singleShot(100, on_retry_save)
        else:
            print(f"   ❌ Installation failed: {error}")
            reply = QMessageBox.warning(
                self.parent_widget,
                "Installation Failed",
                f"Could not install {package_name}:\n\n{error}\n\n"
                f"Would you like to try fixing this with AI?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                error_details = f"Failed to install package {package_name}: {error}"
                self._request_fix_and_retry(
                    error_details,
                    self.last_error.get("code", ""),
                    None,  # on_fix_request
                    on_retry_save,
                )

    def _request_fix_and_retry(
        self, error_context, failed_code, on_fix_request, on_retry_save
    ):
        """Request AI fix and retry save on completion"""
        if on_fix_request:
            # Request fix with callback to retry
            on_fix_request(error_context, failed_code, on_retry_save)

    def reset_attempts(self):
        """Reset auto-fix attempt counter"""
        self.auto_fix_attempts = 0

    def get_last_error(self):
        """Get last error info"""
        return self.last_error

    def get_attempts_remaining(self):
        """Get remaining auto-fix attempts"""
        return max(0, self.max_attempts - self.auto_fix_attempts)

    def get_status_message(self):
        """Get current status message"""
        if self.auto_fix_attempts > 0:
            return f"🔧 Auto-fixing... (Attempt {self.auto_fix_attempts}/{self.max_attempts})"
        return ""
