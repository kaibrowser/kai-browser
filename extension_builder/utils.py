"""
Extension Builder - Utilities
Shared utilities for validation, loading, and module management
CONSOLIDATED: Added shared functions from ai_tab modules
UPDATED: Improved unload_module with thorough cleanup
"""

import sys
import re
import importlib
import importlib.util
import inspect
import gc
from pathlib import Path
from kai_base import KaiModule


def validate_python_syntax(code):
    """
    Validate Python syntax before attempting to load
    Returns: (is_valid, error_message)
    """
    if not code or not code.strip():
        return False, "Code is empty"

    try:
        compile(code, "<string>", "exec")
        return True, None
    except SyntaxError as e:
        error_msg = f"Syntax error on line {e.lineno}: {e.msg}"
        if e.text:
            error_msg += f"\n\nProblematic line:\n{e.text}"
        return False, error_msg
    except Exception as e:
        return False, f"Code validation error: {str(e)}"


def strip_markdown_fences(code):
    """
    Strip markdown code fences that AI adds despite instructions
    Handles: ```python\n...\n``` or ```\n...\n```
    """
    code = re.sub(r"^```python\s*\n", "", code, flags=re.MULTILINE)
    code = re.sub(r"^```\s*\n", "", code, flags=re.MULTILINE)
    code = re.sub(r"\n```\s*$", "", code, flags=re.MULTILINE)
    return code.strip()


def build_ai_context(current_message, conversation_history, current_code=None):
    """
    Build AI context from conversation history and current code
    """
    context = {
        "user_prompt": current_message,
        "has_existing_code": bool(current_code),
        "current_code": current_code if current_code else None,
        "is_modification_request": bool(current_code and len(conversation_history) > 1),
        "conversation_history": [],
    }

    recent_history = conversation_history[-10:]
    for msg in recent_history:
        if msg.get("role") == "user":
            context["conversation_history"].append(
                {"role": "user", "content": msg.get("message", "")}
            )
        elif msg.get("role") == "assistant" and "code" in msg:
            context["conversation_history"].append(
                {
                    "role": "assistant",
                    "content": f"Generated code with {len(msg['code'])} characters",
                }
            )

    return context


