#!/usr/bin/env bash
set -euo pipefail

echo "============================================"
echo "  d2rhelper setup"
echo "============================================"
echo ""

# ---------- Python ----------
if ! command -v python3 &>/dev/null; then
  echo "Error: Python 3 is not installed."
  echo "Install Python 3.12+ from https://www.python.org/downloads/"
  exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 12 ]); then
  echo "Error: Python 3.12+ required, found $PY_VERSION."
  echo "Install Python 3.12+ from https://www.python.org/downloads/"
  exit 1
fi
echo "[ok] Python $PY_VERSION"

# ---------- uv ----------
if ! command -v uv &>/dev/null; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # shellcheck source=/dev/null
  export PATH="$HOME/.local/bin:$PATH"
  if ! command -v uv &>/dev/null; then
    echo "Error: uv installation failed. Install manually: https://docs.astral.sh/uv/"
    exit 1
  fi
fi
echo "[ok] uv $(uv --version 2>/dev/null | head -1)"

# ---------- deps ----------
echo ""
echo "Installing Python dependencies..."
uv sync

# ---------- game data ----------
echo ""
echo "Extracting game data from Diablo II: Resurrected..."
uv run python scripts/extract_txt.py
echo "[ok] Game data extracted."

# ---------- frontend ----------
if ! command -v npm &>/dev/null; then
  echo ""
  echo "Error: npm is required to build the frontend."
  echo "Install Node.js from https://nodejs.org/"
  exit 1
fi
echo "[ok] npm found"
echo ""
echo "Building frontend..."
npm --prefix frontend install --silent
npm --prefix frontend run build
echo "[ok] Frontend built."

# ---------- .env ----------
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo ""
    echo "[!] Created .env from .env.example."
    echo "    For the AI chat to work, get a free API key at:"
    echo "    https://aistudio.google.com/apikey"
    echo "    Then open .env and set GEMINI_API_KEY=your-key-here"
  fi
else
  echo ""
  echo "[ok] .env already exists."
fi

echo ""
echo "============================================"
echo "  Setup complete!"
echo ""
echo "  Launch the app:"
echo "    uv run d2rhelper"
echo ""
echo "  Then open http://127.0.0.1:8000 in your browser."
echo "============================================"
