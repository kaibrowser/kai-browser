"""
Print Page - Ctrl+P to print current page via PDF
"""

import os
import tempfile
import subprocess
import sys
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import QStandardPaths, QMarginsF
from PyQt6.QtGui import QPageLayout, QPageSize


class PrintManager:
    """Handles printing for the browser"""

    def __init__(self, browser):
        self.browser = browser
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """Set up Ctrl+P shortcut"""
        shortcut = QShortcut(QKeySequence("Ctrl+P"), self.browser)
        shortcut.activated.connect(self.print_page)

    def print_page(self):
        """Print via PDF export"""
        web_view = self.browser.get_active_web_view()
        if not web_view:
            return

        # Ask user what to do
        msg = QMessageBox(self.browser)
        msg.setWindowTitle("Print Page")
        msg.setText("How would you like to print?")

        print_btn = msg.addButton("🖨️ Print", QMessageBox.ButtonRole.AcceptRole)
        save_btn = msg.addButton("💾 Save as PDF", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

        msg.exec()

        clicked = msg.clickedButton()

        if clicked == cancel_btn:
            return
        elif clicked == save_btn:
            self._save_as_pdf(web_view)
        elif clicked == print_btn:
            self._print_via_pdf(web_view)

    def _save_as_pdf(self, web_view):
        """Save page as PDF file"""
        downloads = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        )
        title = self.browser.get_current_title() or "page"
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:50]

        path, _ = QFileDialog.getSaveFileName(
            self.browser,
            "Save as PDF",
            os.path.join(downloads, f"{safe_title}.pdf"),
            "PDF Files (*.pdf)",
        )

        if path:
            layout = QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Portrait,
                QMarginsF(10, 10, 10, 10),
            )

            def callback(data):
                if data:
                    with open(path, "wb") as f:
                        f.write(data.data())
                    self.browser.show_status(f"✓ Saved: {os.path.basename(path)}", 3000)
                else:
                    self.browser.show_status("✗ Failed to save PDF", 3000)

            web_view.page().printToPdf(callback, layout)

    def _print_via_pdf(self, web_view):
        """Print by creating temp PDF and opening with system"""
        self.browser.show_status("Preparing to print...", 2000)

        layout = QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Portrait,
            QMarginsF(10, 10, 10, 10),
        )

        def callback(data):
            if not data:
                self.browser.show_status("✗ Print failed", 3000)
                return

            try:
                # Create temp PDF
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
                    f.write(data.data())
                    temp_path = f.name

                # Open with system print
                if sys.platform == "darwin":
                    subprocess.run(["lpr", temp_path])
                elif sys.platform == "win32":
                    os.startfile(temp_path, "print")
                else:
                    # Linux - try various print commands
                    try:
                        subprocess.run(["xdg-open", temp_path])
                    except:
                        subprocess.run(["evince", temp_path])

                self.browser.show_status("✓ Sent to printer", 3000)

            except Exception as e:
                self.browser.show_status(f"✗ Print error: {e}", 3000)

        web_view.page().printToPdf(callback, layout)


def setup_print(browser):
    """Set up print functionality"""
    return PrintManager(browser)
