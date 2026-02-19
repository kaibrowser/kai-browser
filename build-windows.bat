@echo off
setlocal enabledelayedexpansion

echo =====================================
echo   Kai Browser - Windows Build ^& Release
echo =====================================
echo.

:: Activate venv
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo X Virtual environment not found. Run 'python kaibrowser.py' first to create it.
    exit /b 1
)

:: Get version from updater.py
for /f "tokens=2 delims==" %%a in ('findstr /r "VERSION *= *\"" updater.py') do (
    set "RAW=%%a"
)
set "VERSION=%RAW: =%"
set "VERSION=%VERSION:"=%"
if "%VERSION%"=="" (
    echo X Could not read VERSION from updater.py
    exit /b 1
)
set "TAG=v%VERSION%"
echo Version: %VERSION% (tag: %TAG%)
echo.

:: Check if tag already exists on remote
git ls-remote --tags origin | findstr "refs/tags/%TAG%" >nul 2>&1
if %errorlevel%==0 (
    echo X Tag %TAG% already exists on GitHub. Update VERSION in updater.py first.
    exit /b 1
)

:: Install Nuitka if missing
pip show nuitka >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Nuitka...
    pip install nuitka zstandard
)

:: Compile
echo Building with Nuitka...
python -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=kai-browser_logo.ico ^
    --include-data-file=kai-browser_logo.png=kai-browser_logo.png ^
    --enable-plugin=pyqt6 ^
    --include-module=selenium ^
    --include-module=webdriver_manager ^
    --include-module=keyring ^
    --include-module=requests ^
    --include-module=PIL ^
    --include-module=qrcode ^
    --include-module=numpy ^
    --include-module=pandas ^
    --include-module=bs4 ^
    --include-module=lxml ^
    --include-module=cryptography ^
    --output-dir=dist ^
    --output-filename=kaibrowser.exe ^
    --assume-yes-for-download ^
    launch_browser.py

if %errorlevel% neq 0 (
    echo X Nuitka build failed
    exit /b 1
)
echo Build complete
echo.

:: Copy files to dist
echo Copying files to dist...
copy kai-browser_logo.png dist\ >nul 2>&1
copy DISCLAIMER.md dist\ >nul 2>&1
copy README.md dist\ >nul 2>&1
copy LICENSE.save dist\ >nul 2>&1
copy TERMS_OF_SERVICE.md dist\ >nul 2>&1
echo Files copied
echo.

:: Package
echo Packaging archive...
powershell -Command "Compress-Archive -Path dist\* -DestinationPath kaibrowser-windows.zip -Force"
echo Created kaibrowser-windows.zip
echo.

:: Confirm release
set /p "CONFIRM=Push tag %TAG% and create GitHub release? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Build complete. Archive ready but not released.
    exit /b 0
)

:: Tag and push
echo Creating tag %TAG%...
git tag %TAG%
git push origin %TAG%
echo Tag pushed
echo.

:: Create GitHub release and upload
echo Creating GitHub release...
gh release create %TAG% kaibrowser-windows.zip ^
    --title "Kai Browser %TAG%" ^
    --notes "Kai Browser %VERSION% release" ^
    --latest
echo Release created
echo.

echo =====================================
echo   Done! Released %TAG%
echo =====================================