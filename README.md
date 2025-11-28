# kai-browser
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
## Usage

### Starting Kai Browser
After installation, launch the browser:
```bash
./kai_browser
```

### Creating Custom Extensions

Kai Browser features an **AI-powered extension builder** that lets you create browser extensions using natural language—no coding required.

#### Setup Your API Key
1. Open the extension builder in Kai Browser
2. Enter your AI API key in the AI setting tab (Gemini, Claude, OpenAI GPT.)
3. Your API key is saved locally on your machine
4. Select the Active Provider for the API Key you have saved

#### Build Extensions with Natural Language
To create an extension select the AI Generate tab, start your prompt with:
```
make a kai browser extension
```
**Examples:**
- "make a kai browser extension that highlights all links in yellow"
- "make a kai browser extension for dark mode toggle on any website"
- "make a kai browser extension that counts words in text fields"
- "make a kai browser extension to translate selected text to Spanish"
  
Click the "Generate extension with AI" button
The AI will generate the extension code. If the generation was a sucess the code will be displayed, click the save button to install it automatically.
Using a premium AI API key will have better success at generating a complex extension. 

#### Build Extensions with with the code editor
- Select the code editor tab
- use the template of your choice
- enter python code
- Click the Save Load Extension Button this will install it automatically.
  
#### Build Extensions manually
- Create code in your code editor and drop the .py file into the modules folder the browser will install it automatically. 
  

### Managing Extensions
- View active extensions in the manage tab
- Enable/disable extensions as needed
- Modify extensions by describing changes in natural language

### Requirements
- Linux (tested on Ubuntu)
- [List any dependencies here]
