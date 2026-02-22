#!/bin/bash
clear
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Kai Browser Uninstall"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
INSTALL_DIR="$HOME/.local/share/kaibrowser"
if [ -d "$INSTALL_DIR" ]; then
  KEEP_USER_DATA=0
  if [ -d "$INSTALL_DIR/modules" ] || [ -d "$INSTALL_DIR/dependencies" ]; then
    echo "⚠ User data found (extensions & dependencies)"
    read -p "  Keep your extensions and dependencies? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      KEEP_USER_DATA=1
      mv "$INSTALL_DIR/modules" /tmp/kaibrowser_modules_backup 2>/dev/null
      mv "$INSTALL_DIR/dependencies" /tmp/kaibrowser_dependencies_backup 2>/dev/null
    fi
  fi
  rm -rf "$INSTALL_DIR"
  echo "✓ Removed application files"
  if [ "$KEEP_USER_DATA" -eq 1 ]; then
    mkdir -p "$INSTALL_DIR"
    mv /tmp/kaibrowser_modules_backup "$INSTALL_DIR/modules" 2>/dev/null
    mv /tmp/kaibrowser_dependencies_backup "$INSTALL_DIR/dependencies" 2>/dev/null
    echo "✓ Extensions and dependencies kept at $INSTALL_DIR"
  fi
fi
[ -f "$HOME/.local/bin/kaibrowser" ] && rm "$HOME/.local/bin/kaibrowser" && echo "✓ Removed executable"
[ -f "$HOME/.local/share/applications/kaibrowser.desktop" ] && rm "$HOME/.local/share/applications/kaibrowser.desktop" && echo "✓ Removed from applications menu"
[ -f ~/Desktop/kaibrowser.desktop ] && rm ~/Desktop/kaibrowser.desktop && echo "✓ Removed desktop shortcut"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Uninstall Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""