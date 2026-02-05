"""
Settings - Centralized settings registry with auto-generated UI
Easy to extend: just add new entries to SETTINGS dict
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QTabWidget,
    QWidget,
    QFormLayout,
    QMessageBox,
    QScrollArea,
    QFrame,
)
from PyQt6.QtCore import Qt
from history import HistoryManagerWidget
from updater import check_for_updates


# ============================================================================
# SETTINGS REGISTRY - Add new settings here
# ============================================================================

SETTINGS = {
    # General
    "homepage": {
        "default": "https://www.google.com",
        "label": "Homepage",
        "type": "text",
        "category": "General",
        "description": "Page to load on startup and new tabs",
    },
    "search_engine": {
        "default": "google",
        "label": "Search Engine",
        "type": "dropdown",
        "options": [
            ("google", "Google"),
            ("duckduckgo", "DuckDuckGo"),
            ("bing", "Bing"),
            ("brave", "Brave Search"),
        ],
        "category": "General",
        "description": "Default search engine for address bar",
    },
    "restore_session": {
        "default": True,
        "label": "Restore tabs on startup",
        "type": "toggle",
        "category": "General",
        "description": "Reopen your tabs from last session",
    },
    # Privacy
    "clear_data_on_exit": {
        "default": False,
        "label": "Clear data on exit",
        "type": "toggle",
        "category": "Privacy",
        "description": "Clear cookies and cache when closing browser",
    },
    # Actions (buttons, not stored values)
    "clear_browsing_data": {
        "label": "Clear Browsing Data",
        "type": "button",
        "category": "Privacy",
        "action": "clear_data",
        "description": "Clear cookies, cache, and history now",
    },
    # Updates
    "check_updates": {
        "label": "Check for Updates",
        "type": "button",
        "category": "Updates",
        "action": "check_updates",
        "description": "Check if a new version is available",
    },
}

# Search engine URL patterns
SEARCH_URLS = {
    "google": "https://www.google.com/search?q={}",
    "duckduckgo": "https://duckduckgo.com/?q={}",
    "bing": "https://www.bing.com/search?q={}",
    "brave": "https://search.brave.com/search?q={}",
}


# ============================================================================
# SETTINGS MANAGER - Read/write settings
# ============================================================================


class SettingsManager:
    """Manages reading and writing settings"""

    def __init__(self, preferences):
        self.preferences = preferences

    def get(self, key):
        """Get a setting value"""
        if key not in SETTINGS:
            return None

        setting = SETTINGS[key]
        if setting["type"] == "button":
            return None

        return self.preferences.get_module_setting(
            "BrowserSettings", key, setting["default"]
        )

    def set(self, key, value):
        """Set a setting value"""
        if key not in SETTINGS:
            return

        self.preferences.set_module_setting("BrowserSettings", key, value)

    def get_search_url(self, query):
        """Get search URL for current search engine"""
        engine = self.get("search_engine")
        url_pattern = SEARCH_URLS.get(engine, SEARCH_URLS["google"])
        return url_pattern.format(query.replace(" ", "+"))

    def get_homepage(self):
        """Get homepage URL"""
        return self.get("homepage") or "https://www.google.com"


# ============================================================================
# SETTINGS DIALOG - Auto-generated from registry
# ============================================================================


class SettingsDialog(QDialog):
    """Settings dialog - auto-generates UI from SETTINGS registry"""

    def __init__(self, browser, parent=None):
        super().__init__(parent or browser)
        self.browser = browser
        self.settings_manager = SettingsManager(browser.preferences)
        self.widgets = {}

        self.setWindowTitle("Settings")
        self.setMinimumSize(450, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Group settings by category
        categories = {}
        for key, setting in SETTINGS.items():
            cat = setting.get("category", "General")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((key, setting))

        # Create tabs for categories
        tabs = QTabWidget()
        tabs.setStyleSheet(
            """
            QTabWidget::pane {
                border: none;
                background: white;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
                background: #f1f5f9;
                border: none;
                border-radius: 4px 4px 0 0;
            }
            QTabBar::tab:selected {
                background: white;
            }
        """
        )

        for category, settings_list in categories.items():
            tab = self._create_category_tab(settings_list)
            tabs.addTab(tab, category)

        # Add History tab
        history_tab = self._create_history_tab()
        tabs.addTab(history_tab, "History")

        layout.addWidget(tabs)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(16, 8, 16, 16)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            """
            QPushButton {
                background: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 8px 20px;
                color: #64748b;
            }
            QPushButton:hover {
                background: #e2e8f0;
            }
        """
        )
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(
            """
            QPushButton {
                background: #7c3aed;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #6d28d9;
            }
        """
        )
        save_btn.clicked.connect(self.save_and_close)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _create_category_tab(self, settings_list):
        """Create a tab for a category of settings"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        form = QFormLayout(content)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(16)

        for key, setting in settings_list:
            widget = self._create_setting_widget(key, setting)
            if widget:
                # Create label with description
                label_text = setting["label"]
                label = QLabel(label_text)
                label.setStyleSheet("font-weight: 500;")

                # Add description if exists
                if "description" in setting:
                    desc = QLabel(setting["description"])
                    desc.setStyleSheet("color: #64748b; font-size: 11px;")

                    label_container = QWidget()
                    label_layout = QVBoxLayout(label_container)
                    label_layout.setContentsMargins(0, 0, 0, 0)
                    label_layout.setSpacing(2)
                    label_layout.addWidget(label)
                    label_layout.addWidget(desc)

                    form.addRow(label_container, widget)
                else:
                    form.addRow(label, widget)

        scroll.setWidget(content)
        return scroll

    def _create_setting_widget(self, key, setting):
        """Create appropriate widget for setting type"""
        setting_type = setting["type"]

        if setting_type == "text":
            widget = QLineEdit()
            widget.setText(str(self.settings_manager.get(key) or ""))
            widget.setStyleSheet(
                """
                QLineEdit {
                    padding: 8px;
                    border: 1px solid #e2e8f0;
                    border-radius: 4px;
                }
                QLineEdit:focus {
                    border-color: #7c3aed;
                }
            """
            )
            self.widgets[key] = widget
            return widget

        elif setting_type == "dropdown":
            widget = QComboBox()
            current_value = self.settings_manager.get(key)
            for i, (value, label) in enumerate(setting["options"]):
                widget.addItem(label, value)
                if value == current_value:
                    widget.setCurrentIndex(i)
            widget.setStyleSheet(
                """
                QComboBox {
                    padding: 8px;
                    border: 1px solid #e2e8f0;
                    border-radius: 4px;
                }
            """
            )
            self.widgets[key] = widget
            return widget

        elif setting_type == "toggle":
            widget = QCheckBox()
            widget.setChecked(bool(self.settings_manager.get(key)))
            self.widgets[key] = widget
            return widget

        elif setting_type == "button":
            widget = QPushButton(setting["label"])
            widget.setStyleSheet(
                """
                QPushButton {
                    background: #ef4444;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background: #dc2626;
                }
            """
            )
            action = setting.get("action")
            if action == "clear_data":
                widget.clicked.connect(self._clear_browsing_data)
            elif action == "check_updates":
                widget.clicked.connect(self._check_for_updates)
            return widget

        return None

    def _clear_browsing_data(self):
        """Clear browsing data action"""
        reply = QMessageBox.question(
            self,
            "Clear Browsing Data",
            "This will clear all cookies, cache, and history.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.browser.clear_browsing_data()
            QMessageBox.information(self, "Done", "Browsing data cleared.")

    def _check_for_updates(self):
        """Check for updates action"""
        check_for_updates(self.browser, silent=False)

    def _create_history_tab(self):
        """Create history management tab"""
        return HistoryManagerWidget(self.browser)

    def save_and_close(self):
        """Save all settings and close"""
        for key, widget in self.widgets.items():
            setting = SETTINGS[key]

            if setting["type"] == "text":
                self.settings_manager.set(key, widget.text())
            elif setting["type"] == "dropdown":
                self.settings_manager.set(key, widget.currentData())
            elif setting["type"] == "toggle":
                self.settings_manager.set(key, widget.isChecked())

        self.browser.show_status("✓ Settings saved", 2000)
        self.accept()


def show_settings_dialog(browser):
    """Show the settings dialog"""
    dialog = SettingsDialog(browser)
    dialog.exec()
