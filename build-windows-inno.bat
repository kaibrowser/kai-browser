@echo off
setlocal enabledelayedexpansion
echo =====================================
echo   Kai Browser - Windows Installer Build
echo =====================================
echo.

:: ── Config ────────────────────────────────────────────────
set "PYTHON_VERSION=3.12.10"
set "PYTHON_VERSION_SHORT=3.12"
set "PYTHON_EMBED_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip"
set "PYTHON_EMBED_ZIP=python-embed.zip"
set "PYTHON_EMBED_DIR=python-embedded"
set "PIP_URL=https://bootstrap.pypa.io/pip/pip.pyz"

:: Activate venv
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo X Virtual environment not found. Run 'python kaibrowser.py' first to create it.
    exit /b 1
)

:: Get version from updater.py
python -c "exec(open('updater.py').read().split('class')[0]); print(VERSION)" > _version.tmp
set /p VERSION=<_version.tmp
del _version.tmp
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
    echo Tag %TAG% already exists on GitHub. Will upload to existing release.
    set "TAG_EXISTS=1"
) else (
    set "TAG_EXISTS=0"
)

:: ── Download embeddable Python ────────────────────────────
echo Checking for embedded Python %PYTHON_VERSION%...
if not exist "%PYTHON_EMBED_DIR%\python.exe" (
    echo Downloading Python %PYTHON_VERSION% embeddable package...
    if exist "%PYTHON_EMBED_ZIP%" del "%PYTHON_EMBED_ZIP%"
    curl -L "%PYTHON_EMBED_URL%" -o "%PYTHON_EMBED_ZIP%"
    if %errorlevel% neq 0 (
        echo X Failed to download Python embeddable package
        exit /b 1
    )
    if exist "%PYTHON_EMBED_DIR%" rmdir /s /q "%PYTHON_EMBED_DIR%"
    mkdir "%PYTHON_EMBED_DIR%"
    tar -xf "%PYTHON_EMBED_ZIP%" -C "%PYTHON_EMBED_DIR%"
    del "%PYTHON_EMBED_ZIP%"

    :: Download pip into embedded Python
    echo Downloading pip...
    curl -L "%PIP_URL%" -o "%PYTHON_EMBED_DIR%\pip.pyz"
    if %errorlevel% neq 0 (
        echo X Failed to download pip
        exit /b 1
    )

    :: Enable site-packages in embedded Python by uncommenting import site
    set "PTH_FILE=%PYTHON_EMBED_DIR%\python312._pth"
    if exist "!PTH_FILE!" (
        powershell -Command "(Get-Content '!PTH_FILE!') -replace '#import site', 'import site' | Set-Content '!PTH_FILE!'"
        echo Enabled site-packages in embedded Python
    )
    echo Embedded Python ready
) else (
    echo Embedded Python already present
)
echo.

:: Check Inno Setup is installed
echo Checking Inno Setup...
set "INNO=C:\PROGRA~2\InnoSetup6\ISCC.exe"
if not exist "%INNO%" (
    set "INNO=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if not exist "%INNO%" (
    echo X Inno Setup 6 not found
    echo   Download from: https://jrsoftware.org/isdl.php
    exit /b 1
)
echo Inno Setup found

:: Install Nuitka if missing
pip show nuitka >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Nuitka...
    pip install nuitka zstandard
)

:: ── Compile ───────────────────────────────────────────────
echo Building with Nuitka...
python -m nuitka ^
    --standalone ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=kai-browser_logo.ico ^
    --include-data-file=kai-browser_logo.png=kai-browser_logo.png ^
    --enable-plugin=pyqt6 ^
    --include-module=selenium ^
    --include-module=webdriver_manager ^
    --include-module=keyring ^
    --include-module=requests ^
    --include-module=anthropic ^
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

:: ── Copy files to dist ────────────────────────────────────
echo Copying files to dist...
set "DIST_DIR=dist\launch_browser.dist"
copy kai-browser_logo.png "%DIST_DIR%\" >nul 2>&1
copy DISCLAIMER.md "%DIST_DIR%\" >nul 2>&1
copy README.md "%DIST_DIR%\" >nul 2>&1
copy LICENSE.save "%DIST_DIR%\" >nul 2>&1
copy TERMS_OF_SERVICE.md "%DIST_DIR%\" >nul 2>&1

