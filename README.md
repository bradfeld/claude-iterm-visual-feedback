# Claude Code iTerm Visual Feedback

Visual feedback system for [Claude Code](https://claude.ai/claude-code) running in iTerm2. Get immediate visual cues when Claude is thinking vs waiting for your input.

## What It Does

| Event | Visual Feedback |
|-------|-----------------|
| You submit a prompt | Moon phases animate in session title bar |
| Claude stops responding | Your pane flashes white |
| You start typing | Your pane goes back to black |

**Per-session isolation**: Each Claude Code session has independent visual feedback - perfect for multi-pane workflows.

## Demo

When Claude is working:
```
🌒 Your Session Name 🌟⏳🟥🔥
```

When Claude finishes: **Screen flashes white** then waits for your input.

When you start typing: **Screen goes black** (acknowledged!)

## Requirements

- **iTerm2** with Python API enabled
- **macOS** (uses iTerm2's Python API)
- **Python 3.8+**
- **Claude Code CLI**

## Installation

### Quick Install

```bash
git clone https://github.com/bfeld/claude-iterm-visual-feedback.git
cd claude-iterm-visual-feedback
./install.sh
```

### Manual Install

1. **Enable iTerm2 Python API**:
   - iTerm2 → Preferences → General → Magic → Enable Python API ✓

2. **Create the scripts directory**:
   ```bash
   mkdir -p ~/.claude/iterm
   ```

3. **Copy the scripts**:
   ```bash
   cp window_color.py typing_monitor.py animate_title.py ~/.claude/iterm/
   ```

4. **Create Python virtual environment**:
   ```bash
   cd ~/.claude/iterm
   python3 -m venv .venv
   .venv/bin/pip install iterm2
   ```

5. **Configure Claude Code hooks** - Add to `~/.claude/settings.json`:
   ```json
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
   ```

## How It Works

### Session Detection

The scripts use **process tree matching** to identify which iTerm session Claude Code is running in. This works even when `ITERM_SESSION_ID` isn't available to hook subprocesses.

1. Walk up the process tree from the script
2. Match against iTerm session PIDs via the Python API
3. Target only that specific session

### Dark Mode Support

For iTerm profiles with "Use separate colors for light and dark mode" enabled, the scripts set both:
- `background_color` (Light Mode)
- `background_color_dark` (Dark Mode)

## Scripts

| Script | Purpose |
|--------|---------|
| `window_color.py` | Flash screen white/black for a specific session |
| `typing_monitor.py` | Daemon that detects keystrokes and triggers color change |
| `animate_title.py` | Moon phase animation in session title bar |

## Customization

### Change Animation Speed

In `animate_title.py`, adjust:
```python
REFRESH_RATE = 0.1  # seconds between frames (default: 100ms)
```

### Change Animation Icons

In `animate_title.py`, modify the animation arrays:
```python
MOON_PHASES = ['🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘']
END_ANIMATIONS = [STARS, HOURGLASS, RAINBOW, FIRE]
```

### Change Flash Colors

In `window_color.py`, modify `BASE_COLORS_255`:
```python
BASE_COLORS_255 = {
    "white":  (255, 255, 255),  # Flash color
    "black":  (0, 0, 0),        # Return color
    # Add custom colors...
}
```

## Troubleshooting

### No visual feedback

1. **Check iTerm2 Python API is enabled**:
   - iTerm2 → Preferences → General → Magic → Enable Python API

2. **Test the scripts manually**:
   ```bash
   ~/.claude/iterm/.venv/bin/python3 ~/.claude/iterm/window_color.py white
   # Should flash your current pane white
   ```

### Wrong pane flashes

The scripts use process tree detection. If this fails:
1. Check if `ITERM_SESSION_ID` is set in your shell
2. Verify iTerm2 Python API can enumerate sessions

### Animation not visible

iTerm may be showing session names instead of window titles. The updated `animate_title.py` uses `session.async_set_name()` which should work with most iTerm configurations.

## License

MIT License - Feel free to use, modify, and share!

## Credits

Developed for use with [Claude Code](https://claude.ai/claude-code) by Anthropic.
