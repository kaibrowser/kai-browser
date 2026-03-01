"""
Extension Builder - Consolidated Error Handling
Shared error dialogs, package detection, and installation logic
Used by: extension_loader, exceptions, error_handler, code_editor_tab, manage_tab
"""

import sys
import subprocess
import re
import os
import glob
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import Qt


class ClosableMessageBox(QMessageBox):
    def closeEvent(self, event):
        """Override close event to force accept"""
        self.accept()
        event.accept()


def extract_missing_package(error_msg):
    """
    Extract package name from ModuleNotFoundError or ImportError
    Returns: package_name or None
    """
    match = re.search(r"No module named ['\"]([^'\"]+)['\"]", error_msg)
    if match:
        pkg = match.group(1)
        if "." in pkg:
            pkg = pkg.split(".")[0]
        return pkg

    match = re.search(r"cannot import name .+ from ['\"]([^'\"]+)['\"]", error_msg)
    if match:
        pkg = match.group(1)
        if "." in pkg:
            pkg = pkg.split(".")[0]
        return pkg

    return None


def find_system_python():
    """
    Dynamically find a working Python with pip on the system.
    Works across Linux distros, macOS, and Windows regardless of Python version.
    Returns: python executable string or None
    """
    candidates = []

    # 1. Use 'which'/'where' to find python in PATH dynamically
    for cmd in ["python3", "python"]:
        try:
            result = subprocess.run(
                ["which", cmd], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                candidates.append(result.stdout.strip())
        except Exception:
            pass

    # Windows fallback
    for cmd in ["python", "py"]:
        try:
            result = subprocess.run(
                ["where", cmd], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                candidates.append(result.stdout.strip().splitlines()[0])
        except Exception:
            pass

    # 2. Glob scan common bin directories for any python3.x version
    search_dirs = [
        "/usr/bin",
        "/usr/local/bin",
        "/opt/homebrew/bin",
        "/usr/local/opt/python/bin",
    ]
    for d in search_dirs:
        matches = sorted(glob.glob(os.path.join(d, "python3*")), reverse=True)
        candidates.extend(matches)
        matches = sorted(glob.glob(os.path.join(d, "python[0-9]*")), reverse=True)
        candidates.extend(matches)

    # 3. Common explicit paths as final fallback
    candidates.extend(
        [
            "/usr/bin/python3",
            "/usr/bin/python",
            "/usr/local/bin/python3",
            "/usr/local/bin/python",
            r"C:\Python313\python.exe",
            r"C:\Python312\python.exe",
            r"C:\Python311\python.exe",
            r"C:\Python310\python.exe",
            r"C:\Python39\python.exe",
        ]
    )

    # Deduplicate while preserving order
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique_candidates.append(c)

    # Test each candidate
    for candidate in unique_candidates:
        print(f"   🔍 Trying: {candidate}")
        try:
            result = subprocess.run(
                f'"{candidate}" -m pip --version',
                capture_output=True,
                text=True,
                timeout=5,
                shell=True,
            )
            if result.returncode == 0:
                print(f"   ✅ Found working Python: {candidate}")
                print(f"      pip version: {result.stdout.strip()}")
                return candidate
        except Exception as e:
            print(f"   ❌ {candidate} failed: {e}")
            continue

    return None


def install_package(package_name, dependencies_dir):
    """
    Install package to dependencies folder using pip
    Works in both source and compiled (frozen) versions
    Returns: (success: bool, error_msg: str or None)
    """
    try:
        print(f"📦 Installing {package_name} to {dependencies_dir}...")
        print(f"📍 DEBUG INFO:")
        print(f"   sys.executable = {sys.executable}")
        print(f"   sys.frozen = {getattr(sys, 'frozen', False)}")
        print(f"   dependencies_dir = {dependencies_dir}")

        package_map = {
            "cv2": "opencv-python",
            "PIL": "Pillow",
            "yaml": "PyYAML",
            "sklearn": "scikit-learn",
            "skimage": "scikit-image",
        }
        pip_package = package_map.get(package_name, package_name)
        print(f"   pip_package = {pip_package}")

        python_exe = find_system_python()

        if not python_exe:
            return False, (
                "Could not find system Python. Please ensure Python 3 is installed.\n"
                "Try: sudo apt install python3-pip (Debian/Ubuntu) or equivalent"
            )

        print(f"   🚀 Running pip install (timeout: 300s)...")
        cmd = f'"{python_exe}" -m pip install --target "{str(dependencies_dir)}" {pip_package}'
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300, shell=True
        )

        if result.returncode == 0:
            print(f"✅ Successfully installed {pip_package}")
            return True, None
        else:
            error = result.stderr or result.stdout
            print(f"❌ Installation failed: {error}")
            return False, error

    except subprocess.TimeoutExpired:
        return False, "Installation timed out (5 minutes)"
    except Exception as e:
        import traceback

        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"❌ Exception during installation: {error_detail}")
        return False, error_detail


