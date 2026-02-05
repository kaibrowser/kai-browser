# Kai Browser

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-GPL-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)

A Python-based browser where you can create custom extensions using natural language. Describe what you want, and AI builds it.

> **Note:** The AI extension builder is still in early development and actively improving. Available AI providers: Gemini (free tier available), Claude (best results), and OpenAI.

---

## License

KaiBrowser™ is free and open-source software licensed under the **GNU General Public License v3.0**.

This means you can:
- Use the software freely
- Modify the source code
- Distribute your modifications
- Must keep derivatives under GPL v3
- Must disclose source code

See [LICENSE](LICENSE) for full terms.

## Disclaimer

**IMPORTANT**: KaiBrowser™ is provided "AS IS" without warranty. Users are responsible for:
- Third-party extensions installed from any source
- Content accessed through the browser
- Compliance with applicable laws
- AI-generated extension code (always review before activating)

See [DISCLAIMER.md](DISCLAIMER.md) for full legal terms.

---

## Safety Notice

- AI-generated extensions run with full browser permissions
- **Always review generated code before activating extensions**
- Never include sensitive information (passwords, tokens) in AI prompts
- Extensions are stored as Python files in `~/kaibrowser/modules/`
- Use at your own risk

---

## Installation

### Download the Latest Release

[Download Kai Browser](https://github.com/kaibrowser/kai-browser/releases/latest)

### Extract and Run

```bash
# Extract the archive
tar -xzf kai-browser-linux.tar.gz
cd kai-browser

# Make executable (if needed)
chmod +x kai-browser

# Run
./kai-browser
```

### Requirements

- Linux (exe and source code tested on Ubuntu, Kali Linux, Linux Mint)
- Windows (source code tested on Windows 10, 11)
---

## Browser Interface

- **Navigation Bar** – Back, forward, reload, URL bar with security indicator
- **Tab Bar** – Multiple tabs with drag-to-reorder
- **Extensions Menu (🧩)** – Enable, disable, visit the Marketplace or upload an extension
- **Extension Builder (✨)** – Create extensions with AI, write extension code in the code editor
- **Settings (⋮)** – Configure homepage, search engine, etc.

---

## Creating Custom Extensions

Kai Browser features an **AI-powered extension builder** that lets you create browser extensions using natural language—no coding required.

### Method 1: AI Generation

#### Setup Your API Key

1. Click the **✨** button in the toolbar to open the Extension Builder
2. Navigate to the **Settings** tab
3. Enter your API key (Gemini, Claude, or OpenAI)
4. Your key is stored securely using your system's keyring

**API Key Storage:**
- Keys are stored in your system's secure keyring (not plain text)
- Linux: Uses `keyring` library with system keychain
- Never shared or transmitted except to the selected AI provider
- Can be deleted at any time through Settings

#### Generate Extensions with Natural Language

1. Select the **AI** tab
2. Describe your extension (e.g., "Add a button that shows word count")
3. Review the generated code
4. Click **"Add Extension"** to install it

**Examples:**
- "Add a dark mode toggle button"
- "Create a button that highlights all links in yellow"
- "Make a word counter for text fields"
- "Add a button to translate selected text"
- "Create a note-taking extension that saves my notes"
- "Build a todo list that persists across restarts"
- "Make a bookmark manager"

> **Tip:** You can refine your extension after generation. Ask it to "make the button blue" or "add a keyboard shortcut".

#### Auto-Fix Errors

Enable "Auto-fix errors" in the AI tab to have the AI automatically attempt to fix loading errors (retries up to 3 times).

---

### Method 2: Code Editor

1. Click the **✨** button to open the Extension Builder
2. Select the **Code Editor** tab
3. Choose a template or write your own code
4. Click **"Add Extension"** to install it

**Quick Example:**
```python
from PyQt6.QtWidgets import QToolButton
from PyQt6.QtCore import QUrl
import json
from pathlib import Path

class MyPlugin:
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
        button.setText("🎯 My Button")
        button.clicked.connect(self.on_click)
        self.toolbar.addWidget(button)
    
    def on_click(self):
        self.counter += 1
        self.save_data()
        
        # Always use get_active_web_view() to access the current tab
        web_view = self.browser.get_active_web_view()
        if web_view:
            url = web_view.url().toString()
            print(f"Clicked {self.counter} times. Current URL: {url}")
    
    def load_data(self):
        if self.data_file.exists():
            with open(self.data_file, encoding='utf-8') as f:
                return json.load(f).get('counter', 0)
        return 0
    
    def save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump({'counter': self.counter}, f, indent=2)
```

> **Important:** Always use `browser.get_active_web_view()` to access the current tab, not `browser.browser` or `browser.web_view`.

---

### Extension Data Persistence

Extensions automatically handle their own data storage using standard Python file operations. The AI generates proper save/load methods for you.

**How It Works:**

```python
import json
from pathlib import Path

class MyExtension:
    def __init__(self, browser):
        # AI automatically generates this data persistence setup
        data_dir = Path.home() / "kaibrowser" / "extensions" / self.__class__.__name__
        data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = data_dir / "data.json"
        
        # Load saved data
        self.my_data = self.load_data()
    
    def load_data(self):
        if self.data_file.exists():
            with open(self.data_file, encoding='utf-8') as f:
                return json.load(f)
        return {}  # Default value
    
    def save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.my_data, f, indent=2)
```

**Data Location:**
- Extensions save to: `~/kaibrowser/extensions/<ExtensionName>/data.json`
- Organized by extension class name automatically
- Data persists across browser restarts

**Managing Extension Data:**
- Open Extension Builder → **Manage** tab
- Select an extension and click **"Clear Data"** to reset its saved data
- When deleting an extension, its data is automatically removed

**Example - Notes Extension:**
```python
class NotesPlugin:
    def __init__(self, browser):
        self.browser = browser
        
        # Setup data persistence
        data_dir = Path.home() / "kaibrowser" / "extensions" / self.__class__.__name__
        data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = data_dir / "notes.json"
        
        # Load saved notes on startup
        self.notes = self.load_data()
    
    def load_data(self):
        if self.data_file.exists():
            with open(self.data_file, encoding='utf-8') as f:
                return json.load(f).get('notes', '')
        return ''
    
    def save_notes(self, text):
        # Save notes - persists across browser restarts
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump({'notes': text}, f, indent=2)
        print(f"Saved to: {self.data_file}")
```

> **Note:** The AI knows how to set this up! Just ask it to create extensions that "save settings" or "remember data" and it will generate the proper data persistence code automatically.

---

### Method 3: Manual Installation

1. Create your extension as a `.py` file
2. Use the naming format `my_extension.py` (snake_case)
3. Place the file in the `modules/` folder
4. Restart Kai Browser

---

## Managing Extensions

- Open the Extension Builder and select the **Manage** tab to view, reload, or delete extensions
- Use **AI Improve** or **AI Fix** to enhance existing extensions
- **Clear Data** button removes all saved data for selected extension
- Enable/disable extensions from the **Extensions Menu (🧩)** in the toolbar
- Access the **Marketplace** from the Extensions Menu to browse community extensions

---

## Extension Marketplace

### Download Extensions

- Visit [kaibrowser.com/marketplace](https://kaibrowser.com/marketplace)
- **Or** click **Marketplace** in the Extensions Menu (🧩) within the browser
- Download the `.py` file and place it in `modules/`, or copy the code into the Code Editor

### Share Your Extensions

- Upload your extensions at [kaibrowser.com/upload](https://kaibrowser.com/upload)
- Sign in to manage your uploads in **My Extensions**

> **Note:** The marketplace is in early development. Review extension code before installing from untrusted sources. KaiBrowser™ does not guarantee the safety or functionality of third-party extensions. See [DISCLAIMER.md](DISCLAIMER.md) for details.

---

## Data Storage

Kai stores data in OS-appropriate locations:

**Linux:** `~/.local/share/kaibrowser/` and `~/kaibrowser/`
- `~/.local/share/kaibrowser/preferences.json` – Browser settings and extension states
- `~/kaibrowser/extensions/` – Extension data (organized by extension name)
- `~/.local/share/kaibrowser/profile/` – Cookies and browsing data
- `~/.local/share/kaibrowser/cache/` – Cached content

**Windows:** `C:\Users\<user>\AppData\Local\kaibrowser\` and `C:\Users\<user>\kaibrowser\`

**Mac:** `~/Library/Application Support/kaibrowser/` and `~/kaibrowser/`

To reset everything, delete both the `.local/share/kaibrowser` and `~/kaibrowser` folders.

---

## Troubleshooting

### Extension Won't Load

- Check the terminal for error messages
- Use "Fix with AI" when the error dialog appears
- Ensure class name ends with `Module` or `Plugin`, or has an `activate` method
- Use snake_case for file names (e.g., `my_extension.py`)
- Verify PyQt6 syntax is correct
- If you see an `ImportError`, the browser will automatically prompt you to install the package. System-level packages will show the install command to run in your terminal, while other packages can be auto-installed to the dependencies folder through the dialog

### Common PyQt6 Issues

```python
# WRONG
button.setPopupMode(PopupMode.InstantPopup)

# CORRECT
button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
```

**Important PyQt6 Notes:**
- `QAction` is imported from `PyQt6.QtGui` (not QtWidgets like in PyQt5)
- Use full enum paths: `QToolButton.ToolButtonPopupMode.InstantPopup`

### Tab Access Issues

```python
# WRONG (deprecated)
web_view = self.browser.browser
web_view = self.browser_core.browser

# CORRECT
web_view = self.browser.get_active_web_view()
web_view = self.browser_core.get_active_web_view()
```

### Data Persistence Issues

```python
# The AI automatically generates the proper pattern:

# Setup in __init__
data_dir = Path.home() / "kaibrowser" / "extensions" / self.__class__.__name__
data_dir.mkdir(parents=True, exist_ok=True)
self.data_file = data_dir / "data.json"

# Save
with open(self.data_file, 'w', encoding='utf-8') as f:
    json.dump(my_data, f, indent=2)

# Load
if self.data_file.exists():
    with open(self.data_file, encoding='utf-8') as f:
        my_data = json.load(f)
```

### Windows Compatibility

Always include `encoding='utf-8'` when opening files to ensure extensions work on both Linux and Windows:
```python
# Required for Windows (especially with emojis/special characters)
with open(filepath, 'r', encoding='utf-8') as f:
with open(filepath, 'w', encoding='utf-8') as f:
```

### AI Generation Issues

- **Timeout** – AI service busy, try again
- **Rate limit** – Wait 30 seconds
- **Invalid API key** – Check Settings tab

---

## Contributing

We welcome contributions! Please read our contributing guidelines (coming soon) before submitting pull requests.

### Development Roadmap

- [x] Core browser functionality
- [x] Extension system with persistent storage
- [x] AI-powered extension builder
- [x] Basic UI/UX
- [x] Kai Marketplace integration
- [ ] Mobile version
- [ ] Built-in VPN support

---

## Support & Community

- **Bug Reports**: [Open an issue on GitHub](https://github.com/kaibrowser/kai-browser/issues)
- **Feature Requests**: Start a discussion
- **Community**: Join our Discord (coming soon)
- **Sponsor**: Support development via GitHub Sponsors

---

## Documentation

For full documentation, see this README 
---

## Acknowledgments

Built with:
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework (GPL v3)
- [QtWebEngine](https://doc.qt.io/qt-6/qtwebengine-index.html) - Web rendering (LGPL v3)

---

**Version**: 1.0.4  
**Status**: Active Development  
**Copyright**: © 2025 KaiBrowser™

For questions or support, please open an issue or contact the development team.