"""
AI Examples - Lean prompt building
Instructions-only approach with minimal structural skeleton
"""


class AIExamples:

    SKELETON = """
class PluginName:
    def __init__(self, browser):
        self.browser = browser
        # Optional persistence:
        # data_dir = Path.home() / "kaibrowser" / "extensions" / self.__class__.__name__
        # data_dir.mkdir(parents=True, exist_ok=True)
        # self.data_file = data_dir / "data.json"

    def activate(self):
        btn = QToolButton()
        btn.setText("Label")
        btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu()
        action = QAction("Item", menu)
        action.triggered.connect(self.on_action)
        menu.addAction(action)
        btn.setMenu(menu)
        self.browser.toolbar.addWidget(btn)

    def on_action(self):
        web_view = self.browser.get_active_web_view()
        if not web_view:
            return

    # Correct persistence pattern:
    def load_data(self):
        if self.data_file.exists():
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_data(self, data):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        # NOTE: encoding='utf-8' belongs on open() only, never on json.dump()
"""

    PLUGIN_RULES = """PLUGIN RULES:
- Class with __init__(self, browser) and activate(self) methods
- browser.toolbar = QToolBar, browser.get_active_web_view() = QWebEngineView
- Navigate: browser.get_active_web_view().setUrl(QUrl(url))
- Always use get_active_web_view(), never browser.web_view directly
- Data persistence: Path.home() / "kaibrowser" / "extensions" / ClassName / "data.json"
- NEVER create folders outside of this path (no ~/kaibrowser/archives, ~/kaibrowser/data etc)
- encoding='utf-8' goes on open() only — never pass it to json.dump()

CRITICAL PYQT6:
- QAction → PyQt6.QtGui (NOT QtWidgets)
- QToolButton.ToolButtonPopupMode.InstantPopup
- QMessageBox.StandardButton.Yes
- QWebEngineDownloadRequest → QtWebEngineCore
- Never bare except: pass — let errors bubble up
- QThread.run() MUST emit errors via a signal — never swallow them silently:
  error = pyqtSignal(str)  # define on the class
  def run(self): ... except Exception as e: self.error.emit(str(e))
- Never wrap signal-connected methods (on_finished, on_result etc) in try/except — errors there are invisible to the browser's error detection system

OUTPUT FORMAT:
[CHAT]
2-3 sentences explaining what you built or changed
[/CHAT]
[CODE]
Raw Python only, no markdown fences
[/CODE]
[REQUIREMENTS]
📦 pip install package-name
✅ No installation needed
[/REQUIREMENTS]"""

    @classmethod
    def build_prompt(cls, user_request: str, module_context: dict = None) -> str:
        if module_context is None:
            module_context = {}
        if module_context.get("is_fix_request"):
            return cls._fix_prompt(user_request, module_context)
        elif module_context.get("is_modification_request") and module_context.get(
            "current_code"
        ):
            return cls._modify_prompt(user_request, module_context)
        else:
            return cls._new_prompt(user_request)

    @classmethod
    def _new_prompt(cls, user_request: str) -> str:
        return f"""Create a KaiBrowser PyQt6 plugin.

SKELETON (follow this structure):
{cls.SKELETON}
{cls.PLUGIN_RULES}
REQUEST: {user_request}"""

    @classmethod
    def _modify_prompt(cls, user_request: str, context: dict) -> str:
        current_code = context.get("current_code", "")
        history = context.get("conversation_history", [])
        history_text = ""
        if history:
            history_text = "\nCONTEXT:\n"
            for msg in history[-3:]:
                history_text += (
                    f"{msg.get('role','').upper()}: {msg.get('content','')[:100]}\n"
                )

        return f"""Modify this KaiBrowser plugin. Keep all existing functionality, only apply requested changes.

EXISTING CODE:
{current_code}
{history_text}
SKELETON (for reference on correct patterns):
{cls.SKELETON}
{cls.PLUGIN_RULES}
CHANGE REQUEST: {user_request}"""

    @classmethod
    def _fix_prompt(cls, user_request: str, context: dict) -> str:
        failed_code = context.get("failed_code", context.get("current_code", ""))
        error = context.get("error_context", "Unknown error")

        return f"""Fix this broken KaiBrowser plugin.

BROKEN CODE:
{failed_code}

ERROR: {error}

SKELETON (for reference on correct patterns):
{cls.SKELETON}
FIX APPROACH: Prefer simple fixes. For Qt lifecycle errors just recreate the object with parent=. Trust Qt's parent ownership system.

{cls.PLUGIN_RULES}"""
