"""
Navigation - Toolbar, URL bar, and navigation controls
Uses settings for search engine and homepage
Now includes security indicator
"""

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolBar, QLineEdit, QWidget, QHBoxLayout
from settings import show_settings_dialog, SettingsManager
from security_indicator import setup_security_indicator
from PyQt6.QtCore import Qt


class NavigationManager:
    """Handles navigation toolbar and URL bar"""

    def __init__(self, browser):
        self.browser = browser
        self.settings_manager = SettingsManager(browser.preferences)
        self.security_indicator = None

    def setup_navbar(self):
        """Create and configure navigation toolbar"""
        navbar = QToolBar()

        navbar.setStyleSheet(
            """
            QToolBar {
                background-color: #fafafa;
                border-top: none;
                border-bottom: none;
                spacing: 4px;
                padding: 6px 12px 6px 6px;
            }
            QToolBar::separator {
                background-color: #d0d0d0;
                width: 1px;
                margin: 4px 8px;
            }
            QToolBar QToolButton {
                border: none;
                background-color: transparent;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
            }
            QToolBar QToolButton:hover {
                background-color: #d7d7db;
            }
            QToolBar QToolButton:pressed {
                background-color: #c0c0c0;
            }
            QToolButton#qt_toolbar_ext_button {
                background-color: #ebebed;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 2px 4px;
                min-width: 16px;
                max-width: 16px;
                margin: 0px 6px 0px 0px;
                qproperty-icon: none;
                qproperty-text: "»";
                font-size: 11px;
                font-weight: bold;
            }
        """
        )

        navbar.setMovable(False)
        navbar.setFloatable(False)

        navbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)

        self.browser.addToolBar(navbar)

        return navbar

    def setup_url_bar(self, navbar):
        """Create URL bar with security indicator"""
        # Create container for security indicator + URL bar
        url_container = QWidget()
        url_container.setStyleSheet("background: transparent;")
        container_layout = QHBoxLayout(url_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Security indicator (padlock)
        self.security_indicator = setup_security_indicator(self.browser)
        container_layout.addWidget(self.security_indicator)

        # URL bar
        url_bar = QLineEdit()
        url_bar.setMinimumWidth(250)
        url_bar.returnPressed.connect(self.navigate_to_url)
        url_bar.setStyleSheet(
            """
            QLineEdit {
                border: none;
                padding: 6px 10px;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                background-color: white;
                outline: none;
            }
            QMenu {
                background-color: white;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                color: #1f2937;
            }
            QMenu::item:selected {
                background-color: #f3f4f6;
            }
        """
        )
        container_layout.addWidget(url_bar, 1)

        # Add container to navbar
        navbar.addWidget(url_container)

        return url_bar

    def setup_basic_navigation(self, navbar):
        """Set up basic back, forward, reload buttons"""
        # Back button
        back_btn = QAction("←", self.browser)
        back_btn.setToolTip("Back")
        back_btn.triggered.connect(lambda: self._navigate_active_tab("back"))
        navbar.insertAction(navbar.actions()[0] if navbar.actions() else None, back_btn)

        # Forward button
        forward_btn = QAction("→", self.browser)
        forward_btn.setToolTip("Forward")
        forward_btn.triggered.connect(lambda: self._navigate_active_tab("forward"))
        navbar.insertAction(
            navbar.actions()[1] if len(navbar.actions()) > 1 else None,
            forward_btn,
        )

        # Reload button
        reload_btn = QAction("⟳", self.browser)
        reload_btn.setToolTip("Refresh Page")
        reload_btn.triggered.connect(lambda: self._navigate_active_tab("reload"))
        navbar.insertAction(
            navbar.actions()[2] if len(navbar.actions()) > 2 else None,
            reload_btn,
        )

        # Settings button
        settings_btn = QAction("⋮", self.browser)
        settings_btn.setToolTip("Settings")
        settings_btn.triggered.connect(lambda: show_settings_dialog(self.browser))
        navbar.addAction(settings_btn)

    def navigate_to_url(self):
        """Navigate active tab to the URL in the URL bar"""
        url = self.browser.url_bar.text().strip()

        if not url:
            return

        active_tab = self.browser.get_active_tab()
        if not active_tab:
            return

        # Smart URL handling
        if " " in url or ("." not in url and "/" not in url):
            # Search query - use settings for search engine
            url = self.settings_manager.get_search_url(url)
        elif not url.startswith("http://") and not url.startswith("https://"):
            # Add protocol
            url = f"https://{url}"

        active_tab.navigate_to(url)

    def _navigate_active_tab(self, action):
        """Execute navigation action on active tab"""
        web_view = self.browser.get_active_web_view()
        if not web_view:
            return

        if action == "back":
            web_view.back()
        elif action == "forward":
            web_view.forward()
        elif action == "reload":
            web_view.reload()

    def update_url_bar(self):
        """Update URL bar with active tab's URL"""
        active_tab = self.browser.get_active_tab()
        if active_tab:
            url = active_tab.get_url()
            self.browser.url_bar.setText(url)
            # Security indicator updates automatically via signal
