"""
Security Indicator - Chrome-style padlock in URL bar
Shows HTTPS/HTTP status with certificate details popup
"""

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDialog,
    QVBoxLayout,
    QFrame,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QCursor


class SecurityIndicator(QPushButton):
    """Padlock icon that shows security status"""

    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.current_url = ""
        self.is_secure = False

        self.setFixedSize(28, 28)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.clicked.connect(self.show_security_popup)

        # Listen for URL changes
        browser.url_changed.connect(self.on_url_changed)

        # Listen for tab switches
        browser.tab_changed.connect(self.on_tab_changed)

        # Set initial state
        self._update_indicator("")

    def on_tab_changed(self, index):
        """Update indicator when switching tabs"""
        active_tab = self.browser.get_active_tab()
        if active_tab:
            url = active_tab.get_url()
            self.current_url = url
            self._update_indicator(url)

    def on_url_changed(self, url):
        """Update indicator when URL changes"""
        self.current_url = url
        self._update_indicator(url)

    def _update_indicator(self, url):
        """Update icon based on URL scheme"""
        if url.startswith("https://"):
            self.is_secure = True
            self.setText("🔒")
            self.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 14px;
                    color: #5c5c5c;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: #e8e8e8;
                    border-radius: 4px;
                }
            """
            )
        elif url.startswith("http://"):
            self.is_secure = False
            self.setText("⚠️")
            self.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 14px;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: #e8e8e8;
                    border-radius: 4px;
                }
            """
            )
        else:
            # Local files, about:, data:, etc.
            self.is_secure = None
            self.setText("ℹ️")
            self.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 14px;
                    color: #888;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: #e8e8e8;
                    border-radius: 4px;
                }
            """
            )

    def show_security_popup(self):
        """Show security details popup"""
        dialog = SecurityPopup(self.browser, self.current_url, self.is_secure, self)

        # Position below the indicator
        pos = self.mapToGlobal(self.rect().bottomLeft())
        dialog.move(pos.x(), pos.y() + 5)
        dialog.exec()


class SecurityPopup(QDialog):
    """Chrome-style security popup"""

    def __init__(self, browser, url, is_secure, parent=None):
        super().__init__(parent)
        self.browser = browser
        self.url = url
        self.is_secure = is_secure

        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setFixedWidth(320)
        self.setStyleSheet(
            """
            QDialog {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
        """
        )

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header section
        header = QFrame()
        header.setStyleSheet(
            """
            QFrame {
                background-color: #fafafa;
                border-bottom: 1px solid #eee;
                border-radius: 8px 8px 0 0;
                padding: 16px;
            }
        """
        )
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(8)

        # Security status with icon
        status_layout = QHBoxLayout()
        status_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setFixedSize(24, 24)

        status_text = QLabel()
        status_text.setWordWrap(True)

        if self.is_secure is True:
            icon_label.setText("🔒")
            icon_label.setStyleSheet("font-size: 18px;")
            status_text.setText("<b>Connection is secure</b>")
            status_text.setStyleSheet("color: #1a7f37; font-size: 14px;")
        elif self.is_secure is False:
            icon_label.setText("⚠️")
            icon_label.setStyleSheet("font-size: 18px;")
            status_text.setText("<b>Connection is not secure</b>")
            status_text.setStyleSheet("color: #d73a49; font-size: 14px;")
        else:
            icon_label.setText("ℹ️")
            icon_label.setStyleSheet("font-size: 18px;")
            status_text.setText("<b>Site information</b>")
            status_text.setStyleSheet("color: #666; font-size: 14px;")

        status_layout.addWidget(icon_label)
        status_layout.addWidget(status_text, 1)
        header_layout.addLayout(status_layout)

        # Domain
        if self.url:
            try:
                qurl = QUrl(self.url)
                domain = qurl.host()
                if domain:
                    domain_label = QLabel(domain)
                    domain_label.setStyleSheet("color: #666; font-size: 12px;")
                    header_layout.addWidget(domain_label)
            except:
                pass

        layout.addWidget(header)

        # Details section
        details = QFrame()
        details.setStyleSheet(
            """
            QFrame {
                background-color: white;
                padding: 16px;
            }
        """
        )
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(16, 16, 16, 16)
        details_layout.setSpacing(12)

        if self.is_secure is True:
            # Secure connection info
            info = QLabel(
                "Your information (for example, passwords or credit card numbers) "
                "is private when it is sent to this site."
            )
            info.setWordWrap(True)
            info.setStyleSheet("color: #444; font-size: 12px; line-height: 1.4;")
            details_layout.addWidget(info)

            # Certificate info
            cert_info = self._get_certificate_info()
            if cert_info:
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.HLine)
                separator.setStyleSheet("background-color: #eee;")
                details_layout.addWidget(separator)

                cert_label = QLabel(f"<b>Certificate</b><br>{cert_info}")
                cert_label.setWordWrap(True)
                cert_label.setStyleSheet("color: #666; font-size: 11px;")
                details_layout.addWidget(cert_label)

        elif self.is_secure is False:
            # Insecure connection warning
            warning = QLabel(
                "⚠️ You should not enter any sensitive information on this site "
                "(for example, passwords or credit cards), because it could be "
                "stolen by attackers."
            )
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #b35900; font-size: 12px; line-height: 1.4;")
            details_layout.addWidget(warning)

        else:
            # Other (local file, about:, etc.)
            info = QLabel("This page is loaded from a local or internal source.")
            info.setWordWrap(True)
            info.setStyleSheet("color: #666; font-size: 12px;")
            details_layout.addWidget(info)

        layout.addWidget(details)

    def _get_certificate_info(self):
        """Try to get certificate issuer info"""
        # PyQt6 WebEngine has limited certificate access
        # We can show basic info based on common issuers

        if not self.url:
            return None

        try:
            qurl = QUrl(self.url)
            host = qurl.host()

            # For now, return generic info
            # Full certificate inspection would require
            # intercepting SSL handshake which is complex
            return f"Issued for: {host}"
        except:
            return None


def setup_security_indicator(browser):
    """Create and return security indicator widget"""
    return SecurityIndicator(browser)
