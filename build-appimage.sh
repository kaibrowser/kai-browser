#!/bin/bash
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Kai Browser - AppImage Build"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Config ────────────────────────────────────────────────
APPDIR="AppDir"
APPIMAGE_TOOL="appimagetool-x86_64.AppImage"
APPIMAGE_TOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

# ── Get version ───────────────────────────────────────────
VERSION=$(grep -oP 'VERSION\s*=\s*"\K[^"]+' updater.py)
if [ -z "$VERSION" ]; then
    echo "✗ Could not read VERSION from updater.py"
    exit 1
fi
TAG="v${VERSION}"
echo "Version: $VERSION (tag: $TAG)"
echo "Python:  $PYTHON_VERSION"
echo ""

# ── Check / install dependencies ─────────────────────────
echo "→ Checking build dependencies..."
for pkg in python3-venv python3-pip patchelf; do
    if ! dpkg -l "$pkg" &>/dev/null; then
        echo "  Installing $pkg..."
        sudo apt install -y "$pkg"
    fi
done
echo "✓ Build dependencies ready"
echo ""

# ── Setup venv ────────────────────────────────────────────
if [ ! -d "venv" ]; then
    echo "→ Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "→ Installing Python packages..."
pip install -q pyinstaller PyQt6 selenium webdriver-manager PyQt6-WebEngine keyring requests
echo "✓ Python packages ready"
echo ""

# ── Compile with PyInstaller ──────────────────────────────
echo "→ Compiling with PyInstaller..."
pyinstaller --onefile --windowed --name kaibrowser \
    --icon=kai-browser_logo.ico \
    --add-data "kai-browser_logo.png:." \
    --exclude-module=modules \
    --exclude-module=dependencies \
    --exclude-module=__pycache__ \
    --hidden-import=PyQt6 \
    --hidden-import=selenium \
    --hidden-import=webdriver_manager \
    --hidden-import=keyring \
    --hidden-import=requests \
    launch_browser.py
echo "✓ Compile complete"
echo ""

# ── Build AppDir structure ────────────────────────────────
echo "→ Building AppDir structure..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# Copy compiled binary
cp dist/kaibrowser "$APPDIR/usr/bin/kaibrowser"
chmod +x "$APPDIR/usr/bin/kaibrowser"

# Copy supporting files
cp kai-browser_logo.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/kaibrowser.png"
cp kai-browser_logo.png "$APPDIR/kaibrowser.png"

# Desktop entry
cat > "$APPDIR/usr/share/applications/kaibrowser.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Kai Browser
Comment=AI-powered extensible browser
Exec=kaibrowser
Icon=kaibrowser
Terminal=false
Categories=Network;WebBrowser;
DESKTOP

# AppImage required files at root of AppDir
cp "$APPDIR/usr/share/applications/kaibrowser.desktop" "$APPDIR/kaibrowser.desktop"

# AppRun entry point
cat > "$APPDIR/AppRun" << 'APPRUN'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="$HERE/usr/bin:$PATH"

# Setup writable user directories for dependencies and modules
USER_DATA="$HOME/.local/share/kaibrowser"
mkdir -p "$USER_DATA/dependencies"
mkdir -p "$USER_DATA/modules"

exec "$HERE/usr/bin/kaibrowser" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

echo "✓ AppDir structure ready"
echo ""

# ── Download appimagetool if needed ──────────────────────
if [ ! -f "$APPIMAGE_TOOL" ]; then
    echo "→ Downloading appimagetool..."
    wget -q "$APPIMAGE_TOOL_URL" -O "$APPIMAGE_TOOL"
    chmod +x "$APPIMAGE_TOOL"
    echo "✓ appimagetool ready"
    echo ""
fi

# ── Build AppImage ────────────────────────────────────────
echo "→ Building AppImage..."
ARCH=x86_64 ./"$APPIMAGE_TOOL" "$APPDIR" "KaiBrowser-${VERSION}-x86_64.AppImage" 2>/dev/null
echo "✓ Created KaiBrowser-${VERSION}-x86_64.AppImage"
echo ""

# ── Package archive ──────────────────────────────────────
echo "→ Packaging archive..."
mkdir -p appimage_dist
cp "KaiBrowser-${VERSION}-x86_64.AppImage" appimage_dist/
cp kai-browser_logo.png appimage_dist/kaibrowser.png
cp DISCLAIMER.md appimage_dist/
cp README.md appimage_dist/
cp LICENSE.save appimage_dist/
cp TERMS_OF_SERVICE.md appimage_dist/
tar -czf kaibrowser-linux.tar.gz --transform 's|^appimage_dist|kaibrowser|' appimage_dist/
rm -rf appimage_dist
echo "✓ Created kaibrowser-linux.tar.gz"
echo ""

# ── Confirm release ───────────────────────────────────────
read -p "Push tag $TAG and upload AppImage to GitHub release? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "AppImage ready but not released: KaiBrowser-${VERSION}-x86_64.AppImage"
    exit 0
fi

# ── Tag and release ───────────────────────────────────────
TAG_EXISTS=0
RELEASE_EXISTS=0

if git ls-remote --tags origin | grep -q "refs/tags/$TAG"; then
    TAG_EXISTS=1
fi

if gh release view "$TAG" &>/dev/null; then
    RELEASE_EXISTS=1
fi

echo "Tag exists: $TAG_EXISTS | Release exists: $RELEASE_EXISTS"

if [ "$TAG_EXISTS" -eq 1 ] && [ "$RELEASE_EXISTS" -eq 1 ]; then
    echo "→ Uploading to existing release $TAG..."
    gh release upload "$TAG" kaibrowser-linux.tar.gz --clobber

elif [ "$TAG_EXISTS" -eq 1 ] && [ "$RELEASE_EXISTS" -eq 0 ]; then
    echo "→ Creating release for existing tag $TAG..."
    gh release create "$TAG" kaibrowser-linux.tar.gz \
        --title "Kai Browser $TAG" \
        --notes "Kai Browser $VERSION — Universal Linux AppImage (glibc 2.35+)" \
        --latest

else
    echo "→ Creating tag $TAG..."
    git tag "$TAG"
    git push origin "$TAG"
    echo "✓ Tag pushed"
    echo "→ Creating GitHub release..."
    gh release create "$TAG" kaibrowser-linux.tar.gz \
        --title "Kai Browser $TAG" \
        --notes "Kai Browser $VERSION — Universal Linux AppImage (glibc 2.35+)" \
        --latest
fi

echo "✓ Release updated"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Done! Released $TAG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Users can run it with:"
echo "  chmod +x KaiBrowser-${VERSION}-x86_64.AppImage"
echo "  ./KaiBrowser-${VERSION}-x86_64.AppImage"