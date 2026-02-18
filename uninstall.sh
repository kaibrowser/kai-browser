#!/bin/bash
clear
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Kai Browser Uninstall"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

[ -d "$HOME/.local/share/kaibrowser" ] && rm -rf "$HOME/.local/share/kaibrowser" && echo "✓ Removed application files"
[ -f "$HOME/.local/bin/kaibrowser" ] && rm "$HOME/.local/bin/kaibrowser" && echo "✓ Removed executable"
[ -f "$HOME/.local/share/applications/kaibrowser.desktop" ] && rm "$HOME/.local/share/applications/kaibrowser.desktop" && echo "✓ Removed from applications menu"
[ -f ~/Desktop/kaibrowser.desktop ] && rm ~/Desktop/kaibrowser.desktop && echo "✓ Removed desktop shortcut"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Uninstall Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
