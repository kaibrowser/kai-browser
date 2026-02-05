"""
Extension Builder - AI Settings Tab with Model Selection
Configure AI providers, API keys, and choose specific models
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QMessageBox,
    QFrame,
    QGroupBox,
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import Qt


class SettingsTab(QWidget):
    """AI provider settings tab with model selection"""

    # Signal emitted when settings change
    settings_changed = pyqtSignal()

    def __init__(self, browser_core, ai_manager):
        super().__init__()
        self.browser_core = browser_core
        self.ai_manager = ai_manager

        self.setup_ui()

    def setup_ui(self):
        """Set up the settings interface"""
        layout = QVBoxLayout()

        # Info box
        info_box = QLabel(
            "🔑 Configure AI providers and select models\n\n"
            "Available Providers: Gemini, Claude, OpenAI"
        )
        info_box.setStyleSheet(
            """
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 15px;
                font-size: 12px;
            }
        """
        )
        info_box.setWordWrap(True)
        layout.addWidget(info_box)

        # Active provider status (read-only)
        self.status_label = QLabel()
        self.status_label.setStyleSheet(
            "padding: 10px; font-size: 13px; font-weight: bold;"
        )
        layout.addWidget(self.status_label)

        # Spacer
        layout.addSpacing(15)

        # ==================== GEMINI SETTINGS ====================
        gemini_group = QGroupBox("Gemini Settings")
        gemini_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        gemini_layout = QVBoxLayout()

        # API Key
        gemini_layout.addLayout(self._create_key_row("Gemini", "gemini"))

        # Model Selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))

        self.gemini_model_combo = QComboBox()
        self._populate_model_combo("gemini", self.gemini_model_combo)

        self.gemini_model_combo.currentIndexChanged.connect(
            lambda: self.on_model_changed(
                "gemini", self.gemini_model_combo, auto_switch=True
            )
        )

        self.gemini_model_combo.activated.connect(
            lambda: self.switch_to_provider("gemini")
        )

        model_layout.addWidget(self.gemini_model_combo, 1)
        gemini_layout.addLayout(model_layout)

        gemini_group.setLayout(gemini_layout)
        layout.addWidget(gemini_group)

        # ==================== CLAUDE SETTINGS ====================
        claude_group = QGroupBox("Claude Settings")
        claude_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        claude_layout = QVBoxLayout()

        # API Key
        claude_layout.addLayout(self._create_key_row("Claude", "claude"))

        # Model Selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))

        self.claude_model_combo = QComboBox()
        self._populate_model_combo("claude", self.claude_model_combo)

        self.claude_model_combo.currentIndexChanged.connect(
            lambda: self.on_model_changed(
                "claude", self.claude_model_combo, auto_switch=True
            )
        )

        self.claude_model_combo.activated.connect(
            lambda: self.switch_to_provider("claude")
        )

        model_layout.addWidget(self.claude_model_combo, 1)
        claude_layout.addLayout(model_layout)

        claude_group.setLayout(claude_layout)
        layout.addWidget(claude_group)

        # ==================== OPENAI SETTINGS ====================
        openai_group = QGroupBox("OpenAI Settings")
        openai_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        openai_layout = QVBoxLayout()

        # API Key
        openai_layout.addLayout(self._create_key_row("OpenAI", "openai"))

        # Model Selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))

        self.openai_model_combo = QComboBox()
        self._populate_model_combo("openai", self.openai_model_combo)

        self.openai_model_combo.currentIndexChanged.connect(
            lambda: self.on_model_changed(
                "openai", self.openai_model_combo, auto_switch=True
            )
        )

        self.openai_model_combo.activated.connect(
            lambda: self.switch_to_provider("openai")
        )

        model_layout.addWidget(self.openai_model_combo, 1)
        openai_layout.addLayout(model_layout)

        openai_group.setLayout(openai_layout)
        layout.addWidget(openai_group)

        layout.addStretch()

        # Links (open in KaiBrowser)
        links_label = QLabel("Get API Keys:")
        links_label.setStyleSheet("font-weight: bold; padding-top: 10px;")
        layout.addWidget(links_label)

        # Create clickable links that open in browser tabs
        links_layout = QHBoxLayout()

        gemini_link = QPushButton("Gemini")
        gemini_link.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                color: #7c3aed;
                text-decoration: underline;
                padding: 5px;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #6d28d9;
            }
        """
        )
        gemini_link.setCursor(Qt.CursorShape.PointingHandCursor)
        gemini_link.clicked.connect(
            lambda: self.browser_core.create_new_tab(
                "https://makersuite.google.com/app/apikey"
            )
        )
        links_layout.addWidget(gemini_link)

        links_layout.addWidget(QLabel("•"))

        claude_link = QPushButton("Claude")
        claude_link.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                color: #7c3aed;
                text-decoration: underline;
                padding: 5px;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #6d28d9;
            }
        """
        )
        claude_link.setCursor(Qt.CursorShape.PointingHandCursor)
        claude_link.clicked.connect(
            lambda: self.browser_core.create_new_tab("https://console.anthropic.com/")
        )
        links_layout.addWidget(claude_link)

        links_layout.addWidget(QLabel("•"))

        openai_link = QPushButton("OpenAI")
        openai_link.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                color: #7c3aed;
                text-decoration: underline;
                padding: 5px;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #6d28d9;
            }
        """
        )
        openai_link.setCursor(Qt.CursorShape.PointingHandCursor)
        openai_link.clicked.connect(
            lambda: self.browser_core.create_new_tab(
                "https://platform.openai.com/api-keys"
            )
        )
        links_layout.addWidget(openai_link)

        links_layout.addStretch()
        layout.addLayout(links_layout)

        self.setLayout(layout)
        self.update_status()

    def _populate_model_combo(self, provider, combo_box):
        """Populate model dropdown based on whether API key exists"""
        combo_box.clear()

        # Check if API key exists for this provider
        existing_key = self.browser_core.preferences.get_module_setting(
            "AIProviders", f"{provider}_key"
        )

        if not existing_key:
            # No key: show placeholder and disable
            combo_box.addItem("⚠️ Enter API key first", None)
            combo_box.setEnabled(False)
            combo_box.setStyleSheet("QComboBox { color: #999; }")
        else:
            # Key exists: populate models and enable
            combo_box.setEnabled(True)
            combo_box.setStyleSheet("")

            provider_obj = self.ai_manager.get_provider(provider)
            if provider_obj:
                for model_id, model_name in provider_obj.get_available_models():
                    combo_box.addItem(model_name, model_id)
            else:
                # Fallback models if provider not initialized
                if provider == "gemini":
                    combo_box.addItem(
                        "Gemini 2.0 Flash (Experimental)", "gemini-2.0-flash-exp"
                    )
                    combo_box.addItem("Gemini 1.5 Pro", "gemini-1.5-pro")
                elif provider == "claude":
                    combo_box.addItem(
                        "Claude Sonnet 4 (Latest)", "claude-sonnet-4-20250514"
                    )
                    combo_box.addItem("Claude Sonnet 4.5 (Newest)", "claude-sonnet-4-5")
                elif provider == "openai":
                    combo_box.addItem("GPT-4 Turbo", "gpt-4-turbo")
                    combo_box.addItem("GPT-4o", "gpt-4o")

            # Set current model if key exists
            current_model = self.browser_core.preferences.get_module_setting(
                "AIProviders", f"{provider}_model", ""
            )
            if current_model:
                index = combo_box.findData(current_model)
                if index >= 0:
                    combo_box.setCurrentIndex(index)

    def _create_key_row(self, name, provider_key):
        """Create API key input row"""
        row_layout = QHBoxLayout()

        # Label
        label = QLabel(f"API Key:")
        label.setFixedWidth(80)
        row_layout.addWidget(label)

        # Input
        key_input = QLineEdit()
        key_input.setPlaceholderText(f"Enter {name} API key")
        key_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Check if key exists
        existing_key = self.browser_core.preferences.get_module_setting(
            "AIProviders", f"{provider_key}_key"
        )

        if existing_key:
            key_input.setPlaceholderText("••••••••" + existing_key[-4:])

        row_layout.addWidget(key_input, 1)

        # Save button
        save_btn = QPushButton("Save")
        save_btn.setFixedWidth(80)
        save_btn.clicked.connect(lambda: self.save_key(provider_key, key_input))
        row_layout.addWidget(save_btn)

        # Delete button
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedWidth(40)
        delete_btn.clicked.connect(lambda: self.delete_key(provider_key, key_input))
        row_layout.addWidget(delete_btn)

        # Status indicator
        status = QLabel()
        status.setFixedWidth(120)
        if existing_key:
            status.setText("✅ Configured")
            status.setStyleSheet("color: green; font-size: 11px;")
        else:
            status.setText("⚠️ Not set")
            status.setStyleSheet("color: orange; font-size: 11px;")
        row_layout.addWidget(status)

        # Store references
        setattr(self, f"{provider_key}_input", key_input)
        setattr(self, f"{provider_key}_status", status)

        return row_layout

    def save_key(self, provider, input_widget):
        """Save API key"""
        key = input_widget.text().strip()

        if not key:
            QMessageBox.warning(self, "Empty Key", "Please enter an API key!")
            return

        # Save
        self.ai_manager.set_api_key(provider, key)

        # Update UI
        input_widget.clear()
        input_widget.setPlaceholderText("••••••••" + key[-4:])

        status = getattr(self, f"{provider}_status")
        status.setText("✅ Configured")
        status.setStyleSheet("color: green; font-size: 11px;")

        # Re-populate the model dropdown now that key exists
        if provider == "gemini":
            self._populate_model_combo("gemini", self.gemini_model_combo)
        elif provider == "claude":
            self._populate_model_combo("claude", self.claude_model_combo)
        elif provider == "openai":
            self._populate_model_combo("openai", self.openai_model_combo)

        self.update_status()
        self.settings_changed.emit()

        self.browser_core.show_status(f"💾 {provider.title()} key saved", 2000)

    def delete_key(self, provider, input_widget):
        """Delete API key"""
        existing_key = self.browser_core.preferences.get_module_setting(
            "AIProviders", f"{provider}_key"
        )

        if not existing_key:
            return

        reply = QMessageBox.question(
            self,
            "Delete Key?",
            f"Delete {provider.title()} API key?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.ai_manager.set_api_key(provider, "")

            input_widget.clear()
            input_widget.setPlaceholderText(f"Enter {provider.title()} API key")

            status = getattr(self, f"{provider}_status")
            status.setText("⚠️ Not set")
            status.setStyleSheet("color: orange; font-size: 11px;")

            # Disable and clear the model dropdown
            if provider == "gemini":
                self._populate_model_combo("gemini", self.gemini_model_combo)
            elif provider == "claude":
                self._populate_model_combo("claude", self.claude_model_combo)
            elif provider == "openai":
                self._populate_model_combo("openai", self.openai_model_combo)

            self.update_status()
            self.settings_changed.emit()

            self.browser_core.show_status(f"🗑️ {provider.title()} key deleted", 2000)

    def switch_to_provider(self, provider):
        """Switch to a provider immediately (called when dropdown is activated)"""
        current_provider = self.browser_core.preferences.get_module_setting(
            "AIProviders", "selected_provider", "gemini"
        )

        # Only switch if it's a different provider and has a valid key
        existing_key = self.browser_core.preferences.get_module_setting(
            "AIProviders", f"{provider}_key"
        )

        if not existing_key:
            return  # Don't switch if no key

        if provider != current_provider:
            self.ai_manager.set_selected_provider(provider)

            # Get the model name for display
            if provider == "gemini":
                model_name = self.gemini_model_combo.currentText()
            elif provider == "claude":
                model_name = self.claude_model_combo.currentText()
            elif provider == "openai":
                model_name = self.openai_model_combo.currentText()
            else:
                model_name = "Unknown"

            self.browser_core.show_status(
                f"✅ Switched to {provider.title()}: {model_name}", 2000
            )
            self.update_status()
            self.settings_changed.emit()

    def on_model_changed(self, provider, combo_box, auto_switch=False):
        """Handle model selection change"""
        model = combo_box.currentData()
        if model:
            self.ai_manager.set_model(provider, model)
            model_name = combo_box.currentText()

            # Auto-switch to this provider when model is changed
            if auto_switch:
                self.ai_manager.set_selected_provider(provider)
                self.browser_core.show_status(
                    f"✅ Switched to {provider.title()}: {model_name}", 2000
                )
            else:
                self.browser_core.show_status(
                    f"📝 {provider.title()} model: {model_name}", 2000
                )

            self.update_status()
            self.settings_changed.emit()

    def update_status(self):
        """Update status message"""
        current_provider = self.browser_core.preferences.get_module_setting(
            "AIProviders", "selected_provider", "gemini"
        )

        provider_key = self.browser_core.preferences.get_module_setting(
            "AIProviders", f"{current_provider}_key"
        )

        current_model = self.browser_core.preferences.get_module_setting(
            "AIProviders", f"{current_provider}_model", "default"
        )

        provider_names = {"gemini": "Gemini", "claude": "Claude", "openai": "OpenAI"}

        name = provider_names.get(current_provider, current_provider.title())

        if provider_key:
            # Get friendly model name
            if current_provider == "gemini" and hasattr(self, "gemini_model_combo"):
                model_text = self.gemini_model_combo.currentText()
            elif current_provider == "claude" and hasattr(self, "claude_model_combo"):
                model_text = self.claude_model_combo.currentText()
            elif current_provider == "openai" and hasattr(self, "openai_model_combo"):
                model_text = self.openai_model_combo.currentText()
            else:
                model_text = current_model

            self.status_label.setText(f"✅ {name} is ready ({model_text})")
            self.status_label.setStyleSheet(
                "color: green; font-weight: bold; padding: 5px;"
            )
        else:
            self.status_label.setText(f"⚠️ {name} selected but no API key set")
            self.status_label.setStyleSheet(
                "color: orange; font-weight: bold; padding: 5px;"
            )
