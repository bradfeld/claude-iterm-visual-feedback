#!/Users/bfeld/.claude/iterm/.venv/bin/python3
"""
Sets iTerm2 tab/title bar color.
Usage: tab_color.py [color]  (e.g., white, dark, clear)
       tab_color.py          (defaults to dark)

Use 'white' to invert the title bar when Claude finishes.
Use 'clear' to reset when you start typing.
"""
import iterm2
import sys
import os
import subprocess


def get_ancestor_pids():
    """Walk up the process tree and return all ancestor PIDs."""
    pids = set()
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


# Tab colors
TAB_COLORS = {
    "white": (255, 255, 255),   # White title bar (inverted - attention!)
    "light": (220, 220, 220),   # Light gray
    "dark": (30, 30, 40),       # Dark blue-gray (subtle)
    "blue": (20, 40, 80),       # Dark blue
    "purple": (50, 30, 70),     # Dark purple
    "green": (20, 50, 30),      # Dark green
    "red": (60, 20, 20),        # Dark red
    "orange": (70, 40, 10),     # Dark orange
    "clear": None,              # Remove tab color (reset to default)
}


async def main(connection):
    app = await iterm2.app.async_get_app(connection)

    # Get color argument (default to "dark")
    color_name = sys.argv[1].lower() if len(sys.argv) > 1 else "dark"

    # Find the session (tab color is set via session's profile)
    session_id = os.environ.get('ITERM_SESSION_ID')
    if session_id and ':' in session_id:
        session_id = session_id.split(':', 1)[1]
        session = app.get_session_by_id(session_id)
    else:
        session = await find_session_by_process_tree(app)

    if not session:
        # Fallback to current session
        window = app.current_window
        if window and window.current_tab:
            session = window.current_tab.current_session

    if not session:
        return

    # Get the session's profile
    profile = await session.async_get_profile()

    if color_name == "clear" or color_name not in TAB_COLORS:
        # Disable tab color (reset to default)
        await profile.async_set_use_tab_color(False)
        await profile.async_set_use_tab_color_dark(False)
    else:
        r, g, b = TAB_COLORS[color_name]
        color = iterm2.Color(r, g, b)

        # Enable tab color and set it (both light and dark mode)
        await profile.async_set_use_tab_color(True)
        await profile.async_set_use_tab_color_dark(True)
        await profile.async_set_tab_color(color)
        await profile.async_set_tab_color_dark(color)


iterm2.run_until_complete(main)