:: Copy embedded Python into dist
echo Copying embedded Python into dist...
xcopy /e /i /q "%PYTHON_EMBED_DIR%" "%DIST_DIR%\python-embedded\"
echo Files copied
echo.

:: ── Generate Inno Setup script ────────────────────────────
echo Generating installer script...
set "ISS_FILE=installer.iss"
(
echo #define MyAppName "Kai Browser"
echo #define MyAppVersion "%VERSION%"
echo #define MyAppPublisher "Kai Browser"
echo #define MyAppURL "https://kaibrowser.com"
echo #define MyAppExeName "kaibrowser.exe"
echo.
echo [Setup]
echo AppId={{B8F3C2A1-4E7D-4F9B-8C2E-1A3D5F7B9E0C}
echo AppName={#MyAppName}
echo AppVersion={#MyAppVersion}
echo AppPublisher={#MyAppPublisher}
echo AppPublisherURL={#MyAppURL}
echo AppSupportURL={#MyAppURL}
echo AppUpdatesURL={#MyAppURL}
echo DefaultDirName={localappdata}\{#MyAppName}
echo DefaultGroupName={#MyAppName}
echo AllowNoIcons=yes
echo OutputDir=.
echo OutputBaseFilename=kaibrowser-windows-setup
echo SetupIconFile=kai-browser_logo.ico
echo Compression=lzma
echo SolidCompression=yes
echo WizardStyle=modern
echo PrivilegesRequired=lowest
echo.
echo [Languages]
echo Name: "english"; MessagesFile: "compiler:Default.isl"
echo.
echo [Tasks]
echo Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
echo.
echo [Files]
echo Source: "dist\launch_browser.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
echo.
echo [Icons]
echo Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
echo Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
echo Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
echo.
echo [Registry]
echo Root: HKCU; Subkey: "Software\KaiBrowser"; ValueType: string; ValueName: "EmbeddedPython"; ValueData: "{app}\python-embedded\python.exe"; Flags: createvalueifdoesntexist
echo.
echo [Run]
echo Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
) > "%ISS_FILE%"
echo Generated installer.iss
echo.

:: ── Build installer ───────────────────────────────────────
echo Building installer...
"%INNO%" "%ISS_FILE%"
if %errorlevel% neq 0 (
    echo X Installer build failed
    exit /b 1
)
echo Created kaibrowser-windows-setup.exe
echo.

:: ── Confirm release ───────────────────────────────────────
set /p "CONFIRM=Push tag %TAG% and create GitHub release? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Build complete. Installer ready but not released.
    exit /b 0
)

:: ── Tag and release ───────────────────────────────────────
gh release view %TAG% >nul 2>&1
if %errorlevel%==0 (
    set "RELEASE_EXISTS=1"
) else (
    set "RELEASE_EXISTS=0"
)

echo Tag exists: %TAG_EXISTS% ^| Release exists: %RELEASE_EXISTS%

if "%TAG_EXISTS%"=="1" if "%RELEASE_EXISTS%"=="1" (
    echo Uploading to existing release %TAG%...
    gh release upload %TAG% kaibrowser-windows-setup.exe --clobber
    goto done
)

if "%TAG_EXISTS%"=="1" if "%RELEASE_EXISTS%"=="0" (
    echo Creating release for existing tag %TAG%...
    gh release create %TAG% kaibrowser-windows-setup.exe ^
        --title "Kai Browser %TAG%" ^
        --notes "Kai Browser %VERSION% release" ^
        --latest
    goto done
)

echo Creating tag %TAG%...
git tag %TAG%
git push origin %TAG%
echo Tag pushed
echo.
echo Creating GitHub release...
gh release create %TAG% kaibrowser-windows-setup.exe ^
    --title "Kai Browser %TAG%" ^
    --notes "Kai Browser %VERSION% release" ^
    --latest

:done
echo Release updated
echo.
echo =====================================
echo   Done! Released %TAG%
echo =====================================