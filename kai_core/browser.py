"""
KaiBrowser - Main browser class
Tab-enabled browser with global exception handling and module system
Uses settings for homepage and search engine
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStatusBar,
    QTabBar,
    QStackedWidget,
    QPushButton,
)
from PyQt6.QtGui import QKeySequence, QShortcut

from kai_preferences import KaiPreferences
from settings import SettingsManager
from .tab import BrowserTab
from .profile import setup_persistent_profile, clear_profile_data
from .navigation import NavigationManager
from .session import SessionManager
from .exceptions import ExceptionHandler
from .module_loader import ModuleLoader
from updater import check_for_updates
from bookmarks import setup_bookmarks
from downloads import setup_downloads
from find_in_page import setup_find_in_page
from print_page import setup_print
from zoom_controls import setup_zoom
from context_menu import setup_context_menu
from tab_context_menu import setup_tab_context_menu


class KaiBrowser(QMainWindow):
    """
    Tab-enabled browser with global exception handling
    Layout: Window Title → Navbar → Tab Bar → Content
    """

    # Signals that modules can listen to (fired from active tab)
    page_loaded = pyqtSignal(str)
    url_changed = pyqtSignal(str)
    title_changed = pyqtSignal(str)
    tab_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("kai")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize preferences manager
        self.preferences = KaiPreferences()
        print(f"✓ Preferences loaded from: {self.preferences.prefs_file}")

        # Initialize settings manager
        self.settings_manager = SettingsManager(self.preferences)

        # Error tracking for AI
        self.runtime_errors = {}

        # Tab management
        self.tabs = []
        self.current_tab_index = 0

        # Set up persistent profile (shared across all tabs)
        self.profile = setup_persistent_profile()

        # Create the tab structure FIRST
        self._setup_tab_widget()

        # IMPORTANT: Set central widget BEFORE adding toolbars
        self.setCentralWidget(self.tab_container)

        # Create status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # NOW create navigation manager and navbar
        self.nav_manager = NavigationManager(self)
        self.navbar = self.nav_manager.setup_navbar()

        # URL bar (controls active tab)
        self.url_bar = self.nav_manager.setup_url_bar(self.navbar)
        # ---------------------------------
        self.bookmark_star, self.bookmarks_sidebar = setup_bookmarks(self)

        # Connect the signal explicitly
        self.bookmarks_sidebar.bookmark_changed.connect(self.bookmark_star.refresh)

        # Add star to URL bar area (insert into toolbar after url_bar)
        self.navbar.addWidget(self.bookmark_star)

        # Add sidebar to layout (remove duplicate)
        self.sidebar_container.setParent(None)
        self.content_stack.parent().layout().addWidget(self.bookmarks_sidebar)

        # Downloads manager
        self.download_btn, self.downloads_sidebar = setup_downloads(self)
        self.navbar.addWidget(self.download_btn)
        self.content_stack.parent().layout().addWidget(self.downloads_sidebar)

        # Find in page bar
        self.find_bar = setup_find_in_page(self)
        self.tab_layout.insertWidget(0, self.find_bar)

        self.print_manager = setup_print(self)

        self.zoom_manager = setup_zoom(self)

        self.context_menu = setup_context_menu(self)

        self.tab_context_menu = setup_tab_context_menu(self)
        # -------------------------------------

        # Basic navigation
        self.nav_manager.setup_basic_navigation(self.navbar)

        # Tab shortcuts
        self._setup_tab_shortcuts()

        # Connect tab bar signals
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        self.tab_bar.tabCloseRequested.connect(self.close_tab)

        # Session manager
        self.session_manager = SessionManager(self, self.preferences)

        # Module loader
        self.module_loader = ModuleLoader(self)

        # Legacy aliases for backward compatibility
        self.toolbar = self.navbar
        self.modules = self.module_loader.modules
        self._module_metadata = self.module_loader._module_metadata

        # Install global exception handler LAST (after everything is set up)
        self.exception_handler = ExceptionHandler(self)
        self.exception_handler.install()

        # Restore previous session OR create first tab
        restore_enabled = self.settings_manager.get("restore_session")
        if restore_enabled and self.session_manager.restore_session():
            pass  # Session restored
        else:
            self.create_new_tab()

        check_for_updates(self, silent=True)

    def hard_refresh(self):
        """Hard refresh current page (bypass cache)"""
        web_view = self.get_active_web_view()
        if web_view:
            web_view.triggerPageAction(web_view.page().WebAction.ReloadAndBypassCache)
            self.show_status("🔄 Hard refresh", 1000)

    def _setup_tab_widget(self):
        """Set up custom tab bar + stacked widget for tab management"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tab_bar_container = QWidget()
        tab_bar_container.setStyleSheet("background-color: #fafafa;;")
        tab_bar_layout = QVBoxLayout(tab_bar_container)
        tab_bar_layout.setContentsMargins(0, 0, 0, 0)
        tab_bar_layout.setSpacing(0)

        tab_row = QWidget()
        tab_row.setStyleSheet("background-color: #fafafa;;")
        tab_row_layout = QHBoxLayout(tab_row)
        tab_row_layout.setContentsMargins(0, 0, 0, 0)
        tab_row_layout.setSpacing(0)

        self.tab_bar = QTabBar()
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.setMovable(True)
        self.tab_bar.setExpanding(False)
        self.tab_bar.setDrawBase(False)

        from PyQt6.QtCore import Qt

        self.tab_bar.setExpanding(True)
        self.tab_bar.setElideMode(Qt.TextElideMode.ElideRight)

        self.tab_bar.setStyleSheet(
            """
            QTabBar {
                background-color: #fafafa;  
            }
            QTabBar::tab {
                padding: 4px 16px;
                margin-right: 2px;
                margin-bottom: 2px;
                background-color: #fafafa;;
                border: none;
                border-bottom: none;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #7c3aed;
            }
            QTabBar::tab:hover {
                background-color: #d7d7db;
            }
        """
        )

        new_tab_btn = QPushButton("+")
        new_tab_btn.setFixedHeight(28)
        new_tab_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #fafafa;;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #d7d7db;
            }
            QPushButton:pressed {
                background-color: #bcbcbc;
            }
        """
        )
        new_tab_btn.clicked.connect(self.create_new_tab)

        tab_row_layout.addWidget(self.tab_bar)
        tab_row_layout.addWidget(new_tab_btn)
        tab_row_layout.addStretch()

        tab_bar_layout.addWidget(tab_row)
        layout.addWidget(tab_bar_container)

        # Content area with sidebar
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack)

        # Sidebar placeholder (will be replaced after bookmarks init)
        self.sidebar_container = QWidget()
        content_layout.addWidget(self.sidebar_container)

        layout.addWidget(content_area)

        self.tab_container = container
        self.tab_layout = layout

    def _setup_tab_shortcuts(self):
        """Set up keyboard shortcuts for tab management"""
        new_tab_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        new_tab_shortcut.activated.connect(self.create_new_tab)

        close_tab_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_tab_shortcut.activated.connect(
            lambda: self.close_tab(self.current_tab_index)
        )

        hard_refresh_shortcut = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        hard_refresh_shortcut.activated.connect(self.hard_refresh)

        next_tab_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        next_tab_shortcut.activated.connect(self.next_tab)

        prev_tab_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        prev_tab_shortcut.activated.connect(self.previous_tab)

        for i in range(1, 9):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut.activated.connect(lambda idx=i - 1: self.switch_to_tab(idx))

        last_tab_shortcut = QShortcut(QKeySequence("Ctrl+9"), self)
        last_tab_shortcut.activated.connect(
            lambda: self.switch_to_tab(len(self.tabs) - 1)
        )

    # ============================================================================
    # TAB MANAGEMENT METHODS
    # ============================================================================

    def create_new_tab(self, url=None):
        """Create a new browser tab"""
        new_tab = BrowserTab(self.profile, url, self.settings_manager, self.preferences)
        self.tabs.append(new_tab)
        self.content_stack.addWidget(new_tab.get_web_view())

        tab_index = self.tab_bar.addTab(new_tab.get_title()[:20])

        close_btn = QPushButton("🗙")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                font-size: 14px;
                padding: 0px;
                margin-right: 4px;
            }
            QPushButton:hover {
                background-color: #bcbcbc;
                border-radius: 3px;
                color: white;
            }
        """
        )
        close_btn.clicked.connect(
            lambda _, t=new_tab: self.close_tab(
                self.tabs.index(t) if t in self.tabs else -1
            )
        )
        self.tab_bar.setTabButton(
            tab_index, QTabBar.ButtonPosition.RightSide, close_btn
        )

        self._connect_tab_signals(new_tab)

        self.tab_bar.setCurrentIndex(tab_index)
        self.content_stack.setCurrentIndex(tab_index)

        self.nav_manager.update_url_bar()

        print(f"✓ Created tab {tab_index + 1}: {new_tab.get_url()}")

        return new_tab

    def close_tab(self, index):
        """Close a tab by index"""
        if len(self.tabs) <= 1:
            homepage = self.settings_manager.get_homepage()
            self.tabs[0].navigate_to(homepage)
            return

        if index < 0 or index >= len(self.tabs):
            return

        removed_tab = self.tabs.pop(index)

        self.tab_bar.removeTab(index)
        widget = self.content_stack.widget(index)
        self.content_stack.removeWidget(widget)

        removed_tab.get_web_view().deleteLater()

        if index < len(self.tabs):
            self.current_tab_index = index
        else:
            self.current_tab_index = len(self.tabs) - 1

        print(f"✓ Closed tab {index + 1}")

    def switch_to_tab(self, index):
        """Switch to a specific tab by index"""
        if 0 <= index < len(self.tabs):
            self.tab_bar.setCurrentIndex(index)
            self.content_stack.setCurrentIndex(index)

    def next_tab(self):
        """Switch to next tab (wraps around)"""
        next_index = (self.current_tab_index + 1) % len(self.tabs)
        self.switch_to_tab(next_index)

    def previous_tab(self):
        """Switch to previous tab (wraps around)"""
        prev_index = (self.current_tab_index - 1) % len(self.tabs)
        self.switch_to_tab(prev_index)

    def get_active_tab(self):
        """Get the currently active BrowserTab object"""
        if 0 <= self.current_tab_index < len(self.tabs):
            return self.tabs[self.current_tab_index]
        return None

    def get_active_web_view(self):
        """Get the active tab's web view"""
        active_tab = self.get_active_tab()
        return active_tab.get_web_view() if active_tab else None

    @property
    def tab_widget(self):
        """Compatibility: AI expects a QTabWidget-like interface"""
        return self._TabWidgetCompat(self)

    class _TabWidgetCompat:
        """Mimics QTabWidget interface for AI compatibility"""

        def __init__(self, browser):
            self.browser = browser

        def count(self):
            """Return number of tabs"""
            return len(self.browser.tabs)

        def widget(self, index):
            """Get web view at index"""
            if 0 <= index < len(self.browser.tabs):
                return self.browser.tabs[index].get_web_view()
            return None

    def add_new_tab(self, url=None):
        """Compatibility: AI expects this method name"""
        # Convert QUrl to string if needed
        if isinstance(url, QUrl):
            url = url.toString()
        return self.create_new_tab(url)

    def _on_tab_changed(self, index):
        """Handle tab switch"""
        if index < 0 or index >= len(self.tabs):
            return

        self.current_tab_index = index
        self.content_stack.setCurrentIndex(index)
        self.nav_manager.update_url_bar()

        active_tab = self.get_active_tab()
        if active_tab:
            self.setWindowTitle(f"{active_tab.get_title()} - kai")

        self.tab_changed.emit(index)

        print(f"✓ Switched to tab {index + 1}")

    def _connect_tab_signals(self, tab):
        """Connect a tab's signals to browser signals (for modules to listen)"""
        web_view = tab.get_web_view()

        web_view.urlChanged.connect(
            lambda url: (
                self._on_url_changed(url) if tab == self.get_active_tab() else None
            )
        )
        web_view.loadFinished.connect(
            lambda: self._on_page_loaded() if tab == self.get_active_tab() else None
        )

        web_view.loadProgress.connect(
            lambda progress: self._update_tab_progress(tab, progress)
        )

        web_view.titleChanged.connect(lambda title: self._update_tab_title(tab, title))
        web_view.page().newWindowRequested.connect(self._on_new_window_requested)

    def _update_tab_title(self, tab, title):
        """Update tab title in the tab bar (works for any tab, not just active)"""
        try:
            tab_index = self.tabs.index(tab)
            display_title = title[:20] if title else "New Tab"
            self.tab_bar.setTabText(tab_index, display_title)

            if tab == self.get_active_tab():
                self.setWindowTitle(f"{title} - kai")
                self.title_changed.emit(title)
        except ValueError:
            pass

    def _update_tab_progress(self, tab, progress):
        """Update tab loading progress indicator"""
        try:
            tab_index = self.tabs.index(tab)

            if progress < 100:
                # Loading - show gradient based on progress
                gradient_stop = max(0.01, progress / 100.0)  # Ensure minimum visibility

                # Build complete stylesheet with progress for THIS tab only
                base_style = """
                    QTabBar {
                        background-color: #fafafa;  
                    }
                    QTabBar::tab {
                        padding: 4px 16px;
                        margin-right: 2px;
                        margin-bottom: 2px;
                        background-color: #fafafa;
                        border: none;
                        border-bottom: 2px solid transparent;
                        border-radius: 4px;
                    }
                    QTabBar::tab:selected {
                        background-color: white;
                    }
                    QTabBar::tab:hover {
                        background-color: #d7d7db;
                    }
                """

                # Add progress bar for selected tab
                if tab == self.get_active_tab():
                    progress_style = f"""
                        QTabBar::tab:selected {{
                            border-bottom: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #7c3aed, stop:{gradient_stop:.3f} #7c3aed,
                                stop:{gradient_stop:.3f} #e5e7eb, stop:1 #e5e7eb);
                        }}
                    """
                    self.tab_bar.setStyleSheet(base_style + progress_style)

            else:
                # Complete - reset to solid purple bar
                self._reset_tab_stylesheet()

        except ValueError:
            pass

    def _reset_tab_stylesheet(self):
        """Reset tab stylesheet to default"""
        self.tab_bar.setStyleSheet(
            """
            QTabBar {
                background-color: #fafafa;  
            }
            QTabBar::tab {
                padding: 4px 16px;
                margin-right: 2px;
                margin-bottom: 2px;
                background-color: #fafafa;;
                border: none;
                border-bottom: none;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #7c3aed;
            }
            QTabBar::tab:hover {
                background-color: #d7d7db;
            }
        """
        )

    def _on_new_window_requested(self, request):
        """Handle new window/tab requests (target="_blank", middle-click, etc.)"""
        url = request.requestedUrl().toString()

        if not url:
            return

        new_tab = self.create_new_tab(url)
        request.openIn(new_tab.get_web_view().page())

        print(f"✓ Opened new tab from link: {url[:50]}...")

    # ============================================================================
    # LEGACY COMPATIBILITY PROPERTIES & METHODS
    # ============================================================================

    @property
    def browser(self):
        """Legacy: return active tab's web view for backward compatibility"""
        return self.get_active_web_view()

    @property
    def web_view(self):
        """Legacy: return active tab's web view"""
        return self.get_active_web_view()

    @property
    def plugins(self):
        """Alias for modules - AI compatibility"""
        return self.modules

    def get_active_plugins(self):
        """Alias for get_enabled_plugins - AI compatibility"""
        return self.get_enabled_plugins()

    def set_active_tab(self, index):
        """Alias for switch_to_tab - AI compatibility"""
        self.switch_to_tab(index)

    def setUrl(self, url):
        """Legacy: Set URL on active tab"""
        active_tab = self.get_active_tab()
        if active_tab:
            if isinstance(url, QUrl):
                active_tab.navigate_to(url.toString())
            else:
                active_tab.navigate_to(str(url))

    # ============================================================================
    # NAVIGATION & SIGNAL HANDLING
    # ============================================================================

    def navigate_to_url(self):
        """Navigate active tab to the URL in the URL bar"""
        self.nav_manager.navigate_to_url()

    def _on_url_changed(self, url):
        """Internal handler for URL changes (active tab only)"""
        url_str = url.toString()
        self.url_bar.setText(url_str)

        active_tab = self.get_active_tab()
        if active_tab:
            tab_index = self.tabs.index(active_tab)
            self.tab_bar.setTabText(tab_index, active_tab.get_title()[:20])

        self.url_changed.emit(url_str)

    def _on_page_loaded(self):
        """Internal handler for page load completion (active tab only)"""
        active_tab = self.get_active_tab()
        if active_tab:
            url = active_tab.get_url()
            title = active_tab.get_title()

            # Track in history
            from history import track_page_visit

            track_page_visit(self, url, title)

            self.page_loaded.emit(url)

    # ============================================================================
    # MODULE API (works with active tab)
    # ============================================================================

    def load_module(self, module):
        """Load a module - delegates to ModuleLoader"""
        self.module_loader.load_module(module)

    def unload_module(self, module):
        """Unload a module - delegates to ModuleLoader"""
        self.module_loader.unload_module(module)

    def save_module_state(self, module, enabled):
        """Save a module's state to preferences"""
        self.module_loader.save_module_state(module, enabled)

    def enable_plugin(self, plugin_class_name):
        """Enable a plugin by class name"""
        # Check if already enabled
        for module in self.modules:
            if module.__class__.__name__ == plugin_class_name:
                # Already loaded - just make it visible
                if hasattr(module, "activate"):
                    # Natural plugin - show UI
                    for manager in self.modules:
                        if manager.__class__.__name__ == "ModuleManagerModule":
                            manager.natural_plugin_states[id(module)] = True
                            manager._show_natural_plugin(module)
                            break
                return True
        return False

    def disable_plugin(self, plugin_class_name):
        """Disable a plugin by class name"""
        for module in self.modules:
            if module.__class__.__name__ == plugin_class_name:
                if hasattr(module, "deactivate"):
                    # Natural plugin
                    for manager in self.modules:
                        if manager.__class__.__name__ == "ModuleManagerModule":
                            manager.natural_plugin_states[id(module)] = False
                            manager._hide_natural_plugin(module)
                            break
                return True
        return False

    def get_enabled_plugins(self):
        """Get list of enabled plugin class names"""
        active = []
        for module in self.modules:
            module_name = module.__class__.__name__

            # Skip system modules
            if module_name in ["ModuleManagerModule", "ExtensionBuilderModule"]:
                continue

            # Check if enabled
            if not hasattr(module, "enabled"):
                # Natural plugin - check if UI is visible
                if hasattr(module, "_tracked_actions") and module._tracked_actions:
                    is_visible = any(
                        action.isVisible() for action in module._tracked_actions
                    )
                    if is_visible:
                        active.append(module_name)
            elif module.enabled:
                active.append(module_name)

        return active

    def add_toolbar_action(self, action):
        """Allow modules to add actions to the toolbar"""
        self.navbar.addAction(action)

    def add_toolbar_widget(self, widget):
        """Allow modules to add widgets to the toolbar"""
        action = self.navbar.addWidget(widget)
        return action

    def show_status(self, message, timeout=3000):
        """Show a message in the status bar"""
        self.status.showMessage(message, timeout)

    def get_current_url(self):
        """Get the current page URL (active tab)"""
        active_tab = self.get_active_tab()
        return active_tab.get_url() if active_tab else ""

    def get_current_title(self):
        """Get the current page title (active tab)"""
        active_tab = self.get_active_tab()
        return active_tab.get_title() if active_tab else ""

    def inject_javascript(self, script):
        """Execute JavaScript on the current page (active tab)"""
        web_view = self.get_active_web_view()
        if web_view:
            web_view.page().runJavaScript(script)

    def clipboard(self):
        """Provide clipboard access for plugins"""
        return QApplication.clipboard()

    def clear_browsing_data(self):
        """Clear all stored browsing data"""
        clear_profile_data(self.profile)
        self.show_status("All browsing data cleared")

    # ============================================================================
    # SESSION MANAGEMENT (delegates to SessionManager)
    # ============================================================================

    def save_session(self):
        """Save current tabs to preferences"""
        self.session_manager.save_session()

    def restore_session(self):
        """Restore tabs from previous session"""
        return self.session_manager.restore_session()

    def closeEvent(self, event):
        """Save session on close"""
        self.save_session()
        event.accept()


def main():
    app = QApplication(sys.argv)
    browser = KaiBrowser()
    browser.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
