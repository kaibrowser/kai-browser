"""
Profile Management - Persistent storage for browser data
"""

from pathlib import Path
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineScript,
    QWebEnginePage,
)
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QUrl

SCROLLBAR_CSS = """
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 5px;
        border: 2px solid transparent;
        background-clip: padding-box;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #a1a1a1;
        border: 2px solid transparent;
        background-clip: padding-box;
    }
    ::-webkit-scrollbar-corner {
        background: transparent;
    }
"""


def setup_persistent_profile():
    """Set up persistent profile for cookies/cache (shared across tabs)"""
    data_dir = Path.home() / "kaibrowser"  ##".kai_browser"
    data_dir.mkdir(exist_ok=True)

    profile_path = str(data_dir / "profile")
    profile = QWebEngineProfile("kaiProfile")
    profile.setPersistentStoragePath(profile_path)

    cache_path = str(data_dir / "cache")
    profile.setCachePath(cache_path)

    profile.setPersistentCookiesPolicy(
        QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
    )

    # Enable all necessary web features
    settings = profile.settings()

    # Clipboard access
    settings.setAttribute(
        QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True
    )
    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)

    # Local storage
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)

    # JavaScript
    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

    # WebGL
    settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

    # Accelerated 2D canvas
    settings.setAttribute(
        QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True
    )

    # Plugins
    settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)

    # DNS prefetching
    settings.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, True)

    # Focus on navigation
    settings.setAttribute(
        QWebEngineSettings.WebAttribute.FocusOnNavigationEnabled, True
    )

    # Modern scrollbar injection
    scrollbar_script = QWebEngineScript()
    scrollbar_script.setName("modern-scrollbar")
    scrollbar_script.setSourceCode(
        f"""
        (function() {{
            const style = document.createElement('style');
            style.textContent = `{SCROLLBAR_CSS}`;
            if (document.head) {{
                document.head.appendChild(style);
            }} else {{
                document.addEventListener('DOMContentLoaded', function() {{
                    document.head.appendChild(style);
                }});
            }}
        }})();
        """
    )
    scrollbar_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
    scrollbar_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    scrollbar_script.setRunsOnSubFrames(True)

    profile.scripts().insert(scrollbar_script)

    print(f"✓ Browser data will be stored in: {data_dir}")
    print(f"✓ Clipboard access enabled")
    print(f"✓ Modern scrollbar enabled")
    print(f"✓ WebRTC permissions enabled")

    return profile


def setup_page_permissions(page, preferences):
    """Set up permission handling for a web page"""

    def handle_feature_permission(origin: QUrl, feature):
        """Handle camera/microphone/other permission requests"""

        print(f"🔔 Permission request detected!")
        print(f"   Origin: {origin.toString()}")
        print(f"   Feature: {feature}")

        # Get the domain for this origin
        domain = origin.host() or "localhost"

        # Feature names for display
        feature_names = {
            QWebEnginePage.Feature.MediaAudioCapture: "microphone",
            QWebEnginePage.Feature.MediaVideoCapture: "camera",
            QWebEnginePage.Feature.MediaAudioVideoCapture: "camera and microphone",
            QWebEnginePage.Feature.Geolocation: "location",
            QWebEnginePage.Feature.DesktopVideoCapture: "screen sharing",
            QWebEnginePage.Feature.DesktopAudioVideoCapture: "screen and audio sharing",
        }

        feature_name = feature_names.get(feature, "this feature")

        # Check if we have a saved permission for this domain + feature
        pref_key = f"permission_{domain}_{feature.value}"
        saved_permission = preferences.get_module_setting(
            "BrowserPermissions", pref_key, None
        )

        if saved_permission == "granted":
            page.setFeaturePermission(
                origin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )
            return
        elif saved_permission == "denied":
            page.setFeaturePermission(
                origin, feature, QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
            )
            return

        # No saved permission - ask the user
        reply = QMessageBox.question(
            None,
            "Permission Request",
            f"{domain} wants to access your {feature_name}.\n\nAllow?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            page.setFeaturePermission(
                origin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )
            # Save the permission for next time
            preferences.set_module_setting("BrowserPermissions", pref_key, "granted")
        else:
            page.setFeaturePermission(
                origin, feature, QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
            )
            # Save the denial for next time
            preferences.set_module_setting("BrowserPermissions", pref_key, "denied")

    # Connect the permission request signal
    page.featurePermissionRequested.connect(handle_feature_permission)


def clear_profile_data(profile):
    """Clear all stored browsing data"""
    profile.clearAllVisitedLinks()
    profile.cookieStore().deleteAllCookies()
    print("✓ Browser data cleared")


def clear_permissions(preferences):
    """Clear all saved permission grants"""
    # Get all stored settings
    settings = preferences.get_all_module_settings("BrowserPermissions")

    # Remove all permission settings
    for key in list(settings.keys()):
        if key.startswith("permission_"):
            preferences.remove_module_setting("BrowserPermissions", key)

    print("✓ Permissions cleared")
