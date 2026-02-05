"""
Bookmarks - Star in URL bar opens sidebar with all controls
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
    QMessageBox,
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal


class BookmarksManager:
    """Handles bookmark storage and retrieval"""

    def __init__(self, preferences):
        self.preferences = preferences
        self._bookmarks = None

    def _load_bookmarks(self):
        """Load bookmarks from preferences"""
        if self._bookmarks is None:
            data = self.preferences.get_module_setting("Bookmarks", "data", "[]")
            try:
                self._bookmarks = json.loads(data)
            except:
                self._bookmarks = []
        return self._bookmarks

    def _save_bookmarks(self):
        """Save bookmarks to preferences"""
        self.preferences.set_module_setting(
            "Bookmarks", "data", json.dumps(self._bookmarks)
        )

    def get_all(self):
        """Get all bookmarks"""
        return self._load_bookmarks()

    def add(self, url, title):
        """Add a bookmark"""
        bookmarks = self._load_bookmarks()

        if self.is_bookmarked(url):
            return False

        bookmarks.append(
            {"url": url, "title": title, "added": datetime.now().isoformat()}
        )

        self._save_bookmarks()
        return True

    def remove(self, url):
        """Remove a bookmark by URL"""
        bookmarks = self._load_bookmarks()
        self._bookmarks = [b for b in bookmarks if b["url"] != url]
        self._save_bookmarks()

    def is_bookmarked(self, url):
        """Check if URL is bookmarked"""
        bookmarks = self._load_bookmarks()
        return any(b["url"] == url for b in bookmarks)

    def clear_all(self):
        """Clear all bookmarks"""
        self._bookmarks = []
        self._save_bookmarks()


class BookmarksSidebar(QFrame):
    """Sidebar with bookmark list and controls"""

    bookmark_changed = pyqtSignal()  # Signal emitted when bookmarks change

    def __init__(self, browser, manager):
        super().__init__()
        self.browser = browser
        self.manager = manager  # Use shared manager instance

        self.setFixedWidth(300)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #fafafa;
                border-left: 1px solid #e5e7eb;
            }
        """
        )

        self.setup_ui()

        # Listen for URL changes to update add/remove button
        browser.url_changed.connect(self.update_add_button)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(
            """
            QFrame {
                background-color: #f3f4f6;
                border-bottom: 1px solid #e5e7eb;
            }
        """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel("Bookmarks")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
            }
        """
        )
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)

        layout.addWidget(header)

        # Add/Remove current page button
        self.add_btn = QPushButton()
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.toggle_current_page)
        self.add_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #7c3aed;
                color: white;
                border: none;
                padding: 10px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #6d28d9;
            }
        """
        )
        layout.addWidget(self.add_btn)

        # Scroll area for bookmarks
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(8, 8, 8, 8)
        self.list_layout.setSpacing(4)
        self.list_layout.addStretch()

        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)

        # Empty state label
        self.empty_label = QLabel("No bookmarks yet")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(
            "color: #9ca3af; padding: 40px; font-size: 13px;"
        )
        self.empty_label.hide()

    def update_add_button(self, url=None):
        """Update add/remove button based on current page"""
        if url is None:
            url = self.browser.get_current_url()

        if self.manager.is_bookmarked(url):
            self.add_btn.setText("★ Remove this page")
            self.add_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #f59e0b;
                    color: white;
                    border: none;
                    padding: 10px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #d97706;
                }
            """
            )
        else:
            self.add_btn.setText("☆ Add this page")
            self.add_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #7c3aed;
                    color: white;
                    border: none;
                    padding: 10px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #6d28d9;
                }
            """
            )

    def toggle_current_page(self):
        """Add or remove current page from bookmarks"""
        url = self.browser.get_current_url()
        title = self.browser.get_current_title() or url

        if self.manager.is_bookmarked(url):
            self.manager.remove(url)
            self.browser.show_status("Bookmark removed", 2000)
        else:
            self.manager.add(url, title)
            self.browser.show_status("Bookmark added", 2000)

        self.update_add_button()
        self.refresh()
        self.bookmark_changed.emit()  # Notify star to update

    def refresh(self):
        """Refresh bookmark list"""
        # Clear existing bookmark rows (keep stretch at end)
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget and widget != self.empty_label:
                widget.deleteLater()

        bookmarks = self.manager.get_all()

        if not bookmarks:
            self.list_layout.insertWidget(0, self.empty_label)
            self.empty_label.show()
            return

        # Remove empty label if showing
        if self.empty_label.parent() == self.list_container:
            self.list_layout.removeWidget(self.empty_label)
        self.empty_label.hide()

        for bookmark in bookmarks:
            row = self._create_bookmark_row(bookmark)
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)

    def _create_bookmark_row(self, bookmark):
        """Create a row for a bookmark"""
        row = QFrame()
        row.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
            }
            QFrame:hover {
                background-color: #f9fafb;
            }
            QToolTip {
                background-color: #1f2937;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
            }
        """
        )

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 8, 6, 8)
        row_layout.setSpacing(8)

        # Clickable title
        title_btn = QPushButton(bookmark["title"][:35])
        title_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        title_btn.setToolTip(bookmark["url"])
        title_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                text-align: left;
                font-size: 12px;
                color: #1f2937;
                padding: 4px 0;
            }
            QPushButton:hover {
                color: #7c3aed;
            }
        """
        )
        title_btn.clicked.connect(lambda _, url=bookmark["url"]: self._navigate_to(url))
        row_layout.addWidget(title_btn, 1)

        # Delete button
        delete_btn = QPushButton("🗑")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setToolTip("Delete bookmark")
        delete_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #fee2e2;
                border-radius: 4px;
            }
        """
        )
        delete_btn.clicked.connect(
            lambda _, url=bookmark["url"]: self._delete_bookmark(url)
        )
        row_layout.addWidget(delete_btn)

        return row

    def _navigate_to(self, url):
        """Navigate to bookmark URL"""
        self.browser.browser.setUrl(QUrl(url))

    def _delete_bookmark(self, url):
        """Delete a bookmark"""
        self.manager.remove(url)
        self.refresh()
        self.update_add_button()
        self.browser.show_status("Bookmark deleted", 2000)
        self.bookmark_changed.emit()  # Notify star to update

    def showEvent(self, event):
        """Refresh when shown"""
        self.refresh()
        self.update_add_button()
        super().showEvent(event)


class BookmarkStar(QPushButton):
    """Star button in URL bar - opens sidebar"""

    def __init__(self, browser, sidebar, manager):
        super().__init__()
        self.browser = browser
        self.sidebar = sidebar
        self.manager = manager  # Use shared manager instance

        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self.toggle_sidebar)
        self.setToolTip("Bookmarks")

        self._update_style()

        # Listen for URL changes
        browser.url_changed.connect(self.on_url_changed)

        # Listen for tab switches
        browser.tab_changed.connect(self.on_tab_changed)

        # Listen for bookmark changes from sidebar
        sidebar.bookmark_changed.connect(self.refresh)

    def _update_style(self):
        """Update star appearance based on current page bookmark state"""
        url = (
            self.browser.get_current_url()
            if hasattr(self.browser, "get_current_url")
            else ""
        )
        is_bookmarked = self.manager.is_bookmarked(url) if url else False

        if is_bookmarked:
            self.setText("★")
            self.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 18px;
                    color: #f59e0b;
                }
                QPushButton:hover {
                    color: #d97706;
                }
            """
            )
        else:
            self.setText("☆")
            self.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 18px;
                    color: #9ca3af;
                }
                QPushButton:hover {
                    color: #f59e0b;
                }
            """
            )

    def on_tab_changed(self, index):
        """Update star when switching tabs"""
        self._update_style()

    def on_url_changed(self, url):
        """Update star when URL changes"""
        self._update_style()

    def toggle_sidebar(self):
        """Toggle sidebar visibility"""
        if self.sidebar.isVisible():
            self.sidebar.hide()
        else:
            self.sidebar.refresh()
            self.sidebar.update_add_button()
            self.sidebar.show()

    def refresh(self):
        """Refresh star state"""
        self._update_style()


def setup_bookmarks(browser):
    """
    Set up bookmarks for the browser
    Returns: (star_widget, sidebar)
    """
    # Create shared manager instance
    manager = BookmarksManager(browser.preferences)

    # Create sidebar and star with shared manager
    sidebar = BookmarksSidebar(browser, manager)
    sidebar.hide()

    star = BookmarkStar(browser, sidebar, manager)

    return star, sidebar
