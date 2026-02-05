"""
AI Examples - Optimized Context-Aware Prompt Building
Reduced prompt size by consolidating shared sections
Updated: Added data persistence pattern to REFERENCE example
"""


class AIExamples:
    """Context-aware prompt building for AI code generation"""

    REFERENCE = """from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QToolButton, QMenu
from PyQt6.QtGui import QAction
import json
from pathlib import Path

class ExamplePlugin:
    def __init__(self, browser):
        self.browser = browser
        self.toolbar = browser.toolbar
        
        # Data persistence - organized location
        data_dir = Path.home() / "kaibrowser" / "extensions" / self.__class__.__name__
        data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = data_dir / "data.json"
        
        # Load saved data
        self.counter = self.load_data()
    
    def activate(self):
        button = QToolButton()
        button.setText("🎯 Example")
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        menu = QMenu()
        increment_action = QAction("Increment", menu)
        increment_action.triggered.connect(self.increment)
        menu.addAction(increment_action)
        
        status_action = QAction(f"Count: {self.counter}", menu)
        status_action.setEnabled(False)
        menu.addAction(status_action)
        
        button.setMenu(menu)
        self.toolbar.addWidget(button)
    
    def increment(self):
        self.counter += 1
        self.save_data()  # Save after change
        web_view = self.browser.get_active_web_view()
        url = web_view.url().toString() if web_view else "No tab"
        print(f"Counter: {self.counter}, URL: {url}")
    
    def load_data(self):
        if self.data_file.exists():
            with open(self.data_file, encoding='utf-8') as f:
                return json.load(f).get('counter', 0)
        return 0

    def save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump({'counter': self.counter}, f, indent=2)
    """

    # Consolidated shared context - used in all prompts
    SHARED_CONTEXT = """BROWSER API:
- browser.toolbar (QToolBar), browser.get_active_web_view() (QWebEngineView)
- Current tab's URL: browser.get_active_web_view().url().toString()
- Navigate: browser.get_active_web_view().setUrl(QUrl(url))
- Access current page: web_view = browser.get_active_web_view()
- Tab awareness: Always use get_active_web_view() not browser.web_view

PLUGIN STRUCTURE:
- __init__(self, browser) and activate() method
- Use standard PyQt6 APIs (QToolButton, QMenu, QAction)

DATA PERSISTENCE (Optional):
- Save to: Path.home() / "kaibrowser" / "extensions" / self.__class__.__name__
- Use standard json.dump() and json.load()
- ALWAYS use encoding='utf-8' when opening files (required for Windows)
- See REFERENCE example for pattern

CRITICAL PyQt6 SYNTAX:
- QAction is in PyQt6.QtGui NOT PyQt6.QtWidgets (common error!)
- QToolButton.ToolButtonPopupMode.InstantPopup (NOT PopupMode.InstantPopup)
- QMessageBox.StandardButton.Yes (NOT StandardButton.Yes)
- download.isFinished() not download.finished
- Qt enums from QtCore (Qt.AlignmentFlag, etc.)
- QWebEngineDownloadRequest from QtWebEngineCore

ERROR HANDLING:
- NEVER use bare try/except that silently swallows errors with 'pass'
- For input validation, check values explicitly before using them
- Example: if not text or float(text) <= 0: return  # Good
- Example: try: calculate() except: pass  # BAD - hides real errors
- Let errors bubble up so the browser can catch and report them
- The browser has auto-detection that will offer to fix real errors

BUNDLED: PyQt6 (no install needed)

OUTPUT FORMAT - EXACT STRUCTURE REQUIRED:
[CHAT]
Brief response (2-3 sentences) - explain what you built/changed
[/CHAT]

[CODE]
Raw Python code only, no markdown
[/CODE]

[REQUIREMENTS]
📦 pip install package-name (for non-bundled packages, one per line)
✅ No installation needed - uses only bundled packages
🌐 Requires internet connection (if needed)
[/REQUIREMENTS]"""

    @classmethod
    def build_prompt(cls, user_request: str, module_context: dict = None) -> str:
        """Build context-aware prompt for new generation or modifications"""
        if module_context is None:
            module_context = {}

        is_fix = module_context.get("is_fix_request", False)
        is_modification = module_context.get("is_modification_request", False)
        current_code = module_context.get("current_code", "")

        if is_fix:
            return cls._build_fix_prompt(user_request, module_context)
        elif is_modification and current_code:
            return cls._build_modification_prompt(user_request, module_context)
        else:
            return cls._build_new_prompt(user_request, module_context)

    @classmethod
    def _build_new_prompt(cls, user_request: str, context: dict) -> str:
        """Prompt for new extension"""
        return f"""You are a friendly AI assistant creating browser plugins using PyQt6.

{cls.SHARED_CONTEXT}

REFERENCE EXAMPLE:
{cls.REFERENCE}

USER REQUEST: {user_request}

Be conversational in [CHAT], prefer bundled packages, use 📦 pip install format for others."""

    @classmethod
    def _build_modification_prompt(cls, user_request: str, context: dict) -> str:
        """Prompt for modifying existing code"""
        current_code = context.get("current_code", "")
        conversation_history = context.get("conversation_history", [])

        history_text = ""
        if conversation_history:
            history_text = "\n\nPREVIOUS CONTEXT:\n"
            for msg in conversation_history[-5:]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:150]
                history_text += f"{role.upper()}: {content}\n"

        return f"""You are a friendly AI assistant MODIFYING an existing browser plugin.

CRITICAL: Modify the code below - don't create new from scratch.

EXISTING CODE:
```python
{current_code}
```{history_text}

NEW REQUEST: {user_request}

INSTRUCTIONS:
1. Take existing code above
2. Apply ONLY requested changes
3. Keep all existing functionality
4. Maintain same class name/structure

{cls.SHARED_CONTEXT}

In [CHAT] explain what changed. Start with [CHAT] section."""

    @classmethod
    def _build_fix_prompt(cls, user_request: str, context: dict) -> str:
        """Prompt for fixing errors"""
        failed_code = context.get("failed_code", context.get("current_code", ""))
        error_context = context.get("error_context", "Unknown error")

        return f"""You are a friendly AI assistant FIXING a broken browser plugin.

BROKEN CODE:
```python
{failed_code}
```

ERROR: {error_context}

TASK: Analyze error, fix code, maintain functionality, return corrected version.

COMMON FIXES: Missing imports, syntax (indentation/quotes), attribute errors, type errors

FIX PHILOSOPHY - PREFER SIMPLE SOLUTIONS:
- For Qt object lifecycle errors (QMenu/QWidget deleted): Just recreate the object with proper parent, don't add validity checks
- Trust Qt's parent ownership system - adding parent= is usually enough
- Avoid defensive try/except blocks for lifecycle issues
- Don't check if objects are valid before recreating them - just recreate
- Example: Instead of checking "if menu exists", just do "self.menu = QMenu(parent)"

{cls.SHARED_CONTEXT}

In [CHAT] explain what was wrong and how you fixed it. Start with [CHAT] section."""
