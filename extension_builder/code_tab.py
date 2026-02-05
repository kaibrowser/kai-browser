"""
Extension Builder - Code Editor Tab (Minimal UI)
Manual code editing with templates + save popup for naming
With friendly error dialogs and AI fix option
NEW: Auto-install missing packages when detected
CONSOLIDATED: Uses shared error_dialogs module
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QComboBox,
    QMessageBox,
    QInputDialog,
    QProgressDialog,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QTimer, Qt
from .utils import ModuleLoader, CodeTemplates, validate_python_syntax
from pathlib import Path
import sys
import re

# Import from consolidated error_dialogs module
from .error_dialogs import (
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


def friendly_name(class_name):
    """Convert class names to user-friendly names"""
    name = class_name
    for suffix in ["Module", "Plugin", "Extension"]:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break

    result = []
    for char in name:
        if char.isupper() and result:
            result.append(" ")
        result.append(char)

    return "".join(result).strip() or class_name


class CodeEditorTab(QWidget):
    """Minimal code editor with template selector"""

    def __init__(self, browser_core, modules_dir):
        super().__init__()
        self.browser_core = browser_core
        self.modules_dir = modules_dir
        self.loader = ModuleLoader(browser_core, modules_dir)
        self.current_filename = None

        # Get dependencies directory
        if hasattr(browser_core, "dependencies_dir"):
            self.dependencies_dir = browser_core.dependencies_dir
        else:
            if getattr(sys, "frozen", False):
                self.dependencies_dir = Path(sys.executable).parent / "dependencies"
            else:
                self.dependencies_dir = (
                    Path(__file__).parent.parent.parent / "dependencies"
                )
            self.dependencies_dir.mkdir(exist_ok=True)

        # Load saved session
        self.saved_editor_code = self.browser_core.preferences.get_module_setting(
            "ExtensionBuilder", "editor_code", ""
        )

        self.setup_ui()

    def setup_ui(self):
        """Set up minimal code editor interface"""
        layout = QVBoxLayout()

        # Template selector
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Template:"))
        self.template_combo = QComboBox()
        self.template_combo.addItem("🎯 Simple UI Extension", "simple")
        self.template_combo.addItem("⚙️ Background Extension", "background")
        self.template_combo.addItem("💉 JavaScript Injector", "injector")
        self.template_combo.addItem("📝 Blank", "blank")
        # Only use activated to avoid duplicate popups
        self.template_combo.activated.connect(self.load_template)
        template_layout.addWidget(self.template_combo, 1)
        layout.addLayout(template_layout)

        # Code editor
        self.code_editor = QTextEdit()
        self.code_editor.setFont(QFont("Monospace", 10))
        self.code_editor.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 2px solid #333;
                padding: 10px;
            }
        """
        )
        self.code_editor.textChanged.connect(self.save_session)
        layout.addWidget(self.code_editor, 1)

        # Validation status
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("padding: 5px; font-size: 11px;")
        layout.addWidget(self.validation_label)

        # Buttons
        button_layout = QHBoxLayout()

        validate_btn = QPushButton("Validate Syntax")
        validate_btn.clicked.connect(self.validate_code)
        validate_btn.setStyleSheet(
            "background-color:#f1f5f9; color:#0f172a; border:1px solid #e2e8f0; "
            "border-radius:6px; padding:10px; font-size:12px; font-weight:500;"
        )
        button_layout.addWidget(validate_btn)

        save_load_btn = QPushButton("Add Extension")
        save_load_btn.clicked.connect(self.save_and_load_module)
        save_load_btn.setStyleSheet(
            "background-color:#f1f5f9; color:#0f172a; border:1px solid #e2e8f0; "
            "border-radius:6px; padding:10px; font-size:12px; font-weight:500;"
        )
        button_layout.addWidget(save_load_btn)

        layout.addLayout(button_layout)

        # Help text
        help_text = QLabel(
            "💡 Hot Reload: Edit and reload extensions instantly. "
            "When you save, you'll be prompted for a filename."
        )
        help_text.setStyleSheet(
            "color: #28a745; font-style: italic; padding: 5px; font-size: 10px;"
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        self.setLayout(layout)

        # Restore saved code
        if self.saved_editor_code:
            self.code_editor.setPlainText(self.saved_editor_code)
        else:
            # Load initial template without confirmation
            self.load_template_internal()

    def save_session(self):
        """Save current editor code"""
        self.browser_core.preferences.set_module_setting(
            "ExtensionBuilder", "editor_code", self.code_editor.toPlainText()
        )

    def load_template(self):
        """Load selected template (with confirmation if needed)"""
        template_type = self.template_combo.currentData()
        current_code = self.code_editor.toPlainText().strip()

        # Check if we have ANY code at all (even 1 character)
        if current_code:
            reply = QMessageBox.question(
                self,
                "Load Template?",
                "Loading a template will replace your current code. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.No:
                return

        # Load the template
        code = CodeTemplates.get_template(
            template_type, "MyExtension", "Custom extension"
        )
        self.code_editor.setPlainText(code)
        self.validation_label.setText("")

    def load_template_internal(self):
        """Load template without confirmation (for initial load)"""
        template_type = self.template_combo.currentData()
        code = CodeTemplates.get_template(
            template_type, "MyExtension", "Custom extension"
        )
        self.code_editor.setPlainText(code)
        self.validation_label.setText("")
        self._templates_initialized = True

    def validate_code(self):
        """Validate Python syntax"""
        code = self.code_editor.toPlainText()

        if not code.strip():
            self.validation_label.setText("⚠️ No code to validate")
            self.validation_label.setStyleSheet("color: #ffc107; padding: 5px;")
            return False

        is_valid, error_msg = validate_python_syntax(code)

        if is_valid:
            self.validation_label.setText("✅ Syntax is valid!")
            self.validation_label.setStyleSheet(
                "color: #28a745; padding: 5px; font-weight: bold;"
            )
            return True
        else:
            self.validation_label.setText(f"❌ Syntax Error: {error_msg}")
            self.validation_label.setStyleSheet(
                "color: #dc3545; padding: 5px; font-weight: bold;"
            )

            self._show_error_dialog(
                "Syntax Error",
                "The extension has a syntax error in the code.",
                error_msg,
                self.code_editor.toPlainText(),
                "SyntaxError",
            )
            return False

    def save_and_load_module(self):
        """Save and hot-load module with filename popup"""
        code = self.code_editor.toPlainText()

        if not code.strip():
            QMessageBox.warning(self, "Error", "Code cannot be empty!")
            return

        if not self.validate_code():
            return

        # Extract suggested name from class name
        suggested_name = ""
        match = re.search(r"class (\w+)", code)
        if match:
            class_name = match.group(1)
            suggested_name = ModuleLoader.class_to_filename(class_name)

        # Ask user for filename
        filename, ok = QInputDialog.getText(
            self, "Save Extension", "Enter filename (without .py):", text=suggested_name
        )

        if not ok or not filename.strip():
            return

        filename = filename.strip()

        # Validate filename
        if not filename.replace("_", "").replace("-", "").isalnum():
            QMessageBox.warning(
                self,
                "Error",
                "Filename must be alphanumeric with underscores/hyphens only!",
            )
            return

        self.current_filename = filename
        filepath = self.modules_dir / f"{filename}.py"

        # Check if exists
        if filepath.exists():
            reply = QMessageBox.question(
                self,
                "File Exists",
                f"'{filename}.py' already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.No:
                return

        # Unload existing instance if loaded
        for module in self.browser_core.modules[:]:
            if module.__class__.__module__ == f"modules.{filename}":
                self.loader.unload_module(module)
                break

        # Save file
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)

            self.browser_core.show_status(f"💾 {filename}.py saved", 2000)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")
            return

        # Load with delay
        QTimer.singleShot(100, lambda: self._finish_loading(filename))

    def _finish_loading(self, filename):
        """Complete the loading process"""
        success, error_info = self.loader.hot_load_module(filename)

        if success:
            self.loader.refresh_module_manager()
            self.browser_core.show_status(f"✅ {filename} loaded!", 3000)

            self.validation_label.setText(f"✅ Extension loaded successfully!")
            self.validation_label.setStyleSheet(
                "color: #28a745; font-weight: bold; padding: 5px;"
            )

            QMessageBox.information(
                self,
                "Success",
                f"✅ Extension loaded!\n\n"
                f"File: {filename}.py\n\n"
                "Check the toolbar for your extension.",
            )
        else:
            # Show friendly error dialog with AI fix option or Install Package
            friendly = friendly_name(filename)
            user_msg = get_friendly_error_message(
                error_info["type"], error_info["message"]
            )

            self.validation_label.setText(
                f"❌ Load Error: {error_info['message'][:100]}"
            )
            self.validation_label.setStyleSheet("color: #dc3545; padding: 5px;")

            self._show_error_dialog(
                f"{friendly} failed to load",
                user_msg,
                f"{error_info['type']}: {error_info['message']}\n\n{error_info.get('traceback', '')}",
                self.code_editor.toPlainText(),
                error_info["type"],
            )

    def _show_error_dialog(
        self, title, friendly_message, technical_details, code, error_type=""
    ):
        """Show friendly error dialog with Install Package or Fix with AI option"""
        print(f"\n🔍 CODE EDITOR - ERROR DIALOG:")
        print(f"   Title: {title}")
        print(f"   Error Type: {error_type}")
        print(f"   Technical Details: {technical_details[:200]}")

        # Check if this is an import error
        is_import_error = error_type in ["ModuleNotFoundError", "ImportError"]
        print(f"   Is Import Error: {is_import_error}")

        missing_package = None
        if is_import_error:
            missing_package = extract_missing_package(technical_details)
            print(f"   Missing Package: {missing_package}")

        msg = ClosableMessageBox(self)
        msg.setWindowTitle("Extension Error")
        msg.setIcon(QMessageBox.Icon.Warning)

        # Check for system library errors
        is_system_lib_error = any(
            keyword in technical_details.lower()
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
            system_lib_name = extract_system_lib_name(technical_details)
            install_cmds = get_system_lib_commands(system_lib_name)
            msg.setText(
                f"<b>{title}</b>\n\n"
                f"This extension requires system libraries.\n\n"
                f"Pip cannot install these. Please install manually:\n\n"
                f"{install_cmds}\n\n"
                f"Then restart KaiBrowser."
            )
        elif missing_package:
            print(f"   ✅ SHOWING INSTALL PACKAGE DIALOG")
            msg.setText(
                f"<b>{title}</b>\n\n"
                f"This extension requires the <b>{missing_package}</b> package.\n\n"
                f"Would you like to install it now?"
            )
        else:
            print(f"   ✅ SHOWING FIX WITH AI DIALOG")
            msg.setText(
                f"<b>{title}</b>\n\n"
                f"{friendly_message}\n\n"
                "You can fix this manually or let AI help."
            )

        msg.setDetailedText(f"Technical Details:\n{technical_details}")

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
            self._handle_package_install(missing_package)
        elif not missing_package and fix_with_ai_btn and clicked == fix_with_ai_btn:
            print(f"   🔄 Sending to AI for fix")
            self._send_to_ai_for_fix(technical_details, code)

    def _handle_package_install(self, package_name):
        """Install package and retry loading extension"""
        print(f"\n📦 CODE EDITOR - INSTALLING PACKAGE: {package_name}")

        # Show progress dialog
        progress = QProgressDialog(
            f"Installing {package_name}...\nThis may take a moment.", None, 0, 0, self
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
            print(f"   ✅ Installation successful, reloading extension")
            QMessageBox.information(
                self,
                "Package Installed",
                f"Successfully installed {package_name}!\n\n"
                f"The extension will be reloaded now.",
            )

            # Retry loading the extension
            if self.current_filename:
                QTimer.singleShot(
                    100, lambda: self._finish_loading(self.current_filename)
                )
        else:
            print(f"   ❌ Installation failed: {error}")
            reply = QMessageBox.warning(
                self,
                "Installation Failed",
                f"Could not install {package_name}:\n\n{error}\n\n"
                f"Would you like to try fixing this with AI?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                error_details = f"Failed to install package {package_name}: {error}"
                self._send_to_ai_for_fix(error_details, self.code_editor.toPlainText())

    def _send_to_ai_for_fix(self, error_details, code):
        """Send error to AI tab for fixing"""
        # Store error context for AI tab
        error_context = {
            "module_name": self.current_filename or "Unknown",
            "module_file": self.current_filename or "",
            "error_info": {
                "error_type": "LoadError",
                "error_message": error_details[:500],
                "traceback": error_details,
            },
            "source_code": code,
        }

        self.browser_core._pending_runtime_error = error_context

        # Find and open Extension Builder AI tab
        parent_dialog = self.window()
        if hasattr(parent_dialog, "ai_tab"):
            # Switch to AI tab
            if hasattr(parent_dialog, "tabs"):
                parent_dialog.tabs.setCurrentIndex(0)

            # Load error into AI tab
            QTimer.singleShot(
                100, lambda: parent_dialog.load_runtime_error_into_ai_tab(error_context)
            )

        self.browser_core.show_status("📤 Sent to AI for fixing...", 2000)
