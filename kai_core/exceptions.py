"""
Exception Handling - Global error tracking and auto-disable system
With user-friendly error messages and auto-install for missing packages
CONSOLIDATED: Uses shared error_dialogs module
"""

import sys
import traceback
import datetime
from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import QTimer, Qt
from pathlib import Path

# Import from consolidated error_dialogs module
from extension_builder.error_dialogs import (
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
    # Remove common suffixes
    name = class_name
    for suffix in ["Module", "Plugin", "Extension"]:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break

    # Split camelCase/PascalCase into words
    result = []
    for char in name:
        if char.isupper() and result:
            result.append(" ")
        result.append(char)

    return "".join(result).strip() or class_name


class ExceptionHandler:
    """Manages global exception handling and module error tracking"""

    def __init__(self, browser):
        self.browser = browser
        self._original_excepthook = None
        self._disabled_modules = set()
        self._last_error_time = {}

    def install(self):
        """Install global Qt exception handler to catch ALL errors"""
        self._original_excepthook = sys.excepthook

        def global_exception_handler(exc_type, exc_value, exc_traceback):
            """Catch ALL uncaught exceptions"""
            error_info = {
                "timestamp": datetime.datetime.now().isoformat(),
                "error_type": exc_type.__name__,
                "error_message": str(exc_value),
                "traceback": "".join(
                    traceback.format_exception(exc_type, exc_value, exc_traceback)
                ),
                "source": "global_handler",
            }

            # Try to identify which module caused it
            tb_lines = error_info["traceback"].split("\n")
            for line in tb_lines:
                if "/modules/" in line:
                    try:
                        module_file = line.split("/modules/")[1].split(".py")[0]
                        error_info["module_file"] = module_file
                        error_info["module_name"] = self._filename_to_classname(
                            module_file
                        )
                        error_info["friendly_name"] = friendly_name(
                            error_info["module_name"]
                        )
                        break
                    except:
                        pass

            # Print to console (keep technical details here)
            print(f"\n{'='*60}")
            print(f"⚠️  GLOBAL EXCEPTION CAUGHT")
            print(f"{'='*60}")
            if "module_name" in error_info:
                print(f"Module: {error_info['module_name']}")
            print(f"Error: {error_info['error_type']}: {error_info['error_message']}")
            print(f"\nTraceback:\n{error_info['traceback']}")
            print(f"{'='*60}\n")

            # Store error for AI
            if "module_name" in error_info:
                self.browser.runtime_errors[error_info["module_name"]] = error_info

            # Check if we should show error dialog
            should_show = self._should_show_error_dialog(error_info)

            if should_show:
                self._auto_disable_extension(error_info)
                QTimer.singleShot(100, lambda: self._show_error_dialog(error_info))

        sys.excepthook = global_exception_handler
        print("✓ Global exception handler installed")

    def _should_show_error_dialog(self, error_info):
        """Check if we should show error dialog (deduplication logic)"""
        module_name = error_info.get("module_name", "Unknown")
        current_time = datetime.datetime.now()

        if module_name in self._last_error_time:
            last_time = self._last_error_time[module_name]
            time_diff = (current_time - last_time).total_seconds()

            if time_diff < 5.0:
                print(f"⚠️  Suppressing duplicate error (occurred {time_diff:.1f}s ago)")
                return False

        self._last_error_time[module_name] = current_time
        return True

    def _auto_disable_extension(self, error_info):
        """Auto-disable extension that caused error to prevent spam"""
        module_name = error_info.get("module_name")

        if not module_name:
            return

        # Use case-insensitive comparison to handle capitalization differences
        module_name_lower = module_name.lower()

        for module in self.browser.modules:
            if module.__class__.__name__.lower() == module_name_lower:
                if id(module) in self._disabled_modules:
                    return

                friendly = error_info.get("friendly_name", module_name)
                print(f"🛑 Auto-disabling {friendly} due to error")
                self._disabled_modules.add(id(module))

                # REMOVE items completely, don't just hide
                if hasattr(module, "disable"):
                    try:
                        module.disable()
                    except:
                        pass
                elif hasattr(module, "_tracked_actions"):
                    # Remove tracked actions completely from toolbar
                    for action in module._tracked_actions[:]:
                        try:
                            # Get widget if it exists
                            widget = self.browser.navbar.widgetForAction(action)
                            if widget:
                                # Clear menu if it's a button with menu
                                if hasattr(widget, "menu") and widget.menu():
                                    widget.menu().clear()
                                    widget.menu().deleteLater()
                                # Remove widget
                                widget.setParent(None)
                                widget.deleteLater()

                            # Remove action from toolbar
                            self.browser.navbar.removeAction(action)
                        except Exception as e:
                            print(f"   ⚠️ Error removing action: {e}")

                    # Clear the tracked actions list
                    module._tracked_actions.clear()

                self.browser.show_status(f"⚠️ {friendly} disabled due to error", 5000)
                break

    def _show_error_dialog(self, error_info):
        """Show user-friendly error dialog with package install support"""
        try:
            # Check if this is a missing package error
            error_type = error_info.get("error_type", "")
            error_msg = error_info.get("error_message", "")

            print(f"\n🔍 EXCEPTION HANDLER - ERROR DIALOG:")
            print(f"   Error Type: {error_type}")
            print(f"   Error Message: {error_msg}")

            is_import_error = error_type in ["ModuleNotFoundError", "ImportError"]
            print(f"   Is Import Error: {is_import_error}")

            missing_package = None
            if is_import_error:
                missing_package = extract_missing_package(error_msg)
                print(f"   Missing Package: {missing_package}")
            else:
                print(f"   Not an import error, skipping package extraction")

            msg = ClosableMessageBox(self.browser)
            msg.setWindowTitle("Extension Error")
            msg.setIcon(QMessageBox.Icon.Warning)

            # Use friendly name for display
            friendly = error_info.get("friendly_name", "An extension")

            # Check for system library errors
            is_system_lib_error = any(
                keyword in error_msg.lower()
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
                system_lib_name = extract_system_lib_name(error_msg)
                install_cmds = get_system_lib_commands(system_lib_name)
                error_text = (
                    f"<b>{friendly}</b> requires system libraries.\n\n"
                    f"Pip cannot install these. Please install manually:\n\n"
                    f"{install_cmds}\n\n"
                    f"Then restart KaiBrowser."
                )
            elif missing_package:
                print(f"   ✅ SHOWING INSTALL PACKAGE DIALOG")
                user_message = (
                    f"This extension requires the <b>{missing_package}</b> package."
                )
                error_text = (
                    f"<b>{friendly}</b> is missing a required package.\n\n"
                    f"{user_message}\n\n"
                    f"Would you like to install it now?"
                )
            else:
                print(f"   ✅ SHOWING FIX WITH AI DIALOG")
                user_message = get_friendly_error_message(error_type, error_msg)
                error_text = (
                    f"<b>{friendly}</b> encountered a problem and has been disabled.\n\n"
                    f"{user_message}\n\n"
                    f"You can re-enable it from the Extensions menu (🧩) or "
                    f"use the AI builder to fix it."
                )

            msg.setText(error_text)

            # Technical details in "Show Details"
            msg.setDetailedText(
                f"Technical Details:\n"
                f"Error: {error_info['error_type']}\n"
                f"Message: {error_info['error_message']}\n\n"
                f"Traceback:\n{error_info['traceback']}"
            )

            has_builder = any(
                m.__class__.__name__ == "ExtensionBuilderModule"
                for m in self.browser.modules
            )

            # Add appropriate action button
            install_btn = None
            send_to_ai_btn = None

            if is_system_lib_error:
                # No action button for system libs - just show instructions
                print(f"   ℹ️ SYSTEM LIBRARY ERROR - NO ACTION BUTTON")
            elif missing_package:
                # Show "Install Package" button for import errors
                print(f"   ✅ ADDING INSTALL BUTTON")
                install_btn = msg.addButton(
                    "📦 Install Package", QMessageBox.ButtonRole.ActionRole
                )
            elif has_builder and "module_name" in error_info:
                # Show "Fix with AI" for other errors
                print(f"   ✅ ADDING FIX WITH AI BUTTON")
                send_to_ai_btn = msg.addButton(
                    "Fix with AI", QMessageBox.ButtonRole.ActionRole
                )
            else:
                print(f"   ⚠️ NO ACTION BUTTON ADDED")

            msg.addButton(QMessageBox.StandardButton.Ok)
            result = msg.exec()
            clicked_button = msg.clickedButton()

            print(
                f"   Dialog closed, clicked button: {clicked_button.text() if clicked_button else 'None'}"
            )

            # Handle button clicks
            if is_system_lib_error:
                # No action for system lib errors
                print(f"   ℹ️ System library error - user must install manually")
            elif missing_package and install_btn and clicked_button == install_btn:
                print(f"   🔄 User clicked INSTALL PACKAGE button")
                self._handle_package_install(error_info, missing_package)
            elif (
                not missing_package
                and has_builder
                and send_to_ai_btn
                and "module_name" in error_info
                and clicked_button == send_to_ai_btn
            ):
                print(f"   🔄 User clicked FIX WITH AI button")
                self._send_error_to_builder(error_info)
            else:
                print(f"   ℹ️ User clicked OK or cancelled")

        except Exception as e:
            print(f"Failed to show error dialog: {e}")
            traceback.print_exc()

    def _handle_package_install(self, error_info, package_name):
        """Install missing package and reload extension"""
        try:
            # Get dependencies directory
            dependencies_dir = getattr(
                self.browser,
                "dependencies_dir",
                Path(__file__).parent.parent / "dependencies",
            )

            # Show progress dialog
            progress = QProgressDialog(
                f"Installing {package_name}...\nThis may take a moment.",
                None,
                0,
                0,
                self.browser,
            )
            progress.setWindowTitle("Installing Package")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()

            # Process events to show dialog
            from PyQt6.QtWidgets import QApplication

            QApplication.processEvents()

            # Install package (now using consolidated function)
            success, install_error = install_package(package_name, dependencies_dir)

            # Close progress dialog
            progress.close()

            if success:
                # Installation successful
                QMessageBox.information(
                    self.browser,
                    "Package Installed",
                    f"Successfully installed {package_name}!\n\n"
                    f"The extension will be reloaded automatically.",
                )

                # Reload the extension
                self._reload_extension(error_info)

            else:
                # Installation failed - now offer AI fix
                reply = QMessageBox.warning(
                    self.browser,
                    "Installation Failed",
                    f"Could not install {package_name}:\n\n{install_error}\n\n"
                    f"Would you like to try fixing this with AI?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.Yes:
                    self._send_error_to_builder(error_info)

        except Exception as e:
            print(f"Failed to handle package install: {e}")
            traceback.print_exc()
            QMessageBox.critical(
                self.browser,
                "Installation Error",
                f"An error occurred during installation:\n\n{str(e)}",
            )

    def _reload_extension(self, error_info):
        """Reload extension after package installation"""
        try:
            module_file = error_info.get("module_file")
            module_name = error_info.get("module_name")

            if not module_file or not module_name:
                return

            print(f"🔄 Reloading {module_name}...")

            # Find and unload old module - use case-insensitive comparison
            old_module = None
            module_name_lower = module_name.lower()
            for module in self.browser.modules[:]:
                if module.__class__.__name__.lower() == module_name_lower:
                    old_module = module
                    break

            if old_module:
                # Clear disabled flag
                self.clear_disabled_flag(old_module)

                # Unload it
                from extension_loader import unload_module_safe

                unload_module_safe(self.browser, old_module)

            # Remove from sys.modules to force reimport
            module_sys_name = f"modules.{module_file}"
            if module_sys_name in sys.modules:
                del sys.modules[module_sys_name]

            # Reload the single extension
            from extension_loader import load_single_extension
            from pathlib import Path

            if getattr(sys, "frozen", False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).parent.parent

            module_path = base_dir / "modules" / f"{module_file}.py"
            dependencies_dir = getattr(
                self.browser, "dependencies_dir", base_dir / "dependencies"
            )

            loaded = []
            failed = []
            pending = []

            success = load_single_extension(
                module_path, self.browser, dependencies_dir, loaded, failed, pending
            )

            if success:
                self.browser.show_status(
                    f"✓ {error_info.get('friendly_name')} reloaded successfully", 3000
                )
                print(f"✓ Successfully reloaded {module_name}")

                # Refresh Module Manager to track the new instance
                for m in self.browser.modules:
                    if m.__class__.__name__ == "ModuleManagerModule":
                        try:
                            m.populate_menu()
                            print(f"  ✓ Module manager refreshed")
                        except:
                            pass
                        break
            else:
                self.browser.show_status(
                    f"⚠️ Failed to reload {error_info.get('friendly_name')}", 3000
                )
                print(f"✗ Failed to reload {module_name}")

        except Exception as e:
            print(f"Failed to reload extension: {e}")
            traceback.print_exc()

    def _send_error_to_builder(self, error_info):
        """Send error to Extension Builder for AI fixing"""
        try:
            extension_builder = None
            for module in self.browser.modules:
                if module.__class__.__name__ == "ExtensionBuilderModule":
                    extension_builder = module
                    break

            if not extension_builder:
                return

            source_code = None
            if "module_file" in error_info:
                try:
                    module_path = (
                        Path(__file__).parent.parent
                        / "modules"
                        / f"{error_info['module_file']}.py"
                    )
                    if module_path.exists():
                        with open(module_path, "r") as f:
                            source_code = f.read()
                except:
                    pass

            if not hasattr(self.browser, "_pending_runtime_error"):
                self.browser._pending_runtime_error = {}

            self.browser._pending_runtime_error = {
                "module_name": error_info.get("module_name", "Unknown"),
                "module_file": error_info.get("module_file", ""),
                "error_info": error_info,
                "source_code": source_code,
            }

            QTimer.singleShot(100, extension_builder.show_builder)

        except Exception as e:
            print(f"Failed to send error to Extension Builder: {e}")
            traceback.print_exc()

    def _filename_to_classname(self, filename):
        """Convert filename to likely class name"""
        parts = filename.split("_")
        return "".join(word.capitalize() for word in parts)

    def clear_disabled_flag(self, module):
        """Clear auto-disable flag when reloading a module"""
        module_id = id(module)
        if module_id in self._disabled_modules:
            self._disabled_modules.remove(module_id)
            return True
        return False
