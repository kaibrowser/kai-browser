"""
Context Menu - Right-click menu with common actions
"""

import webbrowser
from PyQt6.QtWidgets import QMenu, QApplication, QMessageBox
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineCore import QWebEnginePage


# Sites known to have issues with QtWebEngine
PROBLEM_SITES = [
    "paypal.com",
    "klarna.com",
    "stripe.com",
    "roblox.com",
    "signin.aws.amazon.com",
    "accounts.google.com",  # sometimes
]


class ContextMenuHandler:
    """Handles custom right-click context menu"""

    def __init__(self, browser):
        self.browser = browser
        self._connect_existing_tabs()

        # Load dismissed warnings from preferences
        self._load_dismissed_warnings()

        # Store original create_new_tab to wrap it
        self._original_create_tab = browser.create_new_tab
        browser.create_new_tab = self._wrapped_create_tab

        # Listen for URL changes to detect problem sites
        browser.url_changed.connect(self._check_problem_site)

    def _load_dismissed_warnings(self):
        """Load permanently dismissed warnings from preferences"""
        import json

        dismissed = self.browser.preferences.get_module_setting(
            "ContextMenu", "dismissed_warnings", "[]"
        )
        try:
            self._dismissed_warnings = set(json.loads(dismissed))
        except:
            self._dismissed_warnings = set()

    def _save_dismissed_warnings(self):
        """Save dismissed warnings to preferences"""
        import json

        self.browser.preferences.set_module_setting(
            "ContextMenu",
            "dismissed_warnings",
            json.dumps(list(self._dismissed_warnings)),
        )

    def _check_problem_site(self, url):
        """Check if URL is a known problem site and offer to open externally"""
        from PyQt6.QtWidgets import QCheckBox

        url_lower = url.lower()

        for site in PROBLEM_SITES:
            if site in url_lower:
                # Skip if permanently dismissed
                if site in self._dismissed_warnings:
                    return

                msg = QMessageBox(self.browser)
                msg.setWindowTitle("Compatibility Notice")
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setText(
                    f"This site ({site}) may not work correctly in kai browser due to advanced security checks."
                )
                msg.setInformativeText(
                    "Would you like to open it in your default browser instead?"
                )

                # Add "Don't show again" checkbox
                checkbox = QCheckBox("Don't show this warning again for this site")
                msg.setCheckBox(checkbox)

                open_btn = msg.addButton(
                    "Open in Default Browser", QMessageBox.ButtonRole.AcceptRole
                )
                stay_btn = msg.addButton("Stay Here", QMessageBox.ButtonRole.RejectRole)

                msg.exec()

                # Save preference if checkbox checked
                if checkbox.isChecked():
                    self._dismissed_warnings.add(site)
                    self._save_dismissed_warnings()

                if msg.clickedButton() == open_btn:
                    webbrowser.open(url)
                    # Go back or to homepage
                    web_view = self.browser.get_active_web_view()
                    if web_view and web_view.history().canGoBack():
                        web_view.back()
                    else:
                        self.browser.get_active_tab().navigate_to(
                            self.browser.settings_manager.get_homepage()
                        )
                return

    def _wrapped_create_tab(self, url=None):
        """Wrap tab creation to add context menu"""
        tab = self._original_create_tab(url)
        self._setup_tab_menu(tab)
        return tab

    def _connect_existing_tabs(self):
        """Connect context menu to existing tabs"""
        for tab in self.browser.tabs:
            self._setup_tab_menu(tab)

    def _setup_tab_menu(self, tab):
        """Setup context menu for a tab"""
        from PyQt6.QtCore import Qt

        web_view = tab.get_web_view()
        web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        try:
            web_view.customContextMenuRequested.disconnect()
        except:
            pass

        web_view.customContextMenuRequested.connect(
            lambda pos, wv=web_view: self.show_menu(pos, wv)
        )

    def show_menu(self, pos, web_view):
        """Show context menu at position"""
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

        # Back / Forward
        back_action = QAction("← Back", menu)
        back_action.setEnabled(web_view.history().canGoBack())
        back_action.triggered.connect(web_view.back)
        menu.addAction(back_action)

        forward_action = QAction("→ Forward", menu)
        forward_action.setEnabled(web_view.history().canGoForward())
        forward_action.triggered.connect(web_view.forward)
        menu.addAction(forward_action)

        reload_action = QAction("⟳ Reload", menu)
        reload_action.triggered.connect(web_view.reload)
        menu.addAction(reload_action)

        menu.addSeparator()

        # Copy current URL
        copy_url = QAction("📋 Copy page URL", menu)
        copy_url.triggered.connect(
            lambda: self.copy_to_clipboard(web_view.url().toString())
        )
        menu.addAction(copy_url)

        # Open in default browser
        open_external = QAction("↗ Open in default browser", menu)
        open_external.triggered.connect(
            lambda: webbrowser.open(web_view.url().toString())
        )
        menu.addAction(open_external)

        menu.addSeparator()

        # Undo
        undo_action = QAction("↩ Undo", menu)
        undo_action.triggered.connect(
            lambda: web_view.page().triggerAction(QWebEnginePage.WebAction.Undo)
        )
        menu.addAction(undo_action)

        # Redo
        redo_action = QAction("↪ Redo", menu)
        redo_action.triggered.connect(
            lambda: web_view.page().triggerAction(QWebEnginePage.WebAction.Redo)
        )
        menu.addAction(redo_action)

        menu.addSeparator()

        # Cut
        cut_action = QAction("✂️ Cut", menu)
        cut_action.triggered.connect(
            lambda: web_view.page().triggerAction(QWebEnginePage.WebAction.Cut)
        )
        menu.addAction(cut_action)

        # Copy
        copy_action = QAction("📋 Copy", menu)
        copy_action.triggered.connect(
            lambda: web_view.page().triggerAction(QWebEnginePage.WebAction.Copy)
        )
        menu.addAction(copy_action)

        # Paste
        paste_action = QAction("📝 Paste", menu)
        paste_action.triggered.connect(
            lambda: web_view.page().triggerAction(QWebEnginePage.WebAction.Paste)
        )
        menu.addAction(paste_action)

        menu.addSeparator()

        # Select all
        select_all = QAction("Select all", menu)
        select_all.triggered.connect(
            lambda: web_view.page().triggerAction(QWebEnginePage.WebAction.SelectAll)
        )
        menu.addAction(select_all)

        menu.addSeparator()

        # View source
        view_source = QAction("View page source", menu)
        view_source.triggered.connect(lambda: self.view_source(web_view))
        menu.addAction(view_source)

        # Show menu
        menu.exec(web_view.mapToGlobal(pos))

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.browser.show_status("Copied to clipboard", 1500)

    def view_source(self, web_view):
        """View page source in new tab"""

        def callback(html):
            # Create a data URL with the source
            import html as html_module

            escaped = html_module.escape(html)
            source_html = f"""
            <html><head><title>Source</title>
            <style>
                body {{ font-family: monospace; white-space: pre-wrap; padding: 20px; background: #1e1e1e; color: #d4d4d4; }}
            </style></head>
            <body>{escaped}</body></html>
            """
            new_tab = self.browser.create_new_tab()
            new_tab.get_web_view().setHtml(source_html)

        web_view.page().toHtml(callback)


def setup_context_menu(browser):
    """Set up context menu handler"""
    return ContextMenuHandler(browser)
