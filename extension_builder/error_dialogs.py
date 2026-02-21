"""
Extension Builder - Consolidated Error Handling
Shared error dialogs, package detection, and installation logic
Used by: extension_loader, exceptions, error_handler, code_editor_tab, manage_tab
"""

import sys
import subprocess
import re
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
    # Pattern 1: "No module named 'package'"
    match = re.search(r"No module named ['\"]([^'\"]+)['\"]", error_msg)
    if match:
        pkg = match.group(1)
        # Handle submodules (e.g., "cv2.something" -> "cv2")
        if "." in pkg:
            pkg = pkg.split(".")[0]
        return pkg

    # Pattern 2: "cannot import name 'X' from 'package'"
    match = re.search(r"cannot import name .+ from ['\"]([^'\"]+)['\"]", error_msg)
    if match:
        pkg = match.group(1)
        if "." in pkg:
            pkg = pkg.split(".")[0]
        return pkg

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

        # Map common import names to pip package names
        package_map = {
            "cv2": "opencv-python",
            "PIL": "Pillow",
            "yaml": "PyYAML",
            "sklearn": "scikit-learn",
            "skimage": "scikit-image",
        }
        pip_package = package_map.get(package_name, package_name)
        print(f"   pip_package = {pip_package}")

        # Always search for a working Python with pip
        print(f"   🔍 Finding Python...")
        python_candidates = [
            "py",
            "python",
            "python3",
            r"C:\Python312\python.exe",
            r"C:\Python311\python.exe",
            r"C:\Python310\python.exe",
            "/usr/bin/python3",
            "/usr/bin/python",
        ]

        python_exe = None
        for candidate in python_candidates:
            print(f"   🔍 Trying candidate: {candidate}")
            try:
                cmd = f'"{candidate}" -m pip --version'
                test_result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=5, shell=True
                )
                if test_result.returncode == 0:
                    python_exe = candidate
                    print(f"   ✅ Found working Python: {python_exe}")
                    print(f"      pip version: {test_result.stdout.strip()}")
                    break
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                print(f"   ❌ {candidate} failed: {e}")
                continue

        if not python_exe:
            return False, (
                "Could not find system Python. Please ensure Python 3 is installed.\n"
                "Try: sudo apt install python3-pip (Debian/Ubuntu) or equivalent"
            )

        # Run pip install with increased timeout for large packages
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

    Args:
        parent_widget: Parent QWidget for the dialog
        extension_name: Name of the extension that failed
        error_info: Dict with 'type', 'message', 'traceback'
        dependencies_dir: Path to dependencies folder
        on_install_success: Callback() to run after successful package install
        on_fix_with_ai: Callback(error_details, code) to send to AI for fixing
        dialog_title: Window title for the dialog

    Returns:
        action_taken: "installed", "fixed_with_ai", "cancelled"
    """
    print(f"\n🔍 ERROR DIALOG:")
    print(f"   Extension: {extension_name}")
    print(f"   Error Type: {error_info.get('type', 'Unknown')}")
    print(f"   Error Message: {error_info.get('message', '')[:200]}")

    # Extract error details
    error_type = error_info.get("type", "")
    error_msg = error_info.get("message", "")
    full_error = error_info.get("traceback", "") + "\n" + error_msg

    # Check if this is an import error
    is_import_error = error_type in ["ModuleNotFoundError", "ImportError"]
    print(f"   Is Import Error: {is_import_error}")

    missing_package = None
    if is_import_error:
        missing_package = extract_missing_package(full_error)
        print(f"   Missing Package: {missing_package}")

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

    # Create message box
    msg = ClosableMessageBox(parent_widget)
    msg.setWindowTitle(dialog_title)
    msg.setIcon(QMessageBox.Icon.Warning)

    # Build message based on error type
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

    # Technical details
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
    elif on_fix_with_ai:
        fix_with_ai_btn = msg.addButton(
            "Fix with AI", QMessageBox.ButtonRole.ActionRole
        )

    msg.addButton(QMessageBox.StandardButton.Ok)
    msg.exec()

    clicked = msg.clickedButton()
    print(f"   User clicked: {clicked.text() if clicked else 'None'}")

    # Handle button clicks
    if is_system_lib_error:
        print(f"   ℹ️ System library error - user must install manually")
        return "cancelled"

    elif missing_package and clicked == install_btn:
        print(f"   🔄 Starting package installation")

        # Show progress dialog
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

        # Process events to show dialog
        from PyQt6.QtWidgets import QApplication

        QApplication.processEvents()

        # Install package
        success, install_error = install_package(missing_package, dependencies_dir)

        # Close progress
        progress.close()

        if success:
            print(f"   ✅ Installation successful")
            QMessageBox.information(
                parent_widget,
                "Package Installed",
                f"Successfully installed {missing_package}!\n\n"
                f"The extension will be reloaded now.",
            )

            # Call success callback
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
