"""
Auto-updater - Check GitHub for new releases
"""

import requests
from PyQt6.QtCore import QThread, pyqtSignal, QUrl
from PyQt6.QtWidgets import QMessageBox, QPushButton

VERSION = "1.0.5"
GITHUB_API = "https://api.github.com/repos/kaibrowser/kai-browser/releases/latest"
DOWNLOAD_URL = "https://kaibrowser.com"


def parse_version(version_str):
    """Parse version string to tuple for comparison"""
    # Remove 'v' prefix if present
    v = version_str.lower().strip().lstrip("v")
    try:
        parts = [int(x) for x in v.split(".")]
        # Pad to 3 parts
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts)
    except:
        return (0, 0, 0)


def is_newer_version(latest, current):
    """Check if latest version is newer than current"""
    return parse_version(latest) > parse_version(current)


class UpdateChecker(QThread):
    """Background thread to check for updates"""

    update_available = pyqtSignal(str, str)  # new_version, release_url
    no_update = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, current_version=VERSION):
        super().__init__()
        self.current_version = current_version

    def run(self):
        try:
            response = requests.get(GITHUB_API, timeout=10)

            if response.status_code != 200:
                self.error.emit(f"GitHub API error: {response.status_code}")
                return

            data = response.json()
            latest_version = data.get("tag_name", "")
            release_url = data.get("html_url", DOWNLOAD_URL)

            if is_newer_version(latest_version, self.current_version):
                self.update_available.emit(latest_version, release_url)
            else:
                self.no_update.emit()

        except requests.exceptions.Timeout:
            self.error.emit("Update check timed out")
        except requests.exceptions.ConnectionError:
            self.error.emit("Could not connect to GitHub")
        except Exception as e:
            self.error.emit(str(e))


def check_for_updates(browser, silent=True):
    """
    Check for updates in background

    Args:
        browser: KaiBrowser instance
        silent: If True, only notify if update available. If False, show "up to date" too.
    """
    checker = UpdateChecker()

    # Store reference to prevent garbage collection
    browser._update_checker = checker

    def on_update_available(new_version, release_url):
        msg = QMessageBox(browser)
        msg.setWindowTitle("Update Available")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(
            f"<b>Kai {new_version} is available!</b><br><br>"
            f"You're currently on version {VERSION}.<br><br>"
            f"Visit kaibrowser.com to download the latest version."
        )

        download_btn = msg.addButton("Download", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Later", QMessageBox.ButtonRole.RejectRole)

        msg.exec()

        if msg.clickedButton() == download_btn:
            browser.browser.setUrl(QUrl(DOWNLOAD_URL))

    def on_no_update():
        if not silent:
            QMessageBox.information(
                browser, "Up to Date", f"You're running the latest version ({VERSION})."
            )

    def on_error(error_msg):
        print(f"Update check failed: {error_msg}")
        if not silent:
            QMessageBox.warning(
                browser,
                "Update Check Failed",
                f"Could not check for updates:\n{error_msg}",
            )

    checker.update_available.connect(on_update_available)
    checker.no_update.connect(on_no_update)
    checker.error.connect(on_error)

    checker.start()


def get_current_version():
    """Return current version string"""
    return VERSION
