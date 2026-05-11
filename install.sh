#!/bin/zsh
# One-shot installer for forensic-analyst.
# Run from inside the project directory:
#   bash install.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "==============================================================="
echo "  Forensic Analyst — installer"
echo "  Installing to: $PROJECT_DIR"
echo "==============================================================="
echo

# 1. Check Python 3.10+
if ! command -v python3 >/dev/null; then
  echo "ERROR: python3 is not installed."
  echo "Install it from https://www.python.org/downloads/ and re-run."
  exit 1
fi
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_OK=$(python3 -c 'import sys; print(int(sys.version_info >= (3, 10)))')
if [ "$PY_OK" != "1" ]; then
  echo "ERROR: Python 3.10+ required (found $PY_VERSION)."
  echo "Install a newer Python from https://www.python.org/downloads/"
  exit 1
fi
echo "✓ Python $PY_VERSION found"

# 2. Create venv
if [ ! -d ".venv" ]; then
  echo "→ Creating virtual environment..."
  python3 -m venv .venv
fi
echo "✓ Virtual environment ready"

# 3. Install dependencies
echo "→ Installing dependencies..."
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# 4. Set up API key
if [ -f "$HOME/.anthropic-key" ] && [ -s "$HOME/.anthropic-key" ]; then
  echo "✓ API key already at ~/.anthropic-key (using existing one)"
else
  echo
  echo "→ Setting up your Anthropic API key."
  echo "  If you don't have one, create one at: https://console.anthropic.com/settings/keys"
  echo
  bash "$PROJECT_DIR/setup-key.sh"
fi

# 5. Install Desktop launcher
LAUNCHER_SRC="$PROJECT_DIR/Forensic Analyst.command"
LAUNCHER_DST="$HOME/Desktop/Forensic Analyst.command"
if [ -f "$LAUNCHER_SRC" ]; then
  cp "$LAUNCHER_SRC" "$LAUNCHER_DST"
  chmod +x "$LAUNCHER_DST"
  echo "✓ Desktop launcher installed: $LAUNCHER_DST"
fi

# 6. Add shell alias
if ! grep -q "^forensic()" "$HOME/.zshrc" 2>/dev/null; then
  cat >> "$HOME/.zshrc" <<EOF

# Forensic financial statement analyst
forensic() {
  if [ -z "\$1" ]; then
    echo "Usage: forensic TICKER [--compare] [--form 10-Q]"
    return 1
  fi
  ( cd "$PROJECT_DIR" && .venv/bin/python forensic_analyst.py "\$@" )
}
EOF
  echo "✓ Added 'forensic' alias to ~/.zshrc"
else
  echo "✓ 'forensic' alias already in ~/.zshrc"
fi

echo
echo "==============================================================="
echo "  Installation complete!"
echo "==============================================================="
echo
echo "Try it out, three ways:"
echo
echo "  1. Double-click 'Forensic Analyst.command' on your Desktop"
echo
echo "  2. Open a NEW Terminal window, then run:"
echo "       forensic AAPL"
echo
echo "  3. From this terminal, run:"
echo "       .venv/bin/python forensic_analyst.py AAPL"
echo
echo "Reports are saved in: ~/Documents/forensic-reports/"
echo
