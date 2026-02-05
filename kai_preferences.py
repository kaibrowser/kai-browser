"""
Kai Preferences
Handles saving and loading user preferences including module states
Uses OS keyring for secure API key storage
"""

import json
from pathlib import Path

try:
    import keyring

    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    print("⚠️  keyring not installed. API keys will not be stored securely.")
    print("   Install with: pip install keyring")


class KaiPreferences:
    """Manages persistent storage of browser preferences with secure API keys"""

    SERVICE_NAME = "kai_browser"

    SENSITIVE_KEYS = {
        "gemini_key",
        "claude_key",
        "openai_key",
        "api_key",
        "token",
        "password",
    }

    def __init__(self):
        self.data_dir = Path.home() / "kaibrowser"  ##".kai_browser"
        self.data_dir.mkdir(exist_ok=True)
        self.prefs_file = self.data_dir / "preferences.json"
        self.preferences = self._load_preferences()

    def _load_preferences(self):
        """Load preferences from disk"""
        if self.prefs_file.exists():
            try:
                with open(self.prefs_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Failed to load preferences: {e}")
                return self._default_preferences()
        return self._default_preferences()

    def _default_preferences(self):
        """Return default preferences structure"""
        return {"modules": {}, "dark_mode": {"enabled": False}}

    def _is_sensitive_key(self, key):
        """Check if a key contains sensitive data"""
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in self.SENSITIVE_KEYS)

    def _get_keyring_key(self, module_name, setting_key):
        """Generate keyring key name"""
        return f"{module_name}.{setting_key}"

    def save_preferences(self):
        """Save preferences to disk"""
        try:
            with open(self.prefs_file, "w", encoding="utf-8") as f:
                json.dump(self.preferences, f, indent=2)
            return True
        except Exception as e:
            print(f"⚠️  Failed to save preferences: {e}")
            return False

    def get_module_state(self, module_name):
        """Get the saved state for a module (enabled/disabled)"""
        return self.preferences["modules"].get(module_name, {}).get("enabled", True)

    def set_module_state(self, module_name, enabled):
        """Set the state for a module and save"""
        if module_name not in self.preferences["modules"]:
            self.preferences["modules"][module_name] = {}
        self.preferences["modules"][module_name]["enabled"] = enabled
        self.save_preferences()

    def get_module_setting(self, module_name, setting_key, default=None):
        """Get a specific setting for a module"""
        if self._is_sensitive_key(setting_key):
            if KEYRING_AVAILABLE:
                try:
                    value = keyring.get_password(
                        self.SERVICE_NAME,
                        self._get_keyring_key(module_name, setting_key),
                    )
                    return value if value else default
                except Exception as e:
                    print(f"⚠️  Keyring error: {e}")
                    return default
            else:
                return default

        return (
            self.preferences["modules"].get(module_name, {}).get(setting_key, default)
        )

    def set_module_setting(self, module_name, setting_key, value):
        """Set a specific setting for a module"""
        if module_name not in self.preferences["modules"]:
            self.preferences["modules"][module_name] = {}

        if self._is_sensitive_key(setting_key):
            if KEYRING_AVAILABLE:
                try:
                    if value:
                        keyring.set_password(
                            self.SERVICE_NAME,
                            self._get_keyring_key(module_name, setting_key),
                            str(value),
                        )
                    else:
                        keyring.delete_password(
                            self.SERVICE_NAME,
                            self._get_keyring_key(module_name, setting_key),
                        )
                except Exception as e:
                    print(f"⚠️  Keyring error: {e}")
            else:
                print(f"⚠️  Cannot store {setting_key} securely - keyring not available")
        else:
            self.preferences["modules"][module_name][setting_key] = value
            self.save_preferences()

    def get_dark_mode_enabled(self):
        """Get dark mode state"""
        return self.preferences["dark_mode"]["enabled"]

    def set_dark_mode_enabled(self, enabled):
        """Set dark mode state"""
        self.preferences["dark_mode"]["enabled"] = enabled
        self.save_preferences()

    def clear_sensitive_data(self):
        """Clear all API keys and sensitive data"""
        cleared = []

        if KEYRING_AVAILABLE:
            for module_name, module_data in self.preferences.get("modules", {}).items():
                if not isinstance(module_data, dict):
                    continue
                for key in list(module_data.keys()):
                    if self._is_sensitive_key(key):
                        try:
                            keyring.delete_password(
                                self.SERVICE_NAME,
                                self._get_keyring_key(module_name, key),
                            )
                            cleared.append(f"{module_name}.{key}")
                        except Exception:
                            pass

        if cleared:
            print(f"✓ Cleared {len(cleared)} sensitive keys")
        return cleared
