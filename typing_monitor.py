#!/Users/bfeld/.claude/iterm/.venv/bin/python3
"""
Background daemon that monitors keystrokes and changes window color on typing.
When user types, flips the screen back to black.

Usage: typing_monitor.py start|stop
"""
import sys
import os
import signal
import subprocess

# Path to the venv Python and scripts
VENV_PYTHON = os.path.expanduser('~/.claude/iterm/.venv/bin/python3')
SCRIPT_DIR = os.path.expanduser('~/.claude/iterm')


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


def find_session_id_by_process_tree():
    """Find the iTerm session ID by matching process tree."""
    import iterm2

    ancestor_pids = get_ancestor_pids()

    async def find_session(connection):
        app = await iterm2.async_get_app(connection)
        for window in app.terminal_windows:
            for tab in window.tabs:
                for session in tab.sessions:
                    try:
                        session_pid = await session.async_get_variable('pid')
                        if session_pid and int(session_pid) in ancestor_pids:
                            return session.session_id
                    except Exception:
                        continue
        return None

    try:
        return iterm2.run_until_complete(find_session)
    except Exception:
        return None


def get_pid_file(session_id):
    """Get session-specific PID file."""
    # Sanitize for filename
    safe_id = session_id.replace(':', '_').replace('/', '_') if session_id else 'default'
    return f'/tmp/iterm_typing_monitor_{safe_id}.pid'


def run_monitor():
    """Run the keystroke monitor (called in background process)."""
    import iterm2

    # Get session ID from environment (passed by start())
    session_id = os.environ.get('TYPING_MONITOR_SESSION_ID', '')

    async def main(connection):
        app = await iterm2.async_get_app(connection)

        # Find the actual session object
        target_session = app.get_session_by_id(session_id) if session_id else None

        # Use session ID for KeystrokeMonitor if available
        monitor_session = session_id if session_id else None

        async with iterm2.KeystrokeMonitor(connection, session=monitor_session) as mon:
            while True:
                keystroke = await mon.async_get()

                # Any keystroke clears the tab color (resets title bar)
                if target_session:
                    try:
                        profile = await target_session.async_get_profile()
                        # Clear tab color (reset title bar to default)
                        await profile.async_set_use_tab_color(False)
                        await profile.async_set_use_tab_color_dark(False)
                    except Exception:
                        pass
                else:
                    # Fallback: use tab_color.py (will use process tree)
                    subprocess.Popen(
                        [VENV_PYTHON,
                         os.path.join(SCRIPT_DIR, 'tab_color.py'),
                         'clear'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

    try:
        iterm2.run_until_complete(main, retry=True)
    except Exception:
        pass


def stop_process(session_id=None):
    """Stop any running monitor process for this session."""
    # If no session_id provided, try to detect it
    if not session_id:
        session_id = os.environ.get('ITERM_SESSION_ID', '')
        if not session_id:
            session_id = find_session_id_by_process_tree()

    pid_file = get_pid_file(session_id)
    if os.path.exists(pid_file):
        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, ValueError, FileNotFoundError, PermissionError):
            pass
        try:
            os.remove(pid_file)
        except FileNotFoundError:
            pass


def start():
    """Start monitor as detached background process."""
    # Detect the iTerm session ID BEFORE detaching
    session_id = os.environ.get('ITERM_SESSION_ID', '')
    if session_id and ':' in session_id:
        session_id = session_id.split(':', 1)[1]

    if not session_id:
        # Fall back to process tree detection
        session_id = find_session_id_by_process_tree()

    stop_process(session_id)

    # Pass session ID to the daemon via environment variable
    env = os.environ.copy()
    if session_id:
        env['TYPING_MONITOR_SESSION_ID'] = session_id

    proc = subprocess.Popen(
        [sys.executable, __file__, 'run'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )

    pid_file = get_pid_file(session_id)
    with open(pid_file, 'w') as f:
        f.write(str(proc.pid))

    print(f"Typing monitor started (pid: {proc.pid}, session: {session_id or 'unknown'})")


def stop():
    """Stop the monitor."""
    session_id = os.environ.get('ITERM_SESSION_ID', '')
    if session_id and ':' in session_id:
        session_id = session_id.split(':', 1)[1]
    if not session_id:
        session_id = find_session_id_by_process_tree()

    stop_process(session_id)
    print("Typing monitor stopped")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: typing_monitor.py start|stop')
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == 'start':
        start()
    elif cmd == 'stop':
        stop()
    elif cmd == 'run':
        run_monitor()
