"""
Extension Loader - Now Supports Natural AI Pattern + Auto-Install Missing Packages
Tries natural pattern first (pass browser), falls back to old pattern
FIXED: Proper unload support for natural plugins
NEW: Auto-detects and offers to install missing packages at load-time
CONSOLIDATED: Uses shared error_dialogs module
"""

import importlib.util
import inspect
import sys
from pathlib import Path
from kai_base import KaiModule
from PyQt6.QtWidgets import (
    QMessageBox,
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer

# Import from consolidated error_dialogs module
from extension_builder.error_dialogs import extract_missing_package, install_package


def show_install_dialog(package_name, extension_name):
    """
    Show dialog asking user if they want to install missing package
    Returns: True if user clicked Install, False otherwise
    """
    dialog = QDialog()
    dialog.setWindowTitle("Missing Package")
    dialog.setModal(True)
    dialog.setMinimumWidth(400)

    layout = QVBoxLayout()

    # Message
    msg = QLabel(
        f"<b>{extension_name}</b> requires the package <b>{package_name}</b><br><br>"
        f"Would you like to install it now?"
    )
    msg.setWordWrap(True)
    layout.addWidget(msg)

    # Buttons
    btn_layout = QVBoxLayout()

    install_btn = QPushButton("📦 Install Package")
    install_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
    install_btn.clicked.connect(lambda: dialog.done(1))
    btn_layout.addWidget(install_btn)

    cancel_btn = QPushButton("Cancel")
    cancel_btn.clicked.connect(lambda: dialog.done(0))
    btn_layout.addWidget(cancel_btn)

    layout.addLayout(btn_layout)
    dialog.setLayout(layout)

    result = dialog.exec()
    return result == 1


def show_install_progress(package_name):
    """
    Show progress dialog during installation
    Returns: dialog object (caller should close it)
    """
    dialog = QDialog()
    dialog.setWindowTitle("Installing Package")
    dialog.setModal(True)
    dialog.setMinimumWidth(350)

    layout = QVBoxLayout()

    label = QLabel(f"Installing <b>{package_name}</b>...<br>This may take a moment.")
    label.setWordWrap(True)
    layout.addWidget(label)

    progress = QProgressBar()
    progress.setRange(0, 0)  # Indeterminate
    layout.addWidget(progress)

    dialog.setLayout(layout)
    dialog.show()

    return dialog


def load_all_modules(browser_core):
    """
    Auto-discover and load all modules
    Supports both natural AI pattern and legacy KaiModule pattern
    NOW: Auto-installs missing packages when detected
    """
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent

    modules_dir = base_dir / "modules"

    if not modules_dir.exists():
        print(f"⚠️  modules/ folder not found at: {modules_dir}")
        return []

    # Get dependencies directory from browser
    dependencies_dir = getattr(
        browser_core, "dependencies_dir", base_dir / "dependencies"
    )

    print(f"🔍 Auto-discovering modules from: {modules_dir}\n")

    loaded = []
    failed = []
    pending_install = []  # Extensions waiting for package install

    py_files = sorted(modules_dir.glob("*.py"))

    for py_file in py_files:
        if py_file.stem.startswith("_"):
            continue

        success = load_single_extension(
            py_file, browser_core, dependencies_dir, loaded, failed, pending_install
        )

    # Load system modules (legacy pattern)
    print("\n🔧 Loading System Modules...")

    try:
        from kai_manager import ModuleManagerModule

        extension = ModuleManagerModule()
        browser_core.load_module(extension)
        loaded.append(extension)
        print(f"   ✓ 🔧 ModuleManagerModule (system)")
    except Exception as e:
        print(f"   ✗ kai_manager: {e}")
        failed.append(("kai_manager", str(e)))

    try:
        from extension_builder import ExtensionBuilderModule

        extension = ExtensionBuilderModule()
        browser_core.load_module(extension)
        loaded.append(extension)
        print(f"   ✓ 🔧 ExtensionBuilderModule (system)")
    except Exception as e:
        print(f"   ✗ extension_builder: {e}")
        failed.append(("extension_builder", str(e)))

    print(f"\n✅ Loaded {len(loaded)} modules")
    if failed:
        print(f"⚠️  Failed to load {len(failed)} modules")
    if pending_install:
        print(f"⏳ {len(pending_install)} modules waiting for packages")
    print()

    # Refresh Module Manager
    for module in loaded:
        if module.__class__.__name__ == "ModuleManagerModule":
            try:
                module.populate_menu()
            except:
                pass
            break

    return loaded


def load_single_extension(
    py_file, browser_core, dependencies_dir, loaded, failed, pending_install
):
    """
    Load a single extension file with auto-install support
    Returns: True if loaded successfully
    """
    try:
        # Load module from file
        spec = importlib.util.spec_from_file_location(
            f"modules.{py_file.stem}", py_file
        )
        if not spec or not spec.loader:
            raise Exception("Could not load module spec")

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        # Find the plugin/module class
        extension_class = None
        candidates = []

        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Skip private classes
            if name.startswith("_"):
                continue

            # Skip classes defined in other modules (like QDialog, QWidget, etc.)
            if obj.__module__ != module.__name__:
                continue

            # Skip obvious helper classes (Dialog, Window, Widget in name)
            if any(
                suffix in name for suffix in ["Dialog", "Window", "Widget", "Helper"]
            ):
                continue

            # Accept if:
            # 1. It's a KaiModule subclass (legacy pattern)
            # 2. OR it has an activate() method (natural pattern)
            # 3. OR it has __init__ that takes browser parameter (natural pattern)

            is_kai_module = False
            try:
                is_kai_module = issubclass(obj, KaiModule) and obj != KaiModule
            except:
                pass

            has_activate = "activate" in dir(obj)

            # Check if __init__ expects browser parameter
            has_browser_param = False
            try:
                sig = inspect.signature(obj.__init__)
                params = [p.name for p in sig.parameters.values() if p.name != "self"]
                has_browser_param = "browser" in params
            except:
                pass

            if is_kai_module or has_activate or has_browser_param:
                candidates.append((name, obj))

        # Pick the best candidate
        # Prefer: Module > Plugin > anything else with activate()
        if candidates:
            # Sort by preference
            for name, obj in candidates:
                if "Module" in name:
                    extension_class = obj
                    break
                elif "Plugin" in name:
                    extension_class = obj
                    break

            # If no Module or Plugin in name, take first one
            if not extension_class:
                extension_class = candidates[0][1]

        if not extension_class:
            raise Exception("No plugin/module class found")

        # Try to instantiate - natural pattern first
        extension = None

        # Check what __init__ expects
        sig = inspect.signature(extension_class.__init__)
        params = [p for p in sig.parameters.values() if p.name != "self"]

        if len(params) > 0:
            # Natural AI pattern - expects browser in __init__
            try:
                extension = extension_class(browser_core)
                print(f"   ✓ Natural pattern: {extension_class.__name__}")
            except Exception as e:
                print(
                    f"   ⚠️ Failed natural pattern for {extension_class.__name__}: {e}"
                )
        else:
            # Legacy pattern - no args
            try:
                extension = extension_class()
                print(f"   ✓ Legacy pattern: {extension_class.__name__}")
            except Exception as e:
                print(f"   ⚠️ Failed to instantiate {extension_class.__name__}: {e}")

        if not extension:
            raise Exception("Could not instantiate extension")

        # Load into browser
        browser_core.load_module(extension)
        loaded.append(extension)

        # Status indicator
        if hasattr(extension, "enabled"):
            status = "✓" if extension.enabled else "✗"
            module_type = (
                "📱"
                if hasattr(extension, "module_type")
                and extension.module_type == KaiModule.MODULE_TYPE_UI
                else "⚙️"
            )
            print(f"   {status} {module_type} {extension_class.__name__}")
        else:
            # Natural pattern - always enabled
            print(f"   ✓ 📱 {extension_class.__name__}")

        return True

    except (ModuleNotFoundError, ImportError) as e:
        # Missing package detected!
        error_msg = str(e)
        package_name = extract_missing_package(error_msg)

        if package_name:
            print(f"   📦 Missing package: {package_name}")

            # Ask user if they want to install
            if show_install_dialog(package_name, py_file.stem):
                # Show progress dialog
                progress_dialog = show_install_progress(package_name)

                # Install package (now using consolidated function)
                success, install_error = install_package(package_name, dependencies_dir)

                # Close progress dialog
                progress_dialog.close()

                if success:
                    # Installation successful - retry loading
                    print(f"   🔄 Retrying {py_file.stem}...")

                    # Reload sys.modules to pick up new package
                    if f"modules.{py_file.stem}" in sys.modules:
                        del sys.modules[f"modules.{py_file.stem}"]

                    # Try loading again
                    return load_single_extension(
                        py_file,
                        browser_core,
                        dependencies_dir,
                        loaded,
                        failed,
                        pending_install,
                    )
                else:
                    # Installation failed
                    error_msg = f"Failed to install {package_name}: {install_error}"
                    print(f"   ✗ {error_msg}")
                    failed.append((py_file.stem, error_msg))

                    QMessageBox.warning(
                        None,
                        "Installation Failed",
                        f"Could not install {package_name}:\n\n{install_error}",
                    )
                    return False
            else:
                # User canceled
                print(f"   ⏭️  Skipped installation")
                pending_install.append((py_file.stem, package_name))
                failed.append((py_file.stem, f"Missing package: {package_name}"))
                return False
        else:
            # Could not extract package name
            print(f"   ✗ {py_file.stem}: {error_msg}")
            failed.append((py_file.stem, error_msg))
            return False

    except Exception as e:
        print(f"   ✗ {py_file.stem}: {e}")
        failed.append((py_file.stem, str(e)))
        return False


def unload_module_safe(browser_core, module):
    """
    Safely unload a module - handles both natural and legacy patterns
    """
    try:
        module_name = module.__class__.__name__

        # Check if it's a natural plugin (no 'enabled' attribute)
        is_natural = not hasattr(module, "enabled")

        if is_natural:
            # Natural plugin - call deactivate if available
            if hasattr(module, "deactivate"):
                try:
                    module.deactivate()
                except Exception as e:
                    print(f"⚠️ Deactivate error: {e}")

            # Remove from modules list
            if module in browser_core.modules:
                browser_core.modules.remove(module)

            print(f"✓ Unloaded natural plugin: {module_name}")
        else:
            # Legacy module - use existing disable logic
            if module.enabled:
                module.disable()

            # Remove UI elements
            for action in module.ui_actions[:]:
                browser_core.navbar.removeAction(action)
            module.ui_actions.clear()

            for widget in module.ui_elements[:]:
                widget.setParent(None)
                widget.deleteLater()
            module.ui_elements.clear()

            # Disconnect signals
            for signal, slot in module.signal_connections[:]:
                try:
                    signal.disconnect(slot)
                except:
                    pass
            module.signal_connections.clear()

            # Remove from modules list
            if module in browser_core.modules:
                browser_core.modules.remove(module)

            print(f"✓ Unloaded legacy module: {module_name}")

        return True

    except Exception as e:
        print(f"✗ Failed to unload: {e}")
        return False
