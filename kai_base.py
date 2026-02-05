"""
Enhanced kai_base.py with Runtime Error Tracking
Captures runtime errors and makes them available to AI for fixing
"""


class KaiModule:
    """Base class with runtime error tracking"""

    MODULE_TYPE_UI = "ui"
    MODULE_TYPE_BACKGROUND = "background"
    MODULE_TYPE_MANAGER = "manager"

    def __init__(self):
        self.browser_core = None
        self.enabled = True
        self.module_type = self.MODULE_TYPE_BACKGROUND
        self.ui_elements = []
        self.ui_actions = []
        self.signal_connections = []

        # Runtime error tracking
        self.runtime_errors = []
        self.max_error_history = 5
        self.last_runtime_error = None

        self._last_error_dialog_time = 0
        self._error_dialog_cooldown = 5.0  # seconds

    def initialize(self, browser_core):
        """Called when module is loaded"""
        self.browser_core = browser_core
        self.setup()

    def setup(self):
        """Override this in your module"""
        pass

    def enable(self):
        """Enable module"""
        self.enabled = True

        # Force-clear old actions with same object references
        toolbar_actions = self.browser_core.navbar.actions()
        for action in self.ui_actions:
            if action in toolbar_actions:
                self.browser_core.navbar.removeAction(action)

        # Now add all actions (fresh or reloaded)
        for action in self.ui_actions:
            self.browser_core.navbar.addAction(action)

        for element in self.ui_elements:
            element.setVisible(True)
        self.on_enabled()
        if self.browser_core:
            self.browser_core.save_module_state(self, True)

    def disable(self):
        """Disable module"""
        self.enabled = False
        if hasattr(self, "_background_threads"):
            for thread in self._background_threads[:]:
                if thread.isRunning():
                    thread.quit()
                    thread.wait(1000)
            self._background_threads.clear()
        for action in self.ui_actions:
            self.browser_core.navbar.removeAction(action)
        for element in self.ui_elements:
            element.setVisible(False)
        self.on_disabled()
        if self.browser_core:
            self.browser_core.save_module_state(self, False)

    def on_enabled(self):
        pass

    def on_disabled(self):
        pass

    def add_toolbar_action(self, action):
        """Add action to toolbar"""
        toolbar_action = self.browser_core.navbar.addAction(action)
        self.ui_actions.append(action)
        self.module_type = self.MODULE_TYPE_UI

    def add_toolbar_widget(self, widget):
        """Add widget to toolbar"""
        action = self.browser_core.navbar.addWidget(widget)
        self.ui_elements.append(widget)
        self.ui_actions.append(action)
        self.module_type = self.MODULE_TYPE_UI

    def connect_signal(self, signal, slot):
        """Connect signal"""
        signal.connect(slot)
        self.signal_connections.append((signal, slot))

    def get_preference(self, key, default=None):
        """Get preference"""
        if self.browser_core:
            module_name = self.__class__.__name__
            return self.browser_core.preferences.get_module_setting(
                module_name, key, default
            )
        return default

    def set_preference(self, key, value):
        """Set preference"""
        if self.browser_core:
            module_name = self.__class__.__name__
            self.browser_core.preferences.set_module_setting(module_name, key, value)

    # ============================================================================
    # SIMPLIFIED API HELPERS
    # ============================================================================

    def add_button(self, text, icon=None, on_click=None, checkable=False):
        """Add simple button"""
        from PyQt6.QtGui import QAction

        action = QAction(text, self.browser_core)
        if checkable:
            action.setCheckable(True)
        if on_click:
            action.triggered.connect(
                lambda checked=False: (
                    self._safe_call(on_click, checked)
                    if checkable
                    else self._safe_call(on_click)
                )
            )
        self.add_toolbar_action(action)
        return action

    def add_menu_button(self, text, items, on_select=None, icon=None):
        """Add dropdown menu button"""
        from PyQt6.QtWidgets import QMenu, QToolButton
        from PyQt6.QtGui import QAction
        from PyQt6.QtCore import Qt

        # Create menu
        menu = QMenu(self.browser_core)

        # Store items function/list for dynamic updates
        menu._items_source = items
        menu._on_select = on_select
        menu._parent_module = self

        # Connect aboutToShow to refresh menu dynamically
        def refresh_menu():
            menu.clear()
            menu_items = items() if callable(items) else items

            if menu_items:
                for item in menu_items:
                    # Handle separators
                    if item == "---":
                        menu.addSeparator()
                        continue

                    item_action = QAction(str(item), self.browser_core)

                    # Disable items that start with certain prefixes (for display only)
                    if str(item).startswith(("Current:", "Status:", "Info:")):
                        item_action.setEnabled(False)

                    if on_select:
                        item_action.triggered.connect(
                            lambda checked, i=item: self._safe_call(on_select, i)
                        )
                    menu.addAction(item_action)
            else:
                no_items = QAction("(No items)", self.browser_core)
                no_items.setEnabled(False)
                menu.addAction(no_items)

        menu.aboutToShow.connect(refresh_menu)

        # Initial population
        refresh_menu()

        # Create button
        button = QToolButton(self.browser_core)
        button.setText(text)
        button.setMenu(menu)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

        # Add to toolbar
        self.add_toolbar_widget(button)

        return menu

    def add_input(self, placeholder="", on_enter=None, on_change=None, width=200):
        """Add text input"""
        from PyQt6.QtWidgets import QLineEdit

        input_box = QLineEdit()
        input_box.setPlaceholderText(placeholder)
        input_box.setMaximumWidth(width)
        if on_enter:
            input_box.returnPressed.connect(
                lambda: self._safe_call(on_enter, input_box.text())
            )
        if on_change:
            input_box.textChanged.connect(lambda text: self._safe_call(on_change, text))
        self.add_toolbar_widget(input_box)
        return input_box

    def add_label(self, text, width=None):
        """Add label"""
        from PyQt6.QtWidgets import QLabel

        label = QLabel(text)
        if width:
            label.setFixedWidth(width)
        self.add_toolbar_widget(label)
        return label

    def show_message(self, text, title="Information", icon="info"):
        """Show message dialog"""
        from PyQt6.QtWidgets import QMessageBox

        msg = QMessageBox(self.browser_core)
        msg.setWindowTitle(title)
        msg.setText(text)
        icon_map = {
            "info": QMessageBox.Icon.Information,
            "warning": QMessageBox.Icon.Warning,
            "error": QMessageBox.Icon.Critical,
            "question": QMessageBox.Icon.Question,
        }
        msg.setIcon(icon_map.get(icon, QMessageBox.Icon.Information))
        msg.exec()

    def ask_text(self, prompt, default="", title="Input"):
        """Ask for text input"""
        from PyQt6.QtWidgets import QInputDialog

        text, ok = QInputDialog.getText(self.browser_core, title, prompt, text=default)
        return text if ok else None

    def ask_yes_no(self, question, title="Confirm"):
        """Ask yes/no"""
        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self.browser_core,
            title,
            question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def on_page_load(self, callback):
        """Page load handler"""
        self.connect_signal(
            self.browser_core.page_loaded, lambda url: self._safe_call(callback, url)
        )

    def on_url_change(self, callback):
        """URL change handler"""
        self.connect_signal(
            self.browser_core.url_changed, lambda url: self._safe_call(callback, url)
        )

    def set_interval(self, callback, seconds):
        """Run callback every N seconds"""
        from PyQt6.QtCore import QTimer

        timer = QTimer()
        timer.timeout.connect(lambda: self._safe_call(callback))
        timer.start(int(seconds * 1000))
        self.signal_connections.append((timer, callback))
        return timer

    def run_in_background(self, callback, on_complete=None):
        """Run callback in background thread with error tracking"""
        from PyQt6.QtCore import QThread, pyqtSignal

        class WorkerThread(QThread):
            finished_signal = pyqtSignal(object)
            error_signal = pyqtSignal(object)

            def __init__(self, func, module_instance):
                super().__init__()
                self.func = func
                self.module_instance = module_instance
                self.result = None
                self._last_error_dialog_time = 0
                self._error_dialog_cooldown = 5.0

            def run(self):
                try:
                    self.result = self.func()
                    self.finished_signal.emit(self.result)
                except Exception as e:
                    import traceback
                    import datetime

                    # Capture full error details
                    func_name = "background_task"
                    if hasattr(self.func, "__name__"):
                        func_name = self.func.__name__
                    elif hasattr(self.func, "func") and hasattr(
                        self.func.func, "__name__"
                    ):
                        func_name = self.func.func.__name__

                    error_info = {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "function": func_name,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "traceback": traceback.format_exc(),
                        "args": "background thread",
                        "module_name": self.module_instance.__class__.__name__,
                    }

                    # Store error
                    if not hasattr(self.module_instance, "runtime_errors"):
                        self.module_instance.runtime_errors = []
                    self.module_instance.runtime_errors.append(error_info)

                    if (
                        len(self.module_instance.runtime_errors)
                        > self.module_instance.max_error_history
                    ):
                        self.module_instance.runtime_errors.pop(0)

                    self.module_instance.last_runtime_error = error_info

                    # Print to console
                    print(f"\n{'='*60}")
                    print(f"⚠️  BACKGROUND THREAD ERROR")
                    print(f"{'='*60}")
                    print(f"Module: {error_info['module_name']}")
                    print(f"Function: {error_info['function']}")
                    print(
                        f"Error: {error_info['error_type']}: {error_info['error_message']}"
                    )
                    print(f"\nTraceback:\n{error_info['traceback']}")
                    print(f"{'='*60}\n")

                    # Emit error signal
                    self.error_signal.emit(error_info)

        # Create thread
        thread = WorkerThread(callback, self)

        if not hasattr(self, "_background_threads"):
            self._background_threads = []
        self._background_threads.append(thread)

        def on_thread_finished(result):
            """Handle successful completion"""
            if thread in self._background_threads:
                self._background_threads.remove(thread)
            if on_complete:
                self._safe_call(on_complete, result)

        def on_thread_error(error_info):
            """Handle background thread error"""
            # Clean up thread first
            if thread in self._background_threads:
                self._background_threads.remove(thread)

            # Show error dialog after a delay to ensure main thread is ready
            from PyQt6.QtCore import QTimer

            def show_dialog():
                try:
                    self._show_runtime_error_dialog(error_info)
                except Exception as e:
                    print(f"Failed to show error dialog: {e}")
                    import traceback

                    traceback.print_exc()

            # Use single-shot timer
            QTimer.singleShot(1000, show_dialog)

            # Call on_complete with error result if provided
            if on_complete:
                self._safe_call(on_complete, {"error": error_info["error_message"]})

        # Connect signals
        thread.finished_signal.connect(on_thread_finished)
        thread.error_signal.connect(on_thread_error)
        thread.start()

        return thread

    # ============================================================================
    # RUNTIME ERROR TRACKING
    # ============================================================================

    def _safe_call(self, func, *args, **kwargs):
        """
        Enhanced safe call with runtime error tracking
        Records errors so AI can see them and fix them
        """
        if not self.enabled:
            return None

        try:
            return func(*args, **kwargs)
        except Exception as e:
            import traceback
            import datetime

            # Capture detailed error info
            error_info = {
                "timestamp": datetime.datetime.now().isoformat(),
                "function": func.__name__,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc(),
                "args": str(args)[:200],  # Truncate long args
                "module_name": self.__class__.__name__,
            }

            # Add to error history
            self.runtime_errors.append(error_info)
            if len(self.runtime_errors) > self.max_error_history:
                self.runtime_errors.pop(0)

            self.last_runtime_error = error_info

            # Print to console
            error_msg = (
                f"Runtime error in {self.__class__.__name__}.{func.__name__}: {e}"
            )
            print(f"\n{'='*60}")
            print(f"⚠️  RUNTIME ERROR DETECTED")
            print(f"{'='*60}")
            print(error_msg)
            print(f"\nTraceback:\n{traceback.format_exc()}")
            print(f"{'='*60}\n")

            # Show error dialog with "Report to AI" button
            self._show_runtime_error_dialog(error_info)

            return None

    def _show_runtime_error_dialog(self, error_info):
        """Show runtime error dialog with option to report to AI"""

        import time

        # Rate limit: only show one dialog per 5 seconds
        current_time = time.time()
        if current_time - self._last_error_dialog_time < self._error_dialog_cooldown:
            print(f"⚠️  Error dialog suppressed (cooldown active)")
            return

        self._last_error_dialog_time = current_time

        try:
            from PyQt6.QtWidgets import QMessageBox, QPushButton
            from PyQt6.QtCore import Qt

            # Ensure we're on the main thread
            if not hasattr(self, "browser_core") or not self.browser_core:
                print("Cannot show dialog - no browser_core reference")
                return

            msg = QMessageBox(self.browser_core)
            msg.setWindowTitle(f"Runtime Error: {self.__class__.__name__}")
            msg.setIcon(QMessageBox.Icon.Critical)

            error_text = (
                f"<b>Function:</b> {error_info['function']}<br>"
                f"<b>Error:</b> {error_info['error_type']}<br>"
                f"<b>Message:</b> {error_info['error_message']}<br><br>"
                f"<small>{error_info['traceback'][:500]}</small>"
            )
            msg.setText(error_text)
            msg.setTextFormat(Qt.TextFormat.RichText)

            # Add "Send to AI" button if Extension Builder is available
            has_builder = any(
                m.__class__.__name__ == "ExtensionBuilderModule"
                for m in self.browser_core.modules
            )

            if has_builder:
                send_to_ai_btn = msg.addButton(
                    "🔧 Send to AI for Fix", QMessageBox.ButtonRole.ActionRole
                )

            ok_btn = msg.addButton(QMessageBox.StandardButton.Ok)

            # Show dialog and check result
            msg.exec()

            # Check if user clicked "Send to AI"
            if has_builder and msg.clickedButton() == send_to_ai_btn:
                self._send_error_to_ai(error_info)

        except Exception as e:
            print(f"Error showing runtime error dialog: {e}")
            import traceback

            traceback.print_exc()

    def _send_error_to_ai(self, error_info):
        """Send runtime error to AI Extension Builder"""
        try:
            # Find Extension Builder module
            extension_builder = None
            for module in self.browser_core.modules:
                if module.__class__.__name__ == "ExtensionBuilderModule":
                    extension_builder = module
                    break

            if not extension_builder:
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.warning(
                    self.browser_core,
                    "Extension Builder Not Found",
                    "Cannot send error to AI - Extension Builder module not loaded.",
                )
                return

            # Store error context
            if not hasattr(self.browser_core, "_pending_runtime_error"):
                self.browser_core._pending_runtime_error = {}

            self.browser_core._pending_runtime_error = {
                "module_name": self.__class__.__name__,
                "module_file": self.__class__.__module__.split(".")[-1],
                "error_info": error_info,
                "source_code": self._get_source_code(),
            }

            # Open Extension Builder with error context
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(100, extension_builder.show_builder)

        except Exception as e:
            print(f"Failed to send error to AI: {e}")
            import traceback

            traceback.print_exc()

    def _open_builder_with_error(self, error_info):
        """Open Extension Builder with error context"""
        try:
            # Store error globally for builder to access
            if not hasattr(self.browser_core, "_pending_runtime_error"):
                self.browser_core._pending_runtime_error = {}

            self.browser_core._pending_runtime_error = {
                "module_name": self.__class__.__name__,
                "module_file": self.__class__.__module__.split(".")[-1],
                "error_info": error_info,
                "source_code": self._get_source_code(),
            }

            # Find Extension Builder module
            builder_module = None
            for module in self.browser_core.modules:
                if module.__class__.__name__ == "ExtensionBuilderModule":
                    builder_module = module
                    break

            if builder_module:
                # Open the builder dialog with a delay
                from PyQt6.QtCore import QTimer

                QTimer.singleShot(100, builder_module.show_builder)
            else:
                print("⚠️  Extension Builder not loaded - cannot report error")

        except Exception as e:
            print(f"Failed to open Extension Builder: {e}")
            import traceback

            traceback.print_exc()

    def _get_source_code(self):
        """Get the source code of this module"""
        try:
            import inspect
            import sys

            # Get the module
            module_name = self.__class__.__module__
            if module_name in sys.modules:
                module = sys.modules[module_name]
                source = inspect.getsource(module)
                return source
        except:
            pass

        # Fallback: read from file
        try:
            from pathlib import Path
            import sys

            module_file = self.__class__.__module__.split(".")[-1]

            if hasattr(sys, "frozen"):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).parent

            module_path = base_dir / "modules" / f"{module_file}.py"

            if module_path.exists():
                with open(module_path, "r", encoding="utf-8") as f:
                    return f.read()
        except:
            pass

        return None
