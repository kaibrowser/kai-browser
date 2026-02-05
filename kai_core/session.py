"""
Session Management - Save and restore browser tabs
"""


class SessionManager:
    """Handles saving and restoring browser sessions"""

    def __init__(self, browser, preferences):
        self.browser = browser
        self.preferences = preferences

    def save_session(self):
        """Save current tabs to preferences"""
        tab_urls = []
        for tab in self.browser.tabs:
            tab_urls.append(tab.get_url())

        self.preferences.set_module_setting("Browser", "tab_urls", tab_urls)
        self.preferences.set_module_setting(
            "Browser", "active_tab_index", self.browser.current_tab_index
        )
        print(f"✓ Saved session: {len(tab_urls)} tabs")

    def restore_session(self):
        """Restore tabs from previous session"""
        tab_urls = self.preferences.get_module_setting("Browser", "tab_urls", [])
        active_index = self.preferences.get_module_setting(
            "Browser", "active_tab_index", 0
        )

        if not tab_urls:
            print("ℹ️  No saved session found")
            return False

        # Restore tabs
        for url in tab_urls:
            self.browser.create_new_tab(url)

        # Restore active tab
        if 0 <= active_index < len(self.browser.tabs):
            self.browser.switch_to_tab(active_index)

        print(f"✓ Restored session: {len(tab_urls)} tabs, active: {active_index + 1}")
        return True