def extract_system_lib_name(error_msg):
    """Extract system library name from error message"""
    if "libzbar" in error_msg.lower():
        return "zbar"
    elif "libgl" in error_msg.lower():
        return "opengl"
    else:
        return "unknown"


def get_system_lib_commands(lib_name):
    """Get installation commands for system libraries across distros"""
    commands = {
        "zbar": (
            "<b>Debian/Ubuntu/Mint:</b><br>"
            "<code>sudo apt install libzbar0</code><br><br>"
            "<b>Fedora/RHEL:</b><br>"
            "<code>sudo dnf install zbar</code><br><br>"
            "<b>Arch:</b><br>"
            "<code>sudo pacman -S zbar</code>"
        ),
        "opengl": (
            "<b>Debian/Ubuntu/Mint:</b><br>"
            "<code>sudo apt install libgl1-mesa-glx libglib2.0-0</code><br><br>"
            "<b>Fedora/RHEL:</b><br>"
            "<code>sudo dnf install mesa-libGL glib2</code><br><br>"
            "<b>Arch:</b><br>"
            "<code>sudo pacman -S mesa glib2</code>"
        ),
        "unknown": (
            "<b>Debian/Ubuntu/Mint:</b><br>"
            "<code>sudo apt install &lt;library-name&gt;</code><br><br>"
            "<b>Fedora/RHEL:</b><br>"
            "<code>sudo dnf install &lt;library-name&gt;</code><br><br>"
            "<b>Arch:</b><br>"
            "<code>sudo pacman -S &lt;library-name&gt;</code>"
        ),
    }
    return commands.get(lib_name, commands["unknown"])


def get_friendly_error_message(error_type, error_msg=""):
    """Convert technical errors to user-friendly messages"""
    if error_type == "AttributeError":
        return "The extension tried to use a feature that doesn't exist."
    elif error_type == "TypeError":
        return "The extension received unexpected data."
    elif error_type == "KeyError":
        return "The extension couldn't find something it needed."
    elif error_type == "IndexError":
        return "The extension tried to access data that doesn't exist."
    elif error_type == "ValueError":
        return "The extension received an invalid value."
    elif error_type == "ImportError" or error_type == "ModuleNotFoundError":
        return "The extension requires a component that isn't installed."
    elif error_type == "NameError":
        return "The extension has a coding error (undefined variable)."
    elif error_type == "ZeroDivisionError":
        return "The extension tried to divide by zero."
    elif error_type == "FileNotFoundError":
        return "The extension couldn't find a required file."
    elif error_type == "SyntaxError":
        return "The extension has a syntax error in the code."
    elif error_type == "IndentationError":
        return "The extension has incorrect indentation."
    else:
        return "Something unexpected went wrong."


