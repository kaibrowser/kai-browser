"""
Extension Builder - Manage Extensions Tab
View, edit, reload, delete, and send to AI for improvements

This file lives in: extension_builder/manage_tab.py
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QInputDialog,
)
from PyQt6.QtCore import Qt, QTimer
from .utils import ModuleLoader
from .error_dialogs import show_error_dialog_with_actions


class ManageTab(QWidget):
    """Manage existing extensions tab"""

    def __init__(self, browser_core, modules_dir):
        super().__init__()
        self.browser_core = browser_core
        self.modules_dir = modules_dir
        self.loader = ModuleLoader(browser_core, modules_dir)

        self.setup_ui()
        self.refresh_module_list()

    def setup_ui(self):
        """Set up the manage extensions interface"""
        layout = QVBoxLayout()

        # Header
        info = QLabel("📋 Manage Your Extensions")
        info.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(info)

        # Status indicator
        self.status_label = QLabel("🟢 Loaded  ⚪ Not Loaded")
        self.status_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(self.status_label)

        # Extension list
        self.module_list = QListWidget()
        self.module_list.setStyleSheet(
            """
            QListWidget {
                font-size: 13px;
                padding: 5px;
                border: 1px solid #ddd;
                                       outline: 0;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #000;
                                       outline: none;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
                                       outline: none;
            }
                                       QListWidget::item:selected:hover {
        background-color: #e3f2fd; /* no hover effect when selected */
    }
        """
        )
        self.module_list.itemDoubleClicked.connect(self.edit_selected_module)
        layout.addWidget(self.module_list)

        # Help text
        help_text = QLabel(
            "Tips"
            "\n"
            "• Double-click an extension to edit in the Code Editor tab.\n"
            "• Use the buttons below to delete, reload, improve or fix the selected extension.\n"
            "• When improving / fixng extensions with AI, save with a new name to keep both versions."
        )
        help_text.setStyleSheet(
            "color: #666; font-style: italic; padding: 5px; font-size: 11px;"
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # Action buttons - two rows
        button_layout_1 = QHBoxLayout()
        button_layout_2 = QHBoxLayout()

        # Row 1: Common actions
        reload_btn = QPushButton("Reload")
        reload_btn.clicked.connect(self.reload_selected_module)
        reload_btn.setStyleSheet(
            "background-color:#f1f5f9; color:#0f172a; border:1px solid #e2e8f0; "
            "border-radius:6px; padding:10px; font-weight:500;"
        )
        button_layout_1.addWidget(reload_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_selected_module)
        delete_btn.setStyleSheet(
            "background-color:#f1f5f9; color:#0f172a; border:1px solid #e2e8f0; "
            "border-radius:6px; padding:10px; font-weight:500;"
        )
        button_layout_1.addWidget(delete_btn)

        # Row 2: AI features
        ai_improve_btn = QPushButton("✨ AI Improve")
        ai_improve_btn.clicked.connect(self.send_to_ai_for_improvement)
        ai_improve_btn.setStyleSheet(
            "color:white; border:none; border-radius:6px; padding:10px; font-weight:500;"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #38bdf8, stop:1 #8b5cf6);"
        )
        button_layout_2.addWidget(ai_improve_btn)

        ai_fix_btn = QPushButton("✨ AI Fix")
        ai_fix_btn.clicked.connect(self.send_to_ai_for_fix)
        ai_fix_btn.setStyleSheet(
            "color:white; border:none; border-radius:6px; padding:10px; font-weight:500;"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #60a5fa, stop:1 #7c3aed);"
        )

        button_layout_2.addWidget(ai_fix_btn)

        layout.addLayout(button_layout_1)
        layout.addLayout(button_layout_2)

        self.setLayout(layout)

    def refresh_module_list(self):
        """Refresh the list of extensions"""
        self.module_list.clear()

        # Get all .py files in modules directory
        py_files = sorted(self.modules_dir.glob("*.py"))

        loaded_count = 0
        total_count = 0

        for py_file in py_files:
            # Skip private/system files
            if py_file.stem.startswith("_"):
                continue

            total_count += 1
            is_loaded = self.is_module_loaded(py_file.stem)

            if is_loaded:
                loaded_count += 1

            # Simple: just dot + name
            status = "🟢" if is_loaded else "⚪"
            item_text = f"{status} {py_file.stem}"

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, py_file)
            self.module_list.addItem(item)

        # Update status label
        self.status_label.setText(
            f"🟢 {loaded_count} Loaded  ⚪ {total_count - loaded_count} Not Loaded  (Total: {total_count})"
        )

        if total_count == 0:
            empty_item = QListWidgetItem(
                "📝 No extensions found. Create one in the AI Chat or Code Editor tab!"
            )
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.module_list.addItem(empty_item)

    def is_module_loaded(self, module_name):
        """Check if a module is currently loaded"""
        for module in self.browser_core.modules:
            if module.__class__.__module__ == f"modules.{module_name}":
                return True
        return False

    def get_loaded_module(self, module_name):
        """Get the loaded module instance"""
        for module in self.browser_core.modules:
            if module.__class__.__module__ == f"modules.{module_name}":
                return module
        return None

    def edit_selected_module(self, item):
        """Load extension code into the code editor"""
        filepath = item.data(Qt.ItemDataRole.UserRole)

        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()

            # Get the parent dialog to access tabs
            parent_dialog = self.window()

            # Switch to code editor tab
            if hasattr(parent_dialog, "code_tab"):
                # Load into code editor
                code_tab = parent_dialog.code_tab

                code_tab.code_editor.setPlainText(code)
                code_tab.validation_label.setText(f"📝 Editing: {filepath.stem}.py")
                code_tab.validation_label.setStyleSheet(
                    "color: #0066cc; padding: 5px; font-weight: bold;"
                )

                # Switch to code tab
                parent = parent_dialog.findChildren(QWidget)
                for widget in parent:
                    if widget.__class__.__name__ == "QTabWidget":
                        widget.setCurrentIndex(1)  # Code editor is tab 1
                        break

                self.browser_core.show_status(f"📝 Editing {filepath.stem}.py", 2000)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}")

    def send_to_ai_for_improvement(self):
        """Send selected extension to AI for improvements/upgrades"""
        current_item = self.module_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "No Selection", "Please select an extension to improve!"
            )
            return

        filepath = current_item.data(Qt.ItemDataRole.UserRole)
        if not filepath:
            return

        module_name = filepath.stem

        # Ask user what improvements they want
        improvement_request, ok = QInputDialog.getText(
            self,
            "AI Improvement Request",
            f"What improvements do you want for '{module_name}'?\n\n"
            "Examples:\n"
            "- Add error handling\n"
            "- Add more features\n"
            "- Improve UI design\n"
            "- Make it faster\n"
            "- Add settings menu\n\n"
            "Your request:",
            text="Add more features and improve the UI",
        )

        if not ok or not improvement_request.strip():
            return

        # Load current code
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                current_code = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}")
            return

        # Check if Extension Builder with AI is available
        parent_dialog = self.window()
        if not hasattr(parent_dialog, "ai_tab"):
            QMessageBox.warning(
                self,
                "AI Not Available",
                "AI Chat tab is not available. Cannot send to AI for improvement.",
            )
            return

        # Prepare AI context
        ai_context = {
            "module_name": module_name,
            "module_file": module_name,
            "improvement_request": improvement_request,
            "current_code": current_code,
            "source_code": current_code,
        }

        # Store in browser for AI tab to pick up
        self.browser_core._pending_ai_improvement = ai_context

        # Switch to AI tab
        for widget in parent_dialog.findChildren(QWidget):
            if widget.__class__.__name__ == "QTabWidget":
                widget.setCurrentIndex(0)  # AI tab is tab 0
                break

        # Load into AI tab
        QTimer.singleShot(100, lambda: self._load_improvement_into_ai(ai_context))

    def _load_improvement_into_ai(self, context):
        """Load improvement request into AI tab"""
        parent_dialog = self.window()
        if not hasattr(parent_dialog, "ai_tab"):
            return

        ai_tab = parent_dialog.ai_tab

        # Load current code into preview
        ai_tab.code_preview.setPlainText(context["current_code"])
        ai_tab.current_code = context["current_code"]
        ai_tab.save_btn.setEnabled(True)

        # Show banner
        ai_tab.add_assistant_message(
            f"✨ Improving extension: {context['module_name']}"
        )

        # Pre-fill improvement request
        improvement_prompt = f"Improve this extension: {context['improvement_request']}\n\nKeep existing functionality but make it better."
        ai_tab.message_input.setPlainText(improvement_prompt)

        # Add to conversation history
        ai_tab.conversation_history.append(
            {
                "role": "assistant",
                "status": f'✨ Ready to improve {context["module_name"]}',
            }
        )

        self.browser_core.show_status(
            f"✨ Ready to improve {context['module_name']}", 3000
        )

        QMessageBox.information(
            self,
            "Ready for AI Improvement",
            f"Extension '{context['module_name']}' loaded into AI Chat.\n\n"
            f"Request: {context['improvement_request']}\n\n"
            "Click 'Generate' to let AI improve it!",
        )

    def send_to_ai_for_fix(self):
        """Send selected extension to AI to fix potential issues"""
        current_item = self.module_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "No Selection", "Please select an extension to fix!"
            )
            return

        filepath = current_item.data(Qt.ItemDataRole.UserRole)
        if not filepath:
            return

        module_name = filepath.stem

        # Load current code
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                current_code = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}")
            return

        # Check if Extension Builder with AI is available
        parent_dialog = self.window()
        if not hasattr(parent_dialog, "ai_tab"):
            QMessageBox.warning(
                self,
                "AI Not Available",
                "AI Chat tab is not available. Cannot send to AI for fixing.",
            )
            return

        # Prepare AI context
        ai_context = {
            "module_name": module_name,
            "module_file": module_name,
            "fix_request": "review and fix any potential issues",
            "current_code": current_code,
            "source_code": current_code,
        }

        # Store in browser for AI tab to pick up
        self.browser_core._pending_ai_fix = ai_context

        # Switch to AI tab
        for widget in parent_dialog.findChildren(QWidget):
            if widget.__class__.__name__ == "QTabWidget":
                widget.setCurrentIndex(0)  # AI tab is tab 0
                break

        # Load into AI tab
        QTimer.singleShot(100, lambda: self._load_fix_into_ai(ai_context))

    def _load_fix_into_ai(self, context):
        """Load fix request into AI tab"""
        parent_dialog = self.window()
        if not hasattr(parent_dialog, "ai_tab"):
            return

        ai_tab = parent_dialog.ai_tab

        # Load current code into preview
        ai_tab.code_preview.setPlainText(context["current_code"])
        ai_tab.current_code = context["current_code"]
        ai_tab.save_btn.setEnabled(True)

        # Show banner
        ai_tab.add_assistant_message(
            f"🔧 Reviewing extension: {context['module_name']}"
        )

        # Pre-fill fix request
        fix_prompt = (
            f"Review this extension and fix any issues:\n"
            f"- Add proper error handling\n"
            f"- Fix any bugs or potential crashes\n"
            f"- Improve code quality\n"
            f"- Add missing edge case handling\n\n"
            f"Keep all existing functionality working."
        )
        ai_tab.message_input.setPlainText(fix_prompt)

        # Add to conversation history
        ai_tab.conversation_history.append(
            {"role": "assistant", "status": f'🔧 Ready to fix {context["module_name"]}'}
        )

        self.browser_core.show_status(f"🔧 Ready to fix {context['module_name']}", 3000)

        QMessageBox.information(
            self,
            "Ready for AI Fix",
            f"Extension '{context['module_name']}' loaded into AI Chat.\n\n"
            "AI will review and fix any potential issues.\n\n"
            "Click 'Generate' to let AI fix it!",
        )

    def reload_selected_module(self):
        """Hot-reload the selected module"""
        current_item = self.module_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "No Selection", "Please select an extension to reload!"
            )
            return

        filepath = current_item.data(Qt.ItemDataRole.UserRole)
        if not filepath:
            return

        module_name = filepath.stem

        # Check if module is loaded
        if not self.is_module_loaded(module_name):
            reply = QMessageBox.question(
                self,
                "Module Not Loaded",
                f"{module_name} is not currently loaded.\n\n"
                "Would you like to load it instead?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.load_selected_module()
            return

        # Unload existing instance
        module_instance = self.get_loaded_module(module_name)
        if module_instance:
            self.loader.unload_module(module_instance)

        # Wait briefly then reload
        QTimer.singleShot(100, lambda: self._finish_reload(module_name))

    def _finish_reload(self, module_name):
        """Complete the reload process with consolidated error handling"""

        success, error_info = self.loader.hot_load_module(module_name)

        if success:
            self.loader.refresh_module_manager()
            self.browser_core.show_status(f"🔄 {module_name} reloaded!", 2000)
            self.refresh_module_list()

            QMessageBox.information(
                self,
                "Reloaded",
                f"✅ Extension reloaded successfully!\n\n"
                f"Module: {module_name}\n\n"
                "The updated code is now active.",
            )
        else:
            # Use consolidated error dialog
            action = show_error_dialog_with_actions(
                parent_widget=self,
                extension_name=module_name,
                error_info=error_info,
                dependencies_dir=self.loader.browser_core.dependencies_dir,
                on_install_success=lambda: self._finish_reload(
                    module_name
                ),  # Retry on success
                on_fix_with_ai=lambda err, code: self._send_to_ai_for_fix_from_error(
                    module_name, err
                ),
                dialog_title="Reload Failed",
            )

            self.refresh_module_list()

    def _send_to_ai_for_fix_from_error(self, module_name, error_details):
        """Send error to AI for fixing after reload failure"""
        try:
            # Load current code
            filepath = self.modules_dir / f"{module_name}.py"
            with open(filepath, "r", encoding="utf-8") as f:
                current_code = f.read()
        except:
            current_code = ""

        # Prepare AI context
        ai_context = {
            "module_name": module_name,
            "module_file": module_name,
            "fix_request": "fix reload error",
            "current_code": current_code,
            "source_code": current_code,
            "error_details": error_details,
        }

        self.browser_core._pending_ai_fix = ai_context

        # Switch to AI tab and load
        parent_dialog = self.window()
        for widget in parent_dialog.findChildren(QWidget):
            if widget.__class__.__name__ == "QTabWidget":
                widget.setCurrentIndex(0)
                break

        QTimer.singleShot(100, lambda: self._load_fix_into_ai(ai_context))

    def load_selected_module(self):
        """Load a module into memory"""
        current_item = self.module_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "No Selection", "Please select an extension to load!"
            )
            return

        filepath = current_item.data(Qt.ItemDataRole.UserRole)
        if not filepath:
            return

        module_name = filepath.stem

        # Check if already loaded
        if self.is_module_loaded(module_name):
            QMessageBox.information(
                self,
                "Already Loaded",
                f"{module_name} is already loaded.\n\n"
                "Use 'Reload' to reload it with any changes.",
            )
            return

        # Load module
        success, error_info = self.loader.hot_load_module(module_name)

        if success:
            self.loader.refresh_module_manager()
            self.browser_core.show_status(f"▶️ {module_name} loaded!", 2000)
            self.refresh_module_list()

            QMessageBox.information(
                self,
                "Loaded",
                f"✅ Extension loaded successfully!\n\n" f"Module: {module_name}",
            )
        else:
            show_error_dialog_with_actions(
                parent_widget=self,
                extension_name=module_name,
                error_info=error_info,
                dependencies_dir=self.loader.browser_core.dependencies_dir,
                on_install_success=lambda: self.load_selected_module(),  # Retry on success
                on_fix_with_ai=lambda err, code: self._send_to_ai_for_fix_from_error(
                    module_name, err
                ),
                dialog_title="Load Failed",
            )

        self.refresh_module_list()

    def delete_selected_module(self):
        """Permanently delete an extension file"""
        current_item = self.module_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "No Selection", "Please select an extension to delete!"
            )
            return

        filepath = current_item.data(Qt.ItemDataRole.UserRole)
        if not filepath:
            return

        module_name = filepath.stem

        # Confirm deletion
        reply = QMessageBox.critical(
            self,
            "Delete Extension?",
            f"⚠️ Permanently delete {module_name}.py?\n\n"
            "This action cannot be undone!\n\n"
            "The file will be deleted from disk.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Unload if loaded
                module_instance = self.get_loaded_module(module_name)
                if module_instance:
                    self.loader.unload_module(module_instance)

                # Delete file
                filepath.unlink()

                # Refresh UI
                self.loader.refresh_module_manager()
                self.refresh_module_list()
                self.browser_core.show_status(f"🗑️ {module_name}.py deleted", 2000)

                QMessageBox.information(
                    self, "Deleted", f"✅ {module_name}.py has been deleted."
                )

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete:\n{e}")
