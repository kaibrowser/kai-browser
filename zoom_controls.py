"""
Zoom Controls - Ctrl+Plus/Minus/0 for zoom in/out/reset
"""

from PyQt6.QtGui import QShortcut, QKeySequence


class ZoomManager:
    """Handles page zoom for the browser"""

    def __init__(self, browser):
        self.browser = browser
        self.default_zoom = 1.0
        self.zoom_step = 0.1
        self.min_zoom = 0.25
        self.max_zoom = 5.0
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """Set up zoom shortcuts"""
        # Zoom in: Ctrl+Plus, Ctrl+=, Ctrl+Scroll
        zoom_in = QShortcut(QKeySequence("Ctrl++"), self.browser)
        zoom_in.activated.connect(self.zoom_in)

        zoom_in_alt = QShortcut(QKeySequence("Ctrl+="), self.browser)
        zoom_in_alt.activated.connect(self.zoom_in)

        # Zoom out: Ctrl+Minus
        zoom_out = QShortcut(QKeySequence("Ctrl+-"), self.browser)
        zoom_out.activated.connect(self.zoom_out)

        # Reset: Ctrl+0
        zoom_reset = QShortcut(QKeySequence("Ctrl+0"), self.browser)
        zoom_reset.activated.connect(self.zoom_reset)

    def get_current_zoom(self):
        """Get current zoom level"""
        web_view = self.browser.get_active_web_view()
        if web_view:
            return web_view.zoomFactor()
        return self.default_zoom

    def set_zoom(self, level):
        """Set zoom level"""
        web_view = self.browser.get_active_web_view()
        if not web_view:
            return

        # Clamp to min/max
        level = max(self.min_zoom, min(self.max_zoom, level))
        web_view.setZoomFactor(level)

        percent = int(level * 100)
        self.browser.show_status(f"Zoom: {percent}%", 1500)

    def zoom_in(self):
        """Zoom in by step"""
        current = self.get_current_zoom()
        self.set_zoom(current + self.zoom_step)

    def zoom_out(self):
        """Zoom out by step"""
        current = self.get_current_zoom()
        self.set_zoom(current - self.zoom_step)

    def zoom_reset(self):
        """Reset to default zoom"""
        self.set_zoom(self.default_zoom)
        self.browser.show_status("Zoom: Reset to 100%", 1500)


def setup_zoom(browser):
    """Set up zoom controls"""
    return ZoomManager(browser)
