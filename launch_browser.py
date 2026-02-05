#!/usr/bin/env python3
"""
Kai Browser Launcher with Auto-Discovery
Simply drop modules into modules/ folder and they load automatically!
"""
import sys
import os
from pathlib import Path

# Add graphics workaround flags
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-gpu --no-sandbox --disable-dev-shm-usage"
)


# =============================================================
# Setup dependencies folder BEFORE any other imports
# =============================================================
def setup_dependencies_path():
    """
    Create dependencies and modules folders and add to sys.path
    This allows pip-installed packages and modules to be imported
    """
    # Get app directory (works for both dev and compiled)
    if getattr(sys, "frozen", False):
        # Compiled app
        app_dir = Path(sys.executable).parent
    else:
        # Development
        app_dir = Path(__file__).parent

    # Create dependencies folder
    deps_dir = app_dir / "dependencies"
    deps_dir.mkdir(exist_ok=True)

    # Create modules folder
    modules_dir = app_dir / "modules"
    modules_dir.mkdir(exist_ok=True)

    # Add to Python path (at front so it takes priority)
    deps_str = str(deps_dir)
    if deps_str not in sys.path:
        sys.path.insert(0, deps_str)

    modules_str = str(modules_dir)
    if modules_str not in sys.path:
        sys.path.insert(0, modules_str)

    return deps_dir, modules_dir


# Setup paths FIRST
DEPENDENCIES_DIR, MODULES_DIR = setup_dependencies_path()

# =============================================================
# Now safe to import everything else
# =============================================================
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QUrl
from kai_core import KaiBrowser
from extension_loader import load_all_modules


def show_first_run_warning(browser):
    """Show safety warning on first run"""
    # Check if user has seen this before
    if browser.preferences.get_module_setting("Browser", "first_run_complete", False):
        return  # Already seen it

    msg = QMessageBox(browser)
    msg.setWindowTitle("Welcome to KaiBrowser™")
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setText(
        """
    <h3>Welcome to KaiBrowser™!</h3>
    
    <p>KaiBrowser is an experimental browser with AI-powered 
    extension creation.</p>
    
    <p><b>Important Safety Information:</b></p>
    <ul>
    <li><b>Beta Software:</b> Provided "as is" with no warranty</li>
    <li><b>Extensions:</b> AI-generated and user-created extensions have full browser access</li>
    <li><b>Review Code:</b> Always review extension code before installing</li>
    <li><b>AI Can Err:</b> AI-generated code may contain mistakes or security issues</li>
    <li><b>User Risk:</b> You install and run extensions at your own risk</li>
    <li><b>Open Source:</b> Licensed under GPL v3</li>
    </ul>
    
    <p><b>Extensions can access:</b> Web pages, browsing data, local files</p>
    
    <p><b>By using KaiBrowser, you accept these terms and risks.</b></p>
    
    <p>See LICENSE file for full terms.</p>
    """
    )
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()

    # Mark as shown
    browser.preferences.set_module_setting("Browser", "first_run_complete", True)


def main():
    app = QApplication(sys.argv)

    # Set application icon for taskbar
    if getattr(sys, "frozen", False):
        # Compiled app - icon is bundled
        icon_path = os.path.join(sys._MEIPASS, "kai-browser_logo.png")
    else:
        # Development - icon is in project folder
        icon_path = str(Path(__file__).parent / "kai-browser_logo.png")

    if os.path.exists(icon_path):
        from PyQt6.QtGui import QIcon

        app.setWindowIcon(QIcon(icon_path))

    print("=" * 60)
    print("🔥 Kai Browser")
    print("=" * 60)
    print(f"📦 Dependencies folder: {DEPENDENCIES_DIR}")
    print(f"📂 Modules folder: {MODULES_DIR}")

    # Create the core browser
    browser = KaiBrowser()

    # Store paths on browser for access by extensions
    browser.dependencies_dir = DEPENDENCIES_DIR
    browser.modules_dir = MODULES_DIR

    # ⚠️ SHOW FIRST-RUN WARNING (if first time)
    show_first_run_warning(browser)

    # Auto-discover and load ALL modules from modules/ folder
    # Just drop .py files into modules/ and they'll load automatically!
    modules = load_all_modules(browser)

    print("=" * 60)

    # Check if a URL was passed as an argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"📍 Opening URL from shortcut: {url}")
        browser.browser.setUrl(QUrl(url))
    else:
        print("🌐 Loading default page")

    browser.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
