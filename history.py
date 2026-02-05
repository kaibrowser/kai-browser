"""
History - Track visited pages, view and manage in Settings
"""

import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QLineEdit,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QUrl


class HistoryManager:
    """Handles history storage and retrieval"""

    MAX_ENTRIES = 500

    def __init__(self, preferences):
        self.preferences = preferences
        self._history = None

    def _load_history(self):
        """Load history from preferences"""
        if self._history is None:
            data = self.preferences.get_module_setting("History", "data", "[]")
            try:
                self._history = json.loads(data)
            except:
                self._history = []
        return self._history

    def _save_history(self):
        """Save history to preferences"""
        self.preferences.set_module_setting(
            "History", "data", json.dumps(self._history)
        )

    def add(self, url, title):
        """Add a page to history"""
        # Skip empty or about pages
        if not url or url.startswith("about:") or url.startswith("data:"):
            return

        history = self._load_history()

        # Remove duplicate if exists (will re-add at top)
        history = [h for h in history if h["url"] != url]

        # Add to front
        history.insert(
            0,
            {"url": url, "title": title or url, "visited": datetime.now().isoformat()},
        )

        # Trim to max entries
        self._history = history[: self.MAX_ENTRIES]
        self._save_history()

    def get_all(self):
        """Get all history entries"""
        return self._load_history()

    def search(self, query):
        """Search history by title or URL"""
        query = query.lower()
        history = self._load_history()
        return [
            h
            for h in history
            if query in h["title"].lower() or query in h["url"].lower()
        ]

    def remove(self, url):
        """Remove a single entry"""
        history = self._load_history()
        self._history = [h for h in history if h["url"] != url]
        self._save_history()

    def clear_all(self):
        """Clear all history"""
        self._history = []
        self._save_history()


class HistoryManagerWidget(QWidget):
    """Widget for managing history in Settings - Simple list"""

    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.manager = HistoryManager(browser.preferences)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Search and clear row
        top_row = QHBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search...")
        self.search_box.setStyleSheet(
            """
            QLineEdit {
                padding: 6px 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """
        )
        self.search_box.textChanged.connect(self.on_search)
        top_row.addWidget(self.search_box)

        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet(
            """
            QPushButton {
                background: #ef4444;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: #dc2626;
            }
        """
        )
        clear_btn.clicked.connect(self.clear_all)
        top_row.addWidget(clear_btn)

        layout.addLayout(top_row)

        # Simple list
        from PyQt6.QtWidgets import QListWidget

        self.history_list = QListWidget()
        self.history_list.setStyleSheet(
            """
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover {
                background: #f5f5f5;
            }
            QListWidget::item:selected {
                background: #e5e7eb;
                color: black;
            }
        """
        )
        self.history_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.history_list)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet(
            """
            QPushButton {
                background: #f1f5f9;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: #e2e8f0;
            }
        """
        )
        delete_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(delete_btn)

        layout.addLayout(btn_row)

        self.refresh()

    def refresh(self, entries=None):
        """Refresh history list"""
        self.history_list.clear()

        if entries is None:
            entries = self.manager.get_all()

        for entry in entries[:100]:
            title = entry["title"][:50]
            self.history_list.addItem(title)
            item = self.history_list.item(self.history_list.count() - 1)
            item.setData(Qt.ItemDataRole.UserRole, entry["url"])
            item.setToolTip(entry["url"])

    def _on_item_double_clicked(self, item):
        """Navigate to URL on double-click"""
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self.browser.browser.setUrl(QUrl(url))
            self.window().accept()

    def _delete_selected(self):
        """Delete selected entry"""
        item = self.history_list.currentItem()
        if item:
            url = item.data(Qt.ItemDataRole.UserRole)
            self.manager.remove(url)
            self.refresh()
            self.browser.show_status("Entry deleted", 2000)

    def on_search(self, query):
        """Filter history"""
        if query.strip():
            results = self.manager.search(query)
            self.refresh(results)
        else:
            self.refresh()

    def clear_all(self):
        """Clear all history"""
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Delete all history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.manager.clear_all()
            self.refresh()
            self.browser.show_status("History cleared", 2000)

    def showEvent(self, event):
        """Refresh when shown"""
        self.refresh()
        super().showEvent(event)


def track_page_visit(browser, url, title):
    """Call this when a page loads to track history"""
    manager = HistoryManager(browser.preferences)
    manager.add(url, title)
