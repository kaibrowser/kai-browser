"""
Module Manager - Fixed to Support Natural Plugins
Now detects both legacy KaiModule and natural plugin patterns
"""

from PyQt6.QtWidgets import QMenu, QMessageBox, QToolButton
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QUrl
from kai_base import KaiModule
from about_dialog import show_about_dialog


class ModuleManagerModule(KaiModule):
    """Manages other modules with a dropdown menu"""

    def __init__(self):
        super().__init__()
        self.module_type = self.MODULE_TYPE_MANAGER
        # Track natural plugin states
        self.natural_plugin_states = {}

    def setup(self):
        """Add the Extensions dropdown button to the toolbar"""
        # Create the Extensions menu
        self.extensions_menu = QMenu(self.browser_core)

        # Create a proper tool button with popup menu
        self.extensions_button = QToolButton(self.browser_core)
        self.extensions_button.setText("🧩")
        self.extensions_button.setToolTip("Extensions")
        self.extensions_button.setMenu(self.extensions_menu)
        self.extensions_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.extensions_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

        # Add the button to the toolbar
        self.add_toolbar_widget(self.extensions_button)

        # Load saved states for natural plugins
        self._load_natural_plugin_states()

        # Populate the menu with all loaded modules
        self.populate_menu()

        self.browser_core.show_status("Module Manager loaded", 2000)

    def _load_natural_plugin_states(self):
        """Load saved enable/disable states for natural plugins"""
        for module in self.browser_core.modules:
            if not hasattr(module, "module_type"):
                module_name = module.__class__.__name__
                # Get saved state (default to True/enabled)
                saved_state = self.browser_core.preferences.get_module_state(
                    module_name
                )
                if saved_state is None:
                    saved_state = True
                self.natural_plugin_states[id(module)] = saved_state

                # Apply initial state
                if not saved_state:
                    self._hide_natural_plugin(module)

    def populate_menu(self):
        """Populate the menu with all loaded modules"""
        self.extensions_menu.clear()

        # Clean up orphaned IDs from tracking
        orphaned_ids = []
        for module_id in self.natural_plugin_states:
            found = any(id(m) == module_id for m in self.browser_core.modules)
            if not found:
                orphaned_ids.append(module_id)

        for module_id in orphaned_ids:
            del self.natural_plugin_states[module_id]
            print(f"  ✓ Cleaned up orphaned tracking ID: {module_id}")

        # Add Marketplace button at the top
        marketplace_action = QAction("🛒 Marketplace", self.browser_core)
        marketplace_action.triggered.connect(self.open_marketplace)
        self.extensions_menu.addAction(marketplace_action)

        # Add Upload link
        upload_action = QAction("📤 Upload Extension", self.browser_core)
        upload_action.triggered.connect(self.open_upload)
        self.extensions_menu.addAction(upload_action)

        self.extensions_menu.addSeparator()

        # Separate modules by type
        ui_modules = []
        background_modules = []
        natural_plugins = []
        natural_background_plugins = []  # ← NEW

        for module in self.browser_core.modules:
            # Skip the module manager itself
            if isinstance(module, ModuleManagerModule):
                continue

            # Check if it's a natural plugin (no 'module_type' attribute)
            if not hasattr(module, "module_type"):
                # Check if it's a background plugin
                if hasattr(module, "is_background") and module.is_background:
                    natural_background_plugins.append(module)  # ← NEW
                else:
                    natural_plugins.append(module)
            elif module.module_type == KaiModule.MODULE_TYPE_UI:
                ui_modules.append(module)
            elif module.module_type == KaiModule.MODULE_TYPE_BACKGROUND:
                background_modules.append(module)

        # Sort alphabetically by class name
        ui_modules.sort(key=lambda m: m.__class__.__name__)
        background_modules.sort(key=lambda m: m.__class__.__name__)
        natural_plugins.sort(key=lambda m: m.__class__.__name__)
        natural_background_plugins.sort(key=lambda m: m.__class__.__name__)  # ← NEW

        # Add Natural Plugins section (new pattern)
        if natural_plugins:
            header = QAction("📦 My Extensions", self.browser_core)
            header.setEnabled(False)
            self.extensions_menu.addAction(header)

            for module in natural_plugins:
                self._add_natural_plugin_action(module)

            self.extensions_menu.addSeparator()

        # Add Natural Background Plugins section ← NEW SECTION
        if natural_background_plugins:
            header = QAction("🔧 Background Extensions", self.browser_core)
            header.setEnabled(False)
            self.extensions_menu.addAction(header)

            for module in natural_background_plugins:
                self._add_natural_plugin_action(module)

            self.extensions_menu.addSeparator()

        # Add UI Extensions section
        if ui_modules:
            header = QAction("⚙️ System Extensions", self.browser_core)
            header.setEnabled(False)
            self.extensions_menu.addAction(header)

            for module in ui_modules:
                self._add_module_action(module)

            self.extensions_menu.addSeparator()

        # Add Legacy Background Extensions section (if any exist)
        if background_modules:
            header = QAction("🔧 Background Extensions (Legacy)", self.browser_core)
            header.setEnabled(False)
            self.extensions_menu.addAction(header)

            for module in background_modules:
                self._add_module_action(module)

            self.extensions_menu.addSeparator()

        # Add info option
        info_action = QAction("ℹ️  About", self.browser_core)
        info_action.triggered.connect(self.show_info)
        self.extensions_menu.addAction(info_action)

    def open_marketplace(self):
        """Open the kai marketplace in the browser"""
        self.browser_core.browser.setUrl(QUrl("https://kaibrowser.com/marketplace"))
        self.browser_core.show_status("Opening Marketplace...", 2000)

    def open_upload(self):
        """Open the upload page in the browser"""
        self.browser_core.browser.setUrl(QUrl("https://kaibrowser.com/upload"))
        self.browser_core.show_status("Opening Upload page...", 2000)

    def _add_natural_plugin_action(self, module):
        """Add a natural plugin to the menu with enable/disable support"""
        # Get the class name
        class_name = module.__class__.__name__

        # Try to get module file name (more reliable for natural plugins)
        module_file = module.__class__.__module__.split(".")[-1]

        # Use file name if available, otherwise use class name
        if module_file and module_file != "__main__":
            # Convert file_name to Title Case
            module_name = module_file.replace("_", " ").title()
        else:
            # Fallback to class name
            module_name = class_name.replace("Plugin", "").replace("Module", "")
            module_name = module_name.replace("_", " ").title()

        # If still empty, use class name as-is
        if not module_name.strip():
            module_name = class_name

        action = QAction(f"  {module_name}", self.browser_core)
        action.setCheckable(True)

        # Get current state
        is_enabled = self.natural_plugin_states.get(id(module), True)
        action.setChecked(is_enabled)

        # NOW ENABLED - can toggle
        action.triggered.connect(
            lambda checked, m=module: self.toggle_natural_plugin(m, checked)
        )

        self.extensions_menu.addAction(action)

    def _add_module_action(self, module):
        """Add a legacy KaiModule to the menu"""
        module_name = module.__class__.__name__.replace("Module", "")
        module_name = module_name.replace("_", " ").title()

        action = QAction(f"  {module_name}", self.browser_core)
        action.setCheckable(True)
        action.setChecked(module.enabled)

        # Connect to enable/disable function
        action.triggered.connect(
            lambda checked, m=module: self.toggle_module(m, checked)
        )

        self.extensions_menu.addAction(action)

    def toggle_module(self, module, enabled):
        """Enable or disable a legacy module"""
        module_name = module.__class__.__name__.replace("Module", "")

        if enabled:
            module.enable()
            self.browser_core.show_status(f"✓ {module_name} enabled")
        else:
            module.disable()
            self.browser_core.show_status(f"✗ {module_name} disabled")

    def toggle_natural_plugin(self, module, enabled):
        """Enable or disable a natural plugin"""
        module_name = module.__class__.__name__.replace("Plugin", "").replace(
            "Module", ""
        )

        # Update state
        self.natural_plugin_states[id(module)] = enabled

        # Save to preferences
        self.browser_core.preferences.set_module_state(
            module.__class__.__name__, enabled
        )

        if enabled:
            # Call activate if it exists
            # if hasattr(module, "activate"):
            #     try:
            #         module.activate()
            #     except Exception as e:
            #         print(f"⚠️ Failed to activate {module_name}: {e}")
            self._show_natural_plugin(module)
            self.browser_core.show_status(f"✓ {module_name} enabled")
        else:
            # Call deactivate if it exists
            if hasattr(module, "deactivate"):
                try:
                    module.deactivate()
                except Exception as e:
                    print(f"⚠️ Failed to deactivate {module_name}: {e}")
            self._hide_natural_plugin(module)
            self.browser_core.show_status(f"✗ {module_name} disabled")

    def _show_natural_plugin(self, module):
        """Show a natural plugin's UI elements"""
        # Show all tracked actions/widgets
        if hasattr(module, "_tracked_actions"):
            for action in module._tracked_actions:
                action.setVisible(True)
                # Also show the widget if it has one
                widget = self.browser_core.navbar.widgetForAction(action)
                if widget:
                    widget.setVisible(True)

    def _hide_natural_plugin(self, module):
        """Hide a natural plugin's UI elements"""
        # Hide all tracked actions/widgets
        if hasattr(module, "_tracked_actions"):
            for action in module._tracked_actions:
                action.setVisible(False)
                # Also hide the widget if it has one
                widget = self.browser_core.navbar.widgetForAction(action)
                if widget:
                    widget.setVisible(False)

    def show_info(self):
        """Show about dialog"""
        show_about_dialog(self.browser_core)
