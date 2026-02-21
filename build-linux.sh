#!/bin/bash
set -e
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Kai Browser - Linux Build & Release"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
# Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "✗ Virtual environment not found. Run 'python3 kaibrowser.py' first to create it."
    exit 1
fi
# Get version from updater.py
VERSION=$(grep -oP 'VERSION\s*=\s*"\K[^"]+' updater.py)
if [ -z "$VERSION" ]; then
    echo "✗ Could not read VERSION from updater.py"
    exit 1
fi
TAG="v${VERSION}"
echo "Version: $VERSION (tag: $TAG)"
echo ""
# Check if tag already exists on remote
TAG_EXISTS=0
if git ls-remote --tags origin | grep -q "refs/tags/$TAG"; then
    echo "Tag $TAG already exists on GitHub. Will upload to existing release."
    TAG_EXISTS=1
fi
# Compile
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
echo "✓ Build complete"
echo ""
# Copy files to dist
echo "→ Copying files to dist..."
cp kai-browser_logo.png dist/kaibrowser.png
cp DISCLAIMER.md dist/
cp README.md dist/
cp LICENSE.save dist/
cp HOW_TO_INSTALL.txt dist/
cp TERMS_OF_SERVICE.md dist/
cp install.sh dist/
cp uninstall.sh dist/
echo "✓ Files copied"
echo ""
# Package
echo "→ Packaging archive..."
tar -czf kaibrowser-linux.tar.gz --transform 's|^dist|kaibrowser|' dist/
echo "✓ Created kaibrowser-linux.tar.gz"
echo ""
# Confirm release
read -p "Push tag $TAG and create GitHub release? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Build complete. Archive ready but not released."
    exit 0
fi
# Tag, release and upload
if [ "$TAG_EXISTS" -eq 1 ]; then
    echo "→ Uploading to existing release $TAG..."
    gh release upload "$TAG" kaibrowser-linux.tar.gz --clobber
else
    echo "→ Creating tag $TAG..."
    git tag "$TAG"
    git push origin "$TAG"
    echo "✓ Tag pushed"
    echo ""
    echo "→ Creating GitHub release..."
    gh release create "$TAG" kaibrowser-linux.tar.gz \
        --title "Kai Browser $TAG" \
        --notes "Kai Browser $VERSION release" \
        --latest
fi
echo "✓ Release updated"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Done! Released $TAG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"