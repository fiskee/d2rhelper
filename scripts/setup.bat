@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   d2rhelper setup
echo ============================================
echo.

REM ---------- Python ----------
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    echo Install Python 3.12+ from https://www.python.org/downloads/
    exit /b 1
)

for /f "tokens=2" %%v in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PY_VER=%%v
echo [ok] Python %PY_VER%

REM ---------- uv ----------
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    where uv >nul 2>nul
    if %errorlevel% neq 0 (
        echo Error: uv installation failed. Install manually: https://docs.astral.sh/uv/
        exit /b 1
    )
)
echo [ok] uv found

REM ---------- deps ----------
echo.
echo Installing Python dependencies...
uv sync

REM ---------- game data ----------
echo.
echo Extracting game data from Diablo II: Resurrected...
uv run python scripts\extract_txt.py
echo [ok] Game data extracted.

REM ---------- .env ----------
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo.
        echo [!] Created .env from .env.example.
        echo     For the AI chat to work, get a free API key at:
        echo     https://aistudio.google.com/apikey
        echo     Then open .env and set GEMINI_API_KEY=your-key-here
    )
) else (
    echo.
    echo [ok] .env already exists.
)

echo.
echo ============================================
echo   Setup complete^^!
echo.
echo   Launch the app:
echo     uv run d2rhelper
echo.
echo   Then open http://127.0.0.1:8000 in your browser.
echo ============================================
