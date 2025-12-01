# Kai Browser
A Python-based browser where you can create custom extensions using natural language. Describe what you want, and AI builds it.

## Installation

### Download the Latest Release
[Download Kai Browser](https://github.com/exfo999/kai-browser/releases/latest)

### Extract and Run
```bash
# Extract the archive
tar -xzf kai-browser-linux.tar.gz
cd dist

# Make executable (if needed)
chmod +x kai_browser

# Run
./kai_browser
```

### Requirements
- Linux (tested on Ubuntu)

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
- Enable/disable extensions in the extensions dropdown menu in the main browser window
- Access the **Marketplace** button in the extensions dropdown to browse and download community extensions
- Modify extensions by re-generating with updated natural language prompts

---

## Extension Marketplace

### Download Extensions
- Visit [kaibrowser.com/marketplace](https://kaibrowser.com/marketplace) 
- **Or** click the **Marketplace** button in the extensions dropdown menu within the browser

### Share Your Extensions
- Upload your extensions at [kaibrowser.com/upload](https://kaibrowser.com/upload)
- Sign in to manage your uploaded extensions in **My Extensions**

---

## Support

For issues or questions, please open an issue on GitHub.
