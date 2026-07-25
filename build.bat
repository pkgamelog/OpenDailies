@echo off
echo ==========================================
echo      OpenDailies Automated Build Process
echo ==========================================

:: 1. Check Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python is not installed or not in PATH. Please install Python 3.12+.
    pause
    exit /b 1
)

:: 2. Check for Virtual Environment (create if missing)
if exist ".venv\Scripts\activate.bat" (
    echo Activating existing .venv...
    call .venv\Scripts\activate.bat
) else (
    echo Creating Virtual Environment (.venv)...
    python -m venv .venv
    call .venv\Scripts\activate.bat
)

:: 3. Install Dependencies
echo Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt >nul 2>&1
echo Ensuring PyInstaller is installed...
pip install pyinstaller >nul 2>&1

:: 4. Check FFmpeg & FFprobe
if not exist "ffmpeg.exe" (
    echo WARNING: ffmpeg.exe not found in root directory. Please place it here.
    pause
    exit /b 1
)
if not exist "ffprobe.exe" (
    echo WARNING: ffprobe.exe not found in root directory. Please place it here.
    pause
    exit /b 1
)

:: 5. Clean old build artifacts to prevent stale files
echo Cleaning old build directories...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "OpenDailies.spec" del "OpenDailies.spec"

:: 6. Run PyInstaller
echo Building executable with PyInstaller...
:: Note: --add-binary is used instead of --add-data for .exe files
pyinstaller --noconfirm --onedir --windowed --name "OpenDailies" --icon "assets\icons\OpenDailies.ico" --add-binary "ffmpeg.exe;." --add-binary "ffprobe.exe;." --add-data "assets;assets" main.py

:: Verify build succeeded
if not exist "dist\OpenDailies\OpenDailies.exe" (
    echo.
    echo BUILD FAILED! Check the PyInstaller errors above.
    pause
    exit /b 1
)

:: 7. Check Inno Setup (Optional)
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "installer.iss" (
    if exist "%ISCC%" (
        echo.
        echo Compiling Installer with Inno Setup...
        "%ISCC%" installer.iss
        echo.
        echo ==========================================
        echo BUILD SUCCESSFUL!
        echo Installer is located in the Installer folder.
        echo ==========================================
    ) else (
        echo.
        echo ==========================================
        echo BUILD SUCCESSFUL!
        echo Inno Setup 6 not found. Skipping installer creation.
        echo Your portable app is ready in: dist\OpenDailies\
        echo ==========================================
    )
) else (
    echo.
    echo ==========================================
    echo BUILD SUCCESSFUL!
    echo installer.iss not found. Skipping installer creation.
    echo Your portable app is ready in: dist\OpenDailies\
    echo ==========================================
)

pause