"""
Module Loader - Plugin management system
"""


class ModuleLoader:
    """Handles loading, unloading, and managing browser modules"""

    def __init__(self, browser):
        self.browser = browser
        self.modules = []
        self._module_metadata = {}

    def load_module(self, module):
        """Load a module - supports both natural and legacy patterns"""
        module_name = module.__class__.__name__

        # Clear auto-disable flag when reloading a module
        if hasattr(self.browser, "exception_handler"):
            if self.browser.exception_handler.clear_disabled_flag(module):
                print(f"✓ Cleared auto-disable flag for {module_name}")

        # Check if it's new pattern (has activate method) or old pattern (has initialize)
        if hasattr(module, "activate"):
            # New natural pattern - module already initialized
            # Track the toolbar state BEFORE activation
            actions_before = set(self.browser.navbar.actions())

            module.activate()

            # Track the toolbar state AFTER activation
            actions_after = set(self.browser.navbar.actions())

            # Find new actions added by this module
            new_actions = actions_after - actions_before

            # Store the actions for this module so we can hide/remove them later
            if not hasattr(module, "_tracked_actions"):
                module._tracked_actions = []
            module._tracked_actions.extend(new_actions)

            self.modules.append(module)
            print(
                f"✓ Activated module: {module_name} (tracked {len(new_actions)} actions)"
            )
        else:
            # Old pattern - needs initialization
            module.initialize(self.browser)
            self.modules.append(module)

            # Load saved state
            saved_state = self.browser.preferences.get_module_state(module_name)
            if saved_state:
                module.enable()
            else:
                module.disable()

            print(
                f"✓ Loaded module: {module_name} (State: {'enabled' if saved_state else 'disabled'})"
            )

    def unload_module(self, module):
        """Unload a module - supports both patterns"""
        module_name = module.__class__.__name__
        module_id = id(module)

        # Clear auto-disable tracking
        if hasattr(self.browser, "exception_handler"):
            self.browser.exception_handler.clear_disabled_flag(module)

        # Natural plugin with deactivate()
        if hasattr(module, "deactivate"):
            try:
                module.deactivate()
                print(f"✓ Deactivated: {module_name}")
            except Exception as e:
                print(f"⚠️ Deactivate error in {module_name}: {e}")

        # Legacy pattern cleanup
        if hasattr(module, "disable"):
            try:
                module.disable()
            except:
                pass

        # Clean up tracked widgets/actions
        if module_id in self._module_metadata:
            metadata = self._module_metadata[module_id]

            # Remove widgets
            for widget in metadata["widgets"]:
                try:
                    widget.setParent(None)
                    widget.deleteLater()
                except:
                    pass

            # Remove actions
            for action in metadata["actions"]:
                try:
                    self.browser.navbar.removeAction(action)
                except:
                    pass

            del self._module_metadata[module_id]

        # Remove from modules list
        if module in self.modules:
            self.modules.remove(module)

        print(f"✓ Unloaded: {module_name}")

    def save_module_state(self, module, enabled):
        """Save a module's state to preferences"""
        module_name = module.__class__.__name__
        self.browser.preferences.set_module_state(module_name, enabled)
