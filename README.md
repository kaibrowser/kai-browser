# Kai Browser
A Python-based browser where you can create custom extensions using natural language. Describe what you want, and AI builds it.

## Installation

### Download and Run
```bash
git clone https://github.com/exfo999/kai-browser.git
cd kai-browser/dist
mkdir -p modules
chmod +x kai_browser
./kai_browser
```

### Requirements
- Linux (tested on Ubuntu)
- Python 3.x (if not using pre-compiled version)

---

## Usage

### Starting Kai Browser
After installation, launch the browser:
```bash
./kai_browser
```

---

## Creating Custom Extensions

Kai Browser features an **AI-powered extension builder** that lets you create browser extensions using natural language—no coding required.

### Method 1: AI Generation

#### Setup Your API Key
1. Open the extension builder in Kai Browser
2. Navigate to the **AI Settings** tab
3. Enter your AI API key (Gemini, Claude, or OpenAI GPT)
4. Your API key is saved locally on your machine
5. Select the **Active Provider** for the API key you have saved

#### Generate Extensions with Natural Language
1. Select the **AI Generate** tab
2. Start your prompt with: `make a kai browser extension`
3. Click the **"Generate extension with AI"** button

**Examples:**
- "make a kai browser extension that highlights all links in yellow"
- "make a kai browser extension for dark mode toggle on any website"
- "make a kai browser extension that counts words in text fields"
- "make a kai browser extension to translate selected text to Spanish"

4. If generation succeeds, the code will be displayed
5. Click the **Save** button to install it automatically

> **Tip:** Using a premium AI API key will have better success at generating complex extensions.

---

### Method 2: Code Editor

1. Select the **Code Editor** tab
2. Choose a template
3. Enter your Python code
4. Click **"Save/Load Extension"** to install it automatically

---

### Method 3: Manual Installation

1. Create your extension code in your preferred code editor
2. Save as a `.py` file
3. Drop the file into the `modules/` folder
4. The browser will install it automatically

---

## Managing Extensions

- View active extensions in the **Manage** tab
- Enable/disable extensions as needed
- Modify extensions by re-generating with updated natural language prompts

---

## Support

For issues or questions, please open an issue on GitHub.
