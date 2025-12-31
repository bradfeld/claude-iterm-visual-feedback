#!/bin/bash
#
# Install Claude Code iTerm Visual Feedback
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.claude/iterm"

echo "Claude Code iTerm Visual Feedback Installer"
echo "============================================"
echo ""

# Check for iTerm2
if [[ "$TERM_PROGRAM" != "iTerm.app" ]]; then
    echo "Warning: Not running in iTerm2. This tool is designed for iTerm2."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create target directory
echo "Creating $TARGET_DIR..."
mkdir -p "$TARGET_DIR"

# Copy scripts
echo "Copying scripts..."
cp "$SCRIPT_DIR/window_color.py" "$TARGET_DIR/"
cp "$SCRIPT_DIR/typing_monitor.py" "$TARGET_DIR/"
cp "$SCRIPT_DIR/animate_title.py" "$TARGET_DIR/"

# Create virtual environment if it doesn't exist
if [[ ! -d "$TARGET_DIR/.venv" ]]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$TARGET_DIR/.venv"
    echo "Installing iterm2 package..."
    "$TARGET_DIR/.venv/bin/pip" install --quiet iterm2
else
    echo "Virtual environment already exists, skipping..."
fi

# Test iterm2 import
echo "Testing iterm2 module..."
if "$TARGET_DIR/.venv/bin/python3" -c "import iterm2" 2>/dev/null; then
    echo "✓ iterm2 module working"
else
    echo "✗ Failed to import iterm2 module"
    echo "  Try: $TARGET_DIR/.venv/bin/pip install iterm2"
    exit 1
fi

echo ""
echo "============================================"
echo "Installation complete!"
echo ""
echo "Next steps:"
echo ""
echo "1. Enable iTerm2 Python API:"
echo "   iTerm2 → Preferences → General → Magic → Enable Python API"
echo ""
echo "2. Add hooks to ~/.claude/settings.json:"
echo ""
cat << 'EOF'
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/iterm/.venv/bin/python3 ~/.claude/iterm/animate_title.py start"
          },
          {
            "type": "command",
            "command": "~/.claude/iterm/.venv/bin/python3 ~/.claude/iterm/typing_monitor.py stop"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/iterm/.venv/bin/python3 ~/.claude/iterm/window_color.py white"
          },
          {
            "type": "command",
            "command": "~/.claude/iterm/.venv/bin/python3 ~/.claude/iterm/animate_title.py stop"
          },
          {
            "type": "command",
            "command": "~/.claude/iterm/.venv/bin/python3 ~/.claude/iterm/typing_monitor.py start"
          }
        ]
      }
    ]
  }
}
EOF
echo ""
echo "3. Test it:"
echo "   $TARGET_DIR/.venv/bin/python3 $TARGET_DIR/window_color.py white"
echo "   # Your pane should flash white"
echo ""
