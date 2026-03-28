"""
BrowserTab - Individual tab management
Uses settings for homepage
"""

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from kai_core.profile import setup_page_permissions


class PixmapPromise(QPixmap):
    """QPixmap subclass that also supports .then(callback) and .catch(callback).
    Passes Qt C++ type checks while allowing AI-natural promise-style usage."""

    def __new__(cls, pixmap):
        # Copy pixmap data into a real QPixmap instance of this subclass
        instance = QPixmap.__new__(cls)
        return instance

    def __init__(self, pixmap):
        super().__init__(pixmap)

    def then(self, callback):
        callback(self)
        return self

    def catch(self, callback):
        return self


class KaiWebEngineView(QWebEngineView):
    """QWebEngineView with AI compatibility translations"""

    def grab(self, rectangle=None):
        """Returns a PixmapPromise so grab().then(cb) works naturally"""
        if rectangle is not None:
            pixmap = super().grab(rectangle)
        else:
            pixmap = super().grab()
        return PixmapPromise(pixmap)


class BrowserTab:
    """Represents a single browser tab with its own web view"""

    def __init__(self, profile, url=None, settings_manager=None, preferences=None):
        self.web_view = KaiWebEngineView()  # Use our translated subclass
        self.settings_manager = settings_manager

        page = QWebEnginePage(profile, self.web_view)
        self.web_view.setPage(page)

        if preferences:
            setup_page_permissions(page, preferences)

        if url:
            self.web_view.setUrl(QUrl(url))
        else:
            homepage = self._get_homepage()
            self.web_view.setUrl(QUrl(homepage))

        self.title = "New Tab"
        self._url = url or self._get_homepage()

        self.web_view.titleChanged.connect(self._on_title_changed)
        self.web_view.urlChanged.connect(self._on_url_changed)

    def _get_homepage(self):
        if self.settings_manager:
            return self.settings_manager.get_homepage()
        return "https://www.google.com"

    def _on_title_changed(self, title):
        self.title = title if title else "New Tab"

    def _on_url_changed(self, url):
        self._url = url.toString()

    def get_web_view(self):
        return self.web_view

    def get_title(self):
        return self.title

    def get_url(self):
        return self._url

    def page(self):
        return self.web_view.page()

    def navigate_to(self, url):
        self.web_view.setUrl(QUrl(url))

    def url(self):
        return QUrl(self.get_url())

    def setUrl(self, url):
        if isinstance(url, QUrl):
            self.navigate_to(url.toString())
        else:
            self.navigate_to(str(url))