def show_error_dialog_with_actions(
    parent_widget,
    extension_name,
    error_info,
    dependencies_dir,
    on_install_success=None,
    on_fix_with_ai=None,
    dialog_title="Extension Error",
):
    """
    Show comprehensive error dialog with Install Package or Fix with AI buttons
    """
    print(f"\n🔍 ERROR DIALOG:")
    print(f"   Extension: {extension_name}")
    print(f"   Error Type: {error_info.get('type', 'Unknown')}")
    print(f"   Error Message: {error_info.get('message', '')[:200]}")

    error_type = error_info.get("type", "")
    error_msg = error_info.get("message", "")
    full_error = error_info.get("traceback", "") + "\n" + error_msg

    is_import_error = error_type in ["ModuleNotFoundError", "ImportError"]
    print(f"   Is Import Error: {is_import_error}")

    missing_package = None
    if is_import_error:
        missing_package = extract_missing_package(full_error)
        print(f"   Missing Package: {missing_package}")

    is_system_lib_error = any(
        keyword in full_error.lower()
        for keyword in [
            "shared library",
            "libzbar",
            "libgl",
            "cannot open shared object",
        ]
    )

    msg = ClosableMessageBox(parent_widget)
    msg.setWindowTitle(dialog_title)
    msg.setIcon(QMessageBox.Icon.Warning)

    if is_system_lib_error:
        print(f"   ✅ SHOWING SYSTEM LIBRARY INSTRUCTIONS")
        system_lib_name = extract_system_lib_name(full_error)
        install_cmds = get_system_lib_commands(system_lib_name)
        msg.setText(
            f"<b>{extension_name} failed to load</b>\n\n"
            f"This extension requires system libraries.\n\n"
            f"Pip cannot install these. Please install manually:\n\n"
            f"{install_cmds}\n\n"
            f"Then restart KaiBrowser."
        )
    elif missing_package:
        print(f"   ✅ SHOWING INSTALL PACKAGE DIALOG")
        msg.setText(
            f"<b>{extension_name} failed to load</b>\n\n"
            f"This extension requires the <b>{missing_package}</b> package.\n\n"
            f"Would you like to install it now?"
        )
    else:
        print(f"   ✅ SHOWING FIX WITH AI DIALOG")
        friendly_message = get_friendly_error_message(error_type, error_msg)
        msg.setText(
            f"<b>{extension_name} failed to load</b>\n\n"
            f"{friendly_message}\n\n"
            "You can fix this manually or let AI help."
        )

    msg.setDetailedText(f"Technical Details:\n{full_error}")

    install_btn = None
    fix_with_ai_btn = None

    if is_system_lib_error:
        print(f"   ℹ️ SYSTEM LIBRARY ERROR - NO ACTION BUTTON")
    elif missing_package:
        install_btn = msg.addButton(
            "📦 Install Package", QMessageBox.ButtonRole.ActionRole
        )
    elif on_fix_with_ai:
        fix_with_ai_btn = msg.addButton(
            "Fix with AI", QMessageBox.ButtonRole.ActionRole
        )

    msg.addButton(QMessageBox.StandardButton.Ok)
    msg.exec()

    clicked = msg.clickedButton()
    print(f"   User clicked: {clicked.text() if clicked else 'None'}")

    if is_system_lib_error:
        return "cancelled"

    elif missing_package and clicked == install_btn:
        print(f"   🔄 Starting package installation")

        progress = QProgressDialog(
            f"Installing {missing_package}...\nThis may take a moment.",
            None,
            0,
            0,
            parent_widget,
        )
        progress.setWindowTitle("Installing Package")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        from PyQt6.QtWidgets import QApplication

        QApplication.processEvents()

        success, install_error = install_package(missing_package, dependencies_dir)
        progress.close()

        if success:
            print(f"   ✅ Installation successful")
            # Invalidate cached failed import so Python will retry cleanly
            for key in list(sys.modules.keys()):
                if key == missing_package or key.startswith(missing_package + "."):
                    print(f"   🗑 Removing cached module: {key}")
                    del sys.modules[key]
            # Ensure dependencies dir is still in sys.path
            deps_str = str(dependencies_dir)
            if deps_str not in sys.path:
                sys.path.insert(0, deps_str)
            QMessageBox.information(
                parent_widget,
                "Package Installed",
                f"Successfully installed {missing_package}!\n\n"
                f"The extension will be reloaded now.",
            )
            if on_install_success:
                on_install_success()
            return "installed"
        else:
            print(f"   ❌ Installation failed: {install_error}")
            reply = QMessageBox.warning(
                parent_widget,
                "Installation Failed",
                f"Could not install {missing_package}:\n\n{install_error}\n\n"
                f"Would you like to try fixing this with AI?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes and on_fix_with_ai:
                error_details = (
                    f"Failed to install package {missing_package}: {install_error}"
                )
                on_fix_with_ai(error_details, None)
                return "fixed_with_ai"
            return "cancelled"

    elif not missing_package and clicked == fix_with_ai_btn and on_fix_with_ai:
        print(f"   🔄 Sending to AI for fix")
        on_fix_with_ai(full_error, None)
        return "fixed_with_ai"

    else:
        print(f"   ℹ️ User clicked OK or cancelled")
        return "cancelled"
