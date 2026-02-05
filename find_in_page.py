"""
Find in Page - Ctrl+F search bar for finding text on the current page
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtWebEngineCore import QWebEnginePage


class FindBar(QWidget):
    """Find in page bar - appears below navbar"""

    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.current_match = 0
        self.total_matches = 0

        self.setFixedHeight(40)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #f3f4f6;
                border-bottom: 1px solid #e5e7eb;
            }
        """
        )
        self.setup_ui()
        self.setup_shortcuts()
        self.hide()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find in page...")
        self.search_input.setFixedWidth(250)
        self.search_input.setStyleSheet(
            """
            QLineEdit {
                padding: 6px 10px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background: white;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #7c3aed;
            }
        """
        )
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_input.returnPressed.connect(self.find_next)
        layout.addWidget(self.search_input)

        # Match counter
        self.match_label = QLabel("")
        self.match_label.setStyleSheet(
            "color: #6b7280; font-size: 12px; min-width: 80px;"
        )
        layout.addWidget(self.match_label)

        # Previous button
        prev_btn = QPushButton("▲")
        prev_btn.setFixedSize(28, 28)
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.setToolTip("Previous match (Shift+Enter)")
        prev_btn.setStyleSheet(self._button_style())
        prev_btn.clicked.connect(self.find_previous)
        layout.addWidget(prev_btn)

        # Next button
        next_btn = QPushButton("▼")
        next_btn.setFixedSize(28, 28)
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.setToolTip("Next match (Enter)")
        next_btn.setStyleSheet(self._button_style())
        next_btn.clicked.connect(self.find_next)
        layout.addWidget(next_btn)

        layout.addStretch()

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("Close (Escape)")
        close_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                font-size: 14px;
                color: #6b7280;
            }
            QPushButton:hover {
                color: #1f2937;
                background: #e5e7eb;
                border-radius: 4px;
            }
        """
        )
        close_btn.clicked.connect(self.close_find)
        layout.addWidget(close_btn)

    def _button_style(self):
        return """
            QPushButton {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                font-size: 10px;
                color: #374151;
            }
            QPushButton:hover {
                background: #e5e7eb;
            }
            QPushButton:pressed {
                background: #d1d5db;
            }
        """

    def setup_shortcuts(self):
        # Ctrl+F to open
        find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self.browser)
        find_shortcut.activated.connect(self.open_find)

        # Escape to close
        esc_shortcut = QShortcut(QKeySequence("Escape"), self)
        esc_shortcut.activated.connect(self.close_find)

        # Shift+Enter for previous
        shift_enter = QShortcut(QKeySequence("Shift+Return"), self)
        shift_enter.activated.connect(self.find_previous)

    def open_find(self):
        """Show the find bar and focus input"""
        self.show()
        self.search_input.setFocus()
        self.search_input.selectAll()

    def close_find(self):
        """Hide find bar and clear highlights"""
        self.hide()
        self.search_input.clear()
        self.match_label.setText("")
        self._clear_highlights()

    def on_search_changed(self, text):
        """Search as user types"""
        if not text:
            self.match_label.setText("")
            self._clear_highlights()
            return
        self._find_text(text, QWebEnginePage.FindFlag(0))

    def find_next(self):
        """Find next match"""
        text = self.search_input.text()
        if text:
            self._find_text(text, QWebEnginePage.FindFlag(0))

    def find_previous(self):
        """Find previous match"""
        text = self.search_input.text()
        if text:
            self._find_text(text, QWebEnginePage.FindFlag.FindBackward)

    def _find_text(self, text, flags):
        """Execute find on current page"""
        web_view = self.browser.get_active_web_view()
        if not web_view:
            return

        def callback(found):
            if found:
                self.match_label.setText("Match found")
                self.match_label.setStyleSheet(
                    "color: #059669; font-size: 12px; min-width: 80px;"
                )
            else:
                self.match_label.setText("No matches")
                self.match_label.setStyleSheet(
                    "color: #dc2626; font-size: 12px; min-width: 80px;"
                )

        web_view.findText(text, flags, callback)

    def _clear_highlights(self):
        """Clear all search highlights"""
        web_view = self.browser.get_active_web_view()
        if web_view:
            web_view.findText("")


def setup_find_in_page(browser):
    """Set up find in page for the browser"""
    return FindBar(browser)