class ModuleLoader:
    """Handles hot-loading and unloading of modules"""

    def __init__(self, browser_core, modules_dir):
        self.browser_core = browser_core
        self.modules_dir = modules_dir

    @staticmethod
    def class_to_filename(class_name):
        """Convert ClassName to file_name"""
        if class_name.endswith("Module"):
            class_name = class_name[:-6]
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", class_name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

    def hot_load_module(self, module_name):
        """
        Hot load module with aggressive cache clearing
        Returns: (success: bool, error_info: dict)
        """
        try:
            full_module_name = f"modules.{module_name}"

            # Clear from sys.modules
            if full_module_name in sys.modules:
                del sys.modules[full_module_name]

            # Get the actual .py file path
            py_file = self.modules_dir / f"{module_name}.py"

            if not py_file.exists():
                return False, {
                    "type": "FileNotFound",
                    "message": f"Module file not found: {py_file}",
                }

            # Clear bytecode cache
            try:
                cache_file = importlib.util.cache_from_source(str(py_file))
                import os

                if os.path.exists(cache_file):
                    os.remove(cache_file)
            except:
                pass

            # Clear __pycache__
            try:
                pycache_dir = py_file.parent / "__pycache__"
                if pycache_dir.exists():
                    for cache_file in pycache_dir.glob(f"{module_name}*.pyc"):
                        cache_file.unlink()
            except:
                pass

            # Force garbage collection
            gc.collect()

            # Load module from file path
            spec = importlib.util.spec_from_file_location(full_module_name, py_file)
            if not spec or not spec.loader:
                return False, {
                    "type": "ImportError",
                    "message": "Could not load module spec",
                }

            module = importlib.util.module_from_spec(spec)
            sys.modules[full_module_name] = module
            spec.loader.exec_module(module)

            # Find plugin/module class
            extension_class = None
            candidates = []

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name.startswith("_"):
                    continue

                if obj.__module__ != module.__name__:
                    continue

                if any(
                    suffix in name
                    for suffix in ["Dialog", "Window", "Widget", "Helper"]
                ):
                    continue

                is_kai_module = False
                try:
                    is_kai_module = issubclass(obj, KaiModule) and obj != KaiModule
                except:
                    pass

                has_activate = "activate" in dir(obj)

                has_browser_param = False
                try:
                    sig = inspect.signature(obj.__init__)
                    params = [
                        p.name for p in sig.parameters.values() if p.name != "self"
                    ]
                    has_browser_param = "browser" in params
                except:
                    pass

                if is_kai_module or has_activate or has_browser_param:
                    candidates.append((name, obj))

            if candidates:
                for name, obj in candidates:
                    if "Module" in name or "Plugin" in name:
                        extension_class = obj
                        break

                if not extension_class:
                    extension_class = candidates[0][1]

            if not extension_class:
                return False, {
                    "type": "ClassNotFound",
                    "message": "No plugin/module class found",
                }

            # Create instance
            extension = None

            try:
                sig = inspect.signature(extension_class.__init__)
                params = [p for p in sig.parameters.values() if p.name != "self"]

                if len(params) > 0:
                    extension = extension_class(self.browser_core)
                    print(f"   ✓ Natural pattern: {extension_class.__name__}")
                else:
                    extension = extension_class()
                    print(f"   ✓ Legacy pattern: {extension_class.__name__}")

            except TypeError as e:
                return False, {
                    "type": "InitializationError",
                    "message": f"Module initialization failed: {str(e)}",
                }

            if not extension:
                return False, {
                    "type": "InitializationError",
                    "message": "Failed to instantiate plugin",
                }

            # Load into browser
            try:
                self.browser_core.load_module(extension)
                print(f"  ✓ Hot-loaded: {extension_class.__name__}")
                return True, None
            except Exception as e:
                import traceback

                return False, {
                    "type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }

        except Exception as e:
            import traceback

            return False, {
                "type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc(),
            }

    def unload_module(self, module):
        """Completely unload a module - handles both natural and legacy patterns"""
        try:
            module_name = module.__class__.__name__
            module_file = module.__class__.__module__

            print(f"\n🔄 Unloading: {module_name}")

            # Check if it's a KaiModule (has enabled attribute and ui tracking)
            is_kai_module = hasattr(module, "enabled") and hasattr(module, "ui_actions")

            if is_kai_module:
                # ============================================================
                # KaiModule cleanup (legacy pattern)
                # ============================================================

                # Disable first (this removes actions from toolbar)
                if module.enabled:
                    try:
                        module.disable()
                    except Exception as e:
                        print(f"  ⚠️ Disable error: {e}")

                # Double-check: remove any remaining ui_actions
                for action in module.ui_actions[:]:
                    try:
                        # Get widget for action (if it's a widget action)
                        widget = self.browser_core.navbar.widgetForAction(action)
                        if widget:
                            # Disconnect any signals from the widget
                            try:
                                widget.blockSignals(True)
                            except:
                                pass
                            # Remove menu if exists
                            if hasattr(widget, "menu") and widget.menu():
                                widget.menu().clear()
                                widget.menu().deleteLater()
                            widget.setParent(None)
                            widget.deleteLater()
                        self.browser_core.navbar.removeAction(action)
                        action_text = (
                            action.text() if hasattr(action, "text") else "unknown"
                        )
                        print(f"  ✓ Removed action: {action_text}")
                    except Exception as e:
                        print(f"  ⚠️ Failed to remove action: {e}")
                module.ui_actions.clear()

                # Remove ui_elements (widgets)
                for widget in module.ui_elements[:]:
                    try:
                        # Block signals before cleanup
                        try:
                            widget.blockSignals(True)
                        except:
                            pass
                        # Clear menu if it's a tool button
                        if hasattr(widget, "menu") and widget.menu():
                            widget.menu().clear()
                            widget.menu().deleteLater()
                        widget.setParent(None)
                        widget.deleteLater()
                        print(f"  ✓ Removed widget: {widget.__class__.__name__}")
                    except Exception as e:
                        print(f"  ⚠️ Failed to remove widget: {e}")
                module.ui_elements.clear()

                # Disconnect signals
                for signal, slot in module.signal_connections[:]:
                    try:
                        signal.disconnect(slot)
                    except:
                        pass
                module.signal_connections.clear()

                # Stop background threads
                if hasattr(module, "_background_threads"):
                    for thread in module._background_threads[:]:
                        try:
                            if thread.isRunning():
                                thread.quit()
                                thread.wait(1000)
                                if thread.isRunning():
                                    thread.terminate()
                        except:
                            pass
                    module._background_threads.clear()

                # Stop any QTimers
                if hasattr(module, "_timers"):
                    for timer in module._timers[:]:
                        try:
                            timer.stop()
                            timer.deleteLater()
                        except:
                            pass
                    module._timers.clear()

                print(f"  ✓ KaiModule cleanup complete")

            else:
                # ============================================================
                # Natural plugin cleanup (non-KaiModule)
                # ============================================================

                # Call deactivate if exists
                if hasattr(module, "deactivate"):
                    try:
                        module.deactivate()
                    except Exception as e:
                        print(f"  ⚠️ Deactivate error: {e}")

                # Remove tracked actions if plugin uses this pattern
                if hasattr(module, "_tracked_actions"):
                    for action in module._tracked_actions[:]:
                        try:
                            widget = self.browser_core.navbar.widgetForAction(action)
                            if widget:
                                if hasattr(widget, "menu") and widget.menu():
                                    widget.menu().clear()
                                    widget.menu().deleteLater()
                                widget.setParent(None)
                                widget.deleteLater()
                            self.browser_core.navbar.removeAction(action)
                        except:
                            pass
                    module._tracked_actions.clear()

                # Check for toolbar attribute (some natural plugins store it)
                if hasattr(module, "toolbar_action"):
                    try:
                        action = module.toolbar_action
                        widget = self.browser_core.navbar.widgetForAction(action)
                        if widget:
                            widget.setParent(None)
                            widget.deleteLater()
                        self.browser_core.navbar.removeAction(action)
                    except:
                        pass

                if hasattr(module, "toolbar_widget"):
                    try:
                        module.toolbar_widget.setParent(None)
                        module.toolbar_widget.deleteLater()
                    except:
                        pass

                print(f"  ✓ Natural plugin cleanup complete")

            # ============================================================
            # Aggressive toolbar cleanup - find orphaned items
            # ============================================================
            self._cleanup_toolbar_for_module(module_file)

            # Remove from modules list
            if module in self.browser_core.modules:
                self.browser_core.modules.remove(module)
                print(f"  ✓ Removed from modules list")

            # Clear any references the module might hold
            try:
                if hasattr(module, "browser_core"):
                    module.browser_core = None
                if hasattr(module, "browser"):
                    module.browser = None
                if hasattr(module, "toolbar"):
                    module.toolbar = None
                if hasattr(module, "web_view"):
                    module.web_view = None
            except:
                pass

            # Delete module reference
            del module

            # Force garbage collection
            gc.collect()

            print(f"✅ Unload complete\n")

        except Exception as e:
            print(f"  ✗ Failed to unload: {e}")
            import traceback

            traceback.print_exc()

    def _cleanup_toolbar_for_module(self, module_file):
        """
        Aggressively clean toolbar of any items that might belong to this module.
        This catches items that weren't properly tracked.
        """
        try:
            toolbar = self.browser_core.navbar
            actions_to_remove = []
            widgets_to_remove = []

            # Extract just the module name for matching
            # module_file might be "modules.my_extension" or just "my_extension"
            module_name_parts = module_file.split(".")
            module_short_name = (
                module_name_parts[-1] if module_name_parts else module_file
            )

            # Scan all toolbar actions
            for action in toolbar.actions():
                should_remove = False

                try:
                    # Check the widget for this action
                    widget = toolbar.widgetForAction(action)
                    if widget:
                        # Check if widget class was defined in this module
                        widget_module = widget.__class__.__module__
                        if module_short_name in str(
                            widget_module
                        ) or module_file in str(widget_module):
                            should_remove = True
                            if widget not in widgets_to_remove:
                                widgets_to_remove.append(widget)

                    # Check action's parent
                    parent = action.parent()
                    if parent:
                        parent_module = parent.__class__.__module__
                        if module_short_name in str(
                            parent_module
                        ) or module_file in str(parent_module):
                            should_remove = True

                    # Check connected slots (if possible)
                    # This is tricky in PyQt6, but we can try
                    if hasattr(action, "triggered"):
                        try:
                            # Check if any receivers are from this module
                            receiver_count = action.receivers(action.triggered)
                            # Can't easily get receiver module, but we marked should_remove above
                        except:
                            pass

                except Exception:
                    pass

                if should_remove and action not in actions_to_remove:
                    actions_to_remove.append(action)

            # Remove identified actions
            for action in actions_to_remove:
                try:
                    toolbar.removeAction(action)
                    print(
                        f"  ✓ Removed orphaned action: {action.text() if hasattr(action, 'text') else '?'}"
                    )
                except Exception as e:
                    print(f"  ⚠️ Failed to remove orphaned action: {e}")

            # Remove identified widgets
            for widget in widgets_to_remove:
                try:
                    # Clear menu if exists
                    if hasattr(widget, "menu") and widget.menu():
                        widget.menu().clear()
                        widget.menu().deleteLater()
                    widget.setParent(None)
                    widget.deleteLater()
                    print(f"  ✓ Removed orphaned widget: {widget.__class__.__name__}")
                except Exception as e:
                    print(f"  ⚠️ Failed to remove orphaned widget: {e}")

            # Also scan toolbar layout directly for any missed widgets
            if toolbar.layout():
                layout = toolbar.layout()
                items_to_remove = []

                for i in range(layout.count()):
                    try:
                        item = layout.itemAt(i)
                        if item and item.widget():
                            widget = item.widget()
                            widget_module = str(widget.__class__.__module__)

                            if (
                                module_short_name in widget_module
                                or module_file in widget_module
                            ):
                                if widget not in widgets_to_remove:
                                    items_to_remove.append(widget)
                    except:
                        pass

                for widget in items_to_remove:
                    try:
                        if hasattr(widget, "menu") and widget.menu():
                            widget.menu().clear()
                            widget.menu().deleteLater()
                        widget.setParent(None)
                        widget.deleteLater()
                        print(
                            f"  ✓ Removed orphaned layout widget: {widget.__class__.__name__}"
                        )
                    except Exception as e:
                        print(f"  ⚠️ Failed to remove layout widget: {e}")

        except Exception as e:
            print(f"  ⚠️ Toolbar cleanup error: {e}")

    def refresh_module_manager(self):
        """Refresh module manager menu"""
        from PyQt6.QtCore import QTimer

        def do_refresh():
            for module in self.browser_core.modules:
                if module.__class__.__name__ == "ModuleManagerModule":
                    try:
                        module.populate_menu()
                        print(f"  ✓ Module manager refreshed")
                    except Exception as e:
                        print(f"  ✗ Failed to refresh module manager: {e}")
                    break

        QTimer.singleShot(50, do_refresh)


class CodeTemplates:
    """Code templates for different extension types"""

    SIMPLE = """\"\"\"
{description}
\"\"\"
from PyQt6.QtWidgets import QToolButton, QMenu
from PyQt6.QtGui import QAction


class {class_name}:
    \"\"\"Your custom extension\"\"\"
    
    def __init__(self, browser):
        self.browser = browser
        self.toolbar = browser.toolbar
    
    def activate(self):
        \"\"\"Set up your extension\"\"\"
        button = QToolButton()
        button.setText("🎯 My Button")
        button.clicked.connect(self.on_click)
        self.toolbar.addWidget(button)
        
        print("✅ {class_name} loaded!")
    
    def on_click(self):
        \"\"\"Called when button is clicked\"\"\"
        web_view = self.browser.get_active_web_view()
        url = web_view.url().toString() if web_view else "No active tab"
        print(f"🎯 Button clicked! Current URL: {{url}}")
"""

    BACKGROUND = """\"\"\"
{description}
\"\"\"


class {class_name}:
    \"\"\"Background extension - runs automatically\"\"\"
    
    def __init__(self, browser):
        self.browser = browser
        self.is_background = True
        self._connections = []  # Track signal connections
    
    def activate(self):
        \"\"\"Set up background monitoring on all tabs\"\"\"
        # Connect to existing tabs
        for tab in self.browser.tabs:
            web_view = tab.get_web_view()
            web_view.loadFinished.connect(self.on_page_load)
            self._connections.append((web_view, web_view.loadFinished, self.on_page_load))
        
        # Monitor new tabs being created
        # Hook into tab creation by wrapping create_new_tab
        self._original_create_tab = self.browser.create_new_tab
        self.browser.create_new_tab = self._wrapped_create_tab
        
        print("✅ {class_name} monitoring started")
    
    def deactivate(self):
        \"\"\"Stop background monitoring\"\"\"
        # Disconnect from all tabs
        for web_view, signal, slot in self._connections:
            try:
                signal.disconnect(slot)
            except:
                pass
        self._connections.clear()
        
        # Restore original create_new_tab
        if hasattr(self, '_original_create_tab'):
            self.browser.create_new_tab = self._original_create_tab
        
        print("❌ {class_name} monitoring stopped")
    
    def _wrapped_create_tab(self, url=None):
        \"\"\"Wrap tab creation to connect to new tabs\"\"\"
        new_tab = self._original_create_tab(url)
        
        # Connect to the new tab
        web_view = new_tab.get_web_view()
        web_view.loadFinished.connect(self.on_page_load)
        self._connections.append((web_view, web_view.loadFinished, self.on_page_load))
        
        return new_tab
    
    def on_page_load(self, success):
        \"\"\"Called when any page finishes loading in any tab\"\"\"
        if not success:
            return
        
        # Find which tab triggered this
        sender = self.browser.sender()
        for tab in self.browser.tabs:
            if tab.get_web_view() == sender:
                url = tab.get_url()
                print(f"📄 Page loaded: {{url}}")
                
                # Do something with the URL
                if "example.com" in url:
                    print("Detected example.com!")
                break
"""

    INJECTOR = """\"\"\"
{description}
\"\"\"
from PyQt6.QtWidgets import QToolButton, QMenu
from PyQt6.QtGui import QAction


class {class_name}:
    \"\"\"JavaScript injector extension\"\"\"
    
    def __init__(self, browser):
        self.browser = browser
        self.toolbar = browser.toolbar
        self.inject_enabled = False
    
    def activate(self):
        \"\"\"Set up injector with toggle button\"\"\"
        button = QToolButton()
        button.setText("💉 Inject JS")
        button.setCheckable(True)
        button.setChecked(self.inject_enabled)
        button.toggled.connect(self.toggle_inject)
        self.toolbar.addWidget(button)
        
        # Monitor page loads
        web_view = self.browser.get_active_web_view()
        if web_view:
            web_view.loadFinished.connect(self.on_page_load)
        
        print("✅ {class_name} ready")
    
    def toggle_inject(self, checked):
        \"\"\"Toggle auto-injection on/off\"\"\"
        self.inject_enabled = checked
        status = "enabled" if checked else "disabled"
        print(f"Auto-inject {{status}}")
    
    def on_page_load(self, success):
        \"\"\"Inject JavaScript when page loads\"\"\"
        if not success or not self.inject_enabled:
            return
        
        # Your custom JavaScript here
        js_code = '''
        (function() {{
            console.log('Custom JS injected!');
            // Add your JavaScript here
            document.body.style.border = '3px solid blue';
        }})();
        '''
        
        web_view = self.browser.get_active_web_view()
        if web_view:
            web_view.page().runJavaScript(js_code)
"""

    BLANK = """\"\"\"
{description}
\"\"\"


class {class_name}:
    \"\"\"Blank extension template\"\"\"
    
    def __init__(self, browser):
        self.browser = browser
    
    def activate(self):
        \"\"\"Set up your extension\"\"\"
        # Your code here
        pass
"""

    @classmethod
    def get_template(cls, template_type, class_name, description):
        """Get template code by type"""
        templates = {
            "simple": cls.SIMPLE,
            "background": cls.BACKGROUND,
            "injector": cls.INJECTOR,
            "blank": cls.BLANK,
        }

        template = templates.get(template_type, cls.SIMPLE)
        return template.format(class_name=class_name, description=description)
