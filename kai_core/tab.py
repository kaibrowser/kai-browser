"""
BrowserTab - Individual tab management
Uses settings for homepage
"""

from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from kai_core.profile import setup_page_permissions


class BrowserTab:
    """Represents a single browser tab with its own web view"""

    def __init__(self, profile, url=None, settings_manager=None, preferences=None):
        self.web_view = QWebEngineView()
        self.settings_manager = settings_manager

        # Use shared profile for persistent storage
        page = QWebEnginePage(profile, self.web_view)
        self.web_view.setPage(page)

        # Set up permission handling (camera, microphone, etc.)
        if preferences:
            setup_page_permissions(page, preferences)

        # Set initial URL
        if url:
            self.web_view.setUrl(QUrl(url))
        else:
            homepage = self._get_homepage()
            self.web_view.setUrl(QUrl(homepage))

        # Tab metadata
        self.title = "New Tab"
        self._url = url or self._get_homepage()

        # Connect signals for metadata updates
        self.web_view.titleChanged.connect(self._on_title_changed)
        self.web_view.urlChanged.connect(self._on_url_changed)

    def _get_homepage(self):
        """Get homepage from settings or default"""
        if self.settings_manager:
            return self.settings_manager.get_homepage()
        return "https://www.google.com"

    def _on_title_changed(self, title):
        """Update tab title"""
        self.title = title if title else "New Tab"

    def _on_url_changed(self, url):
        """Update tab URL"""
        self._url = url.toString()

    def get_web_view(self):
        """Get the QWebEngineView for this tab"""
        return self.web_view

    def get_title(self):
        """Get current tab title"""
        return self.title

    def get_url(self):
        """Get current tab URL"""
        return self._url

    def page(self):
        """Compatibility: Allow tab.page() to work like web_view.page()"""
        return self.web_view.page()

    def navigate_to(self, url):
        """Navigate this tab to a URL"""
        self.web_view.setUrl(QUrl(url))

    def url(self):
        """Compatibility: Allow tab.url() to work like web_view.url()"""
        return QUrl(self.get_url())

    def setUrl(self, url):
        """Compatibility: Allow tab.setUrl() to work"""
        if isinstance(url, QUrl):
            self.navigate_to(url.toString())
        else:
            self.navigate_to(str(url))
