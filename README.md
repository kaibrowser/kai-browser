# Kai Browser

A Python-based browser where you can create custom extensions using natural language. Describe what you want, and AI builds it.

> **Note:** The AI extension builder is still in early development and actively improving.

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

- Linux (tested on Ubuntu)

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

> **Tip:** You can refine your extension after generation. Ask it to "make the button blue" or "add a keyboard shortcut".

#### Auto-Fix Errors

Enable "Auto-fix errors" in the AI tab to have the AI automatically attempt to fix loading errors (retries up to 3 times).

---

### Method 2: Code Editor

1. Click the **✨** button to open the Extension Builder
2. Select the **Code Editor** tab
3. Choose a template or write your own code
4. Click **"Add Extension"** to install it

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

> **Note:** The marketplace is in early development. Review extension code before installing from untrusted sources.

---

## Data Storage

Kai stores data in `~/.kai_browser/`:

- `preferences.json` – Settings and extension states
- `profile/` – Cookies and browsing data
- `cache/` – Cached content

To reset everything, delete the `~/.kai_browser/` folder.

---

## Troubleshooting

### Extension Won't Load

- Check the terminal for error messages
- Use "Fix with AI" when the error dialog appears
- Ensure class name ends with `Module` or `Plugin`, or has an `activate` method
- Use snake_case for file names (e.g., `my_extension.py`)

### Common PyQt6 Issues

```python
# WRONG
button.setPopupMode(PopupMode.InstantPopup)

# CORRECT
button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
```

### AI Generation Issues

- **Timeout** – AI service busy, try again
- **Rate limit** – Wait 30 seconds
- **Invalid API key** – Check Settings tab

---

## Documentation

For full documentation, visit [kaibrowser.com/docs](https://kaibrowser.com/docs)

---

## Support

For issues or questions, please [open an issue on GitHub](https://github.com/kaibrowser/kai-browser/issues).
