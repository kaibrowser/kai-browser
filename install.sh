#!/bin/bash
clear
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Kai Browser Installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

INSTALL_DIR="$HOME/.local/share/kaibrowser"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

echo "→ Installing application files..."
cp kaibrowser "$INSTALL_DIR/" || { echo "✗ Failed to copy kaibrowser"; exit 1; }
cp kaibrowser.png "$INSTALL_DIR/" 2>/dev/null
cp DISCLAIMER.md "$INSTALL_DIR/" 2>/dev/null
cp README.md "$INSTALL_DIR/" 2>/dev/null
cp LICENSE.save "$INSTALL_DIR/" 2>/dev/null
cp TERMS_OF_SERVICE.md "$INSTALL_DIR/" 2>/dev/null
chmod +x "$INSTALL_DIR/kaibrowser"

cat > "$BIN_DIR/kaibrowser" << 'WRAPPER'
#!/bin/bash
exec "$HOME/.local/share/kaibrowser/kaibrowser" "$@"
WRAPPER
chmod +x "$BIN_DIR/kaibrowser"
echo "✓ Installed to $INSTALL_DIR"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "⚠ WARNING: $BIN_DIR is not in your PATH"
    echo "Add this line to your shell config (~/.bashrc or ~/.zshrc):"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/kaibrowser.desktop" << DESKTOPEOF
[Desktop Entry]
Version=1.0.5
Type=Application
Name=Kai Browser
Comment=AI-powered extensible browser
Exec=$INSTALL_DIR/kaibrowser
Icon=$INSTALL_DIR/kaibrowser.png
Terminal=false
Categories=Network;WebBrowser;
DESKTOPEOF
echo "✓ Added to applications menu"

if [ -d ~/Desktop ]; then
    read -p "Create desktop shortcut? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp "$HOME/.local/share/applications/kaibrowser.desktop" ~/Desktop/
        chmod +x ~/Desktop/kaibrowser.desktop
        if command -v gio &> /dev/null; then
            gio set ~/Desktop/kaibrowser.desktop metadata::trusted true 2>/dev/null
        fi
        echo "✓ Desktop shortcut created"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installation Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Launch: kaibrowser"
echo ""
