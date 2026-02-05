"""
About Dialog - Version info and credits
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from updater import VERSION


class AboutDialog(QDialog):
    """Simple about dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Kai")
        self.setFixedSize(320, 280)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Logo/Title
        title = QLabel("🌐 Kai Browser")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Version
        version = QLabel(f"Version {VERSION}")
        version.setStyleSheet("font-size: 13px; color: #666;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(8)

        # Description
        desc = QLabel("Generate extensions from plain English.")
        desc.setStyleSheet("font-size: 12px; color: #444;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(8)

        # Credits
        credits = QLabel(
            "Built because I was too lazy to learn PyQt6.\nNow nobody else has to either."
        )
        credits.setStyleSheet("font-size: 11px; color: #888; font-style: italic;")
        credits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(credits)

        layout.addStretch()

        # Website link
        website = QLabel(
            '<a href="https://kaibrowser.com" style="color: #7c3aed;">kaibrowser.com</a>'
        )
        website.setOpenExternalLinks(True)
        website.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(website)

        layout.addSpacing(8)

        # Close button
        close_btn = QPushButton("OK")
        close_btn.setFixedWidth(80)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background: #7c3aed;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #6d28d9;
            }
        """
        )
        close_btn.clicked.connect(self.accept)

        btn_layout = QVBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)


def show_about_dialog(parent):
    """Show the about dialog"""
    dialog = AboutDialog(parent)
    dialog.exec()
