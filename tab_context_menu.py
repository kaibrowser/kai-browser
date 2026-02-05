"""
Tab Context Menu - Right-click menu for tabs
"""

from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt


class TabContextMenu:
    """Handles right-click context menu for tabs"""

    def __init__(self, browser):
        self.browser = browser
        self.pinned_tabs = set()  # Track pinned tab indices
        self._setup_menu()

    def _setup_menu(self):
        """Connect context menu to tab bar"""
        self.browser.tab_bar.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.browser.tab_bar.customContextMenuRequested.connect(self._show_menu)

    def _show_menu(self, pos):
        """Show context menu for tab at position"""
        tab_index = self.browser.tab_bar.tabAt(pos)
        if tab_index < 0:
            return

        menu = QMenu(self.browser)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: white;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #f3f4f6;
            }
            QMenu::separator {
                height: 1px;
                background: #e5e7eb;
                margin: 4px 8px;
            }
        """
        )

        # New tab
        new_tab = QAction("➕ New tab", menu)
        new_tab.triggered.connect(self.browser.create_new_tab)
        menu.addAction(new_tab)

        menu.addSeparator()

        # Duplicate tab
        duplicate = QAction("📋 Duplicate tab", menu)
        duplicate.triggered.connect(lambda: self._duplicate_tab(tab_index))
        menu.addAction(duplicate)

        # Pin/Unpin tab
        is_pinned = tab_index in self.pinned_tabs
        pin_text = "📌 Unpin tab" if is_pinned else "📌 Pin tab"
        pin_action = QAction(pin_text, menu)
        pin_action.triggered.connect(lambda: self._toggle_pin(tab_index))
        menu.addAction(pin_action)

        menu.addSeparator()

        # Reload tab
        reload_tab = QAction("⟳ Reload tab", menu)
        reload_tab.triggered.connect(lambda: self._reload_tab(tab_index))
        menu.addAction(reload_tab)

        # Mute tab (placeholder - would need audio detection)
        # mute_tab = QAction("🔇 Mute tab", menu)
        # menu.addAction(mute_tab)

        menu.addSeparator()

        # Close other tabs
        close_others = QAction("Close other tabs", menu)
        close_others.triggered.connect(lambda: self._close_other_tabs(tab_index))
        close_others.setEnabled(len(self.browser.tabs) > 1)
        menu.addAction(close_others)

        # Close tabs to the right
        close_right = QAction("Close tabs to the right", menu)
        close_right.triggered.connect(lambda: self._close_tabs_right(tab_index))
        close_right.setEnabled(tab_index < len(self.browser.tabs) - 1)
        menu.addAction(close_right)

        menu.addSeparator()

        # Close tab
        close_tab = QAction("✕ Close tab", menu)
        close_tab.triggered.connect(lambda: self.browser.close_tab(tab_index))
        menu.addAction(close_tab)

        menu.exec(self.browser.tab_bar.mapToGlobal(pos))

    def _duplicate_tab(self, index):
        """Duplicate a tab"""
        if 0 <= index < len(self.browser.tabs):
            url = self.browser.tabs[index].get_url()
            self.browser.create_new_tab(url)
            self.browser.show_status("Tab duplicated", 1500)

    def _toggle_pin(self, index):
        """Pin or unpin a tab"""
        if index in self.pinned_tabs:
            # Unpin
            self.pinned_tabs.discard(index)
            self.browser.tab_bar.setTabText(
                index, self.browser.tabs[index].get_title()[:20]
            )
            self.browser.show_status("Tab unpinned", 1500)
        else:
            # Pin - move to front and shorten
            self.pinned_tabs.add(index)
            self.browser.tab_bar.setTabText(index, "📌")
            self.browser.show_status("Tab pinned", 1500)

    def _reload_tab(self, index):
        """Reload a specific tab"""
        if 0 <= index < len(self.browser.tabs):
            self.browser.tabs[index].get_web_view().reload()

    def _close_other_tabs(self, keep_index):
        """Close all tabs except the specified one"""
        # Close from end to start to avoid index shifting issues
        for i in range(len(self.browser.tabs) - 1, -1, -1):
            if i != keep_index and i not in self.pinned_tabs:
                self.browser.close_tab(i)
        self.browser.show_status("Other tabs closed", 1500)

    def _close_tabs_right(self, index):
        """Close all tabs to the right of specified index"""
        for i in range(len(self.browser.tabs) - 1, index, -1):
            if i not in self.pinned_tabs:
                self.browser.close_tab(i)
        self.browser.show_status("Tabs closed", 1500)


def setup_tab_context_menu(browser):
    """Set up tab context menu"""
    return TabContextMenu(browser)
