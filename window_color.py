#!/Users/bfeld/.claude/iterm/.venv/bin/python3
"""
Changes iTerm2 window background and foreground colors.
Usage: window_color.py [color]  (e.g., white, black, red)
       window_color.py          (cycles to next color)
"""
import iterm2
import sys
import os


def get_ancestor_pids():
    """Walk up the process tree and return all ancestor PIDs."""
    pids = set()
    try:
        pid = os.getpid()
        while pid > 1:
            pids.add(pid)
            # Get parent PID
            with open(f'/proc/{pid}/stat', 'r') as f:
                stat = f.read().split()
                pid = int(stat[3])  # ppid is 4th field
    except FileNotFoundError:
        # macOS doesn't have /proc, use subprocess
        import subprocess
        pid = os.getpid()
        while pid > 1:
            pids.add(pid)
            try:
                result = subprocess.run(
                    ['ps', '-o', 'ppid=', '-p', str(pid)],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    break
                pid = int(result.stdout.strip())
            except (ValueError, subprocess.SubprocessError):
                break
    return pids


async def find_session_by_process_tree(app):
    """Find the iTerm session that is an ancestor of our process."""
    ancestor_pids = get_ancestor_pids()

    for window in app.terminal_windows:
        for tab in window.tabs:
            for session in tab.sessions:
                try:
                    session_pid = await session.async_get_variable('pid')
                    if session_pid and int(session_pid) in ancestor_pids:
                        return session
                except Exception:
                    continue
    return None

# ====== CONFIGURATION SECTION ======
# List the color names you want to cycle through:
COLOR_SEQUENCE = ["red", "green", "blue", "purple", "orange", "black", "white"]

# RGB values (0–255) - Default: 10% intensity for visible but subtle tints
BASE_COLORS_255 = {
    "red":    (25, 0, 0),      # 10% red (default)
    "green":  (0, 25, 0),      # 10% green (default)
    "blue":   (0, 0, 25),      # 10% blue (default)
    "purple": (16, 0, 25),     # 10% purple (67% red, 100% blue)
    "pink":   (16, 0, 25),     # Same as purple (synonym)
    "orange": (25, 8, 0),      # 10% orange (100% red, 33% green)
    "brown":  (25, 8, 0),      # Same as orange (synonym)
    "black":  (0, 0, 0),       # Reset to black (no tint)
    "white":  (255, 255, 255), # Bright white for flash
    # Softer "done" colors - noticeable but not harsh
    "done":   (50, 50, 55),    # Soft gray - default done indicator
    "dim":    (35, 35, 40),    # Very subtle lift
    "glow":   (60, 50, 35),    # Warm amber glow
    "cool":   (35, 45, 60),    # Cool blue tint
}

# Foreground colors - dark for light backgrounds, light for dark backgrounds
FOREGROUND_COLORS_255 = {
    "white":  (0, 0, 0),       # Black text on white background
    "default": (255, 255, 255), # White text on dark backgrounds
}

# Factor to darken colors; 1.0 = use values as-is (default)
DARKEN_FACTOR = 1.0
# ====== END CONFIGURATION SECTION ======


def make_dark_color(r_255: int, g_255: int, b_255: int, factor: float) -> iterm2.Color:
    """Return a darkened iterm2.Color from 8-bit RGB and darken factor.

    Note: iterm2.Color expects 8-bit values (0-255), not 16-bit.
    """
    r = int(r_255 * factor)
    g = int(g_255 * factor)
    b = int(b_255 * factor)
    return iterm2.Color(r, g, b)


def build_dark_backgrounds():
    """Build a list of (name, Color) in the chosen order."""
    backgrounds = []
    for name in COLOR_SEQUENCE:
        if name not in BASE_COLORS_255:
            # Skip unknown names silently
            continue
        r, g, b = BASE_COLORS_255[name]
        dark_color = make_dark_color(r, g, b, DARKEN_FACTOR)
        backgrounds.append((name, dark_color))
    return backgrounds


def color_key(c: iterm2.Color):
    return (c.red, c.green, c.blue)


async def change_session_background(session, backgrounds, target_color=None):
    """
    backgrounds: list of (name, iterm2.Color)
    target_color: optional color name to set (e.g., "red", "blue")

    If target_color is provided, sets that specific color.
    Otherwise, cycles to the next dark color based on current background.
    """
    profile = await session.async_get_profile()

    if target_color:
        # Set specific color by name
        for name, color in backgrounds:
            if name == target_color:
                next_bg = color
                break
        else:
            # Color name not found, ignore
            return
    else:
        # Cycle to next color
        current_background = profile.background_color
        color_list = [bg for (_, bg) in backgrounds]
        color_tuples = [color_key(bg) for bg in color_list]
        current_tuple = color_key(current_background)

        try:
            idx = color_tuples.index(current_tuple)
        except ValueError:
            # If current color isn't one of ours, start from first dark color
            idx = -1

        next_idx = (idx + 1) % len(color_list)
        next_bg = color_list[next_idx]

    # Set background color directly on the session's profile
    # This affects only this session, not the base profile
    # Must set both regular AND dark mode colors (for profiles with separate light/dark mode)
    await profile.async_set_background_color(next_bg)
    await profile.async_set_background_color_dark(next_bg)

    # Set foreground color based on background
    if target_color == "white":
        # Dark text on white background
        fg_r, fg_g, fg_b = FOREGROUND_COLORS_255["white"]
    else:
        # Light text on dark backgrounds
        fg_r, fg_g, fg_b = FOREGROUND_COLORS_255["default"]

    fg_color = iterm2.Color(fg_r, fg_g, fg_b)
    await profile.async_set_foreground_color(fg_color)
    await profile.async_set_foreground_color_dark(fg_color)
    await profile.async_set_bold_color(fg_color)
    await profile.async_set_bold_color_dark(fg_color)


async def main(connection):
    app = await iterm2.app.async_get_app(connection)

    # Get optional color argument from command line
    target_color = sys.argv[1].lower() if len(sys.argv) > 1 else None

    backgrounds = build_dark_backgrounds()
    if not backgrounds:
        # Nothing configured, nothing to do
        return

    # Strategy 1: Try ITERM_SESSION_ID environment variable
    session_id = os.environ.get('ITERM_SESSION_ID')
    if session_id:
        # Extract the actual session ID (format: w0t0p0:actual-session-id)
        if ':' in session_id:
            session_id = session_id.split(':', 1)[1]
        session = app.get_session_by_id(session_id)
        if session:
            await change_session_background(session, backgrounds, target_color)
            return

    # Strategy 2: Find session by walking process tree
    session = await find_session_by_process_tree(app)
    if session:
        await change_session_background(session, backgrounds, target_color)
        return

    # Strategy 3: Fallback to current focused session only
    window = app.current_window
    if window:
        tab = window.current_tab
        if tab:
            session = tab.current_session
            if session:
                await change_session_background(session, backgrounds, target_color)


iterm2.run_until_complete(main)
