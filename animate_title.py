#!/Users/bfeld/.claude/iterm/.venv/bin/python3
"""
Background process that animates iTerm session name with moon phases.
Usage: animate_title.py start|stop|run
"""
import sys
import os
import signal
import subprocess

MOON_PHASES = ['🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘']

# All the animation options for the end of title
STARS = ['🌟', '✨', '💫', '⭐']
PLANETS = ['🪐', '🌍', '🌎', '🌏']
ROCKET = ['🚀', '·🚀', '.·🚀', '·.·🚀', ':·.·🚀', '·:·.·🚀', '.·:·.·🚀']
BRAILLE = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']
HOURGLASS = ['⏳', '⌛']
ARROWS = ['🔄', '🔃']
CIRCLE = ['◐', '◓', '◑', '◒']
CAT = ['🐱', '😺', '😸', '😹']
MUSIC = ['🎵', '🎶', '♪', '♫']
RAINBOW = ['🟥', '🟧', '🟨', '🟩', '🟦', '🟪']
THINKING = ['🧠', '💭', '💡']
ROBOT = ['🤖', '🤖']  # Could add eye states
ENERGY = ['⚡', '🔋', '🪫', '🔋']
WAVE = ['～', '〰️', '～', '〰️']
FIRE = ['🔥', '🔥', '🔥', '🔥']
SNOW = ['❄️', '✳️', '❇️', '✴️']

# Selected animations for end of title
END_ANIMATIONS = [STARS, HOURGLASS, RAINBOW, FIRE]

# Fire burst animation (grows and shrinks) - for Stop event
FIRE_BURST = [
    '🔥',
    '🔥🔥',
    '🔥🔥🔥',
    '🔥🔥🔥🔥',
    '🔥🔥🔥🔥🔥',
    '🔥🔥🔥🔥',
    '🔥🔥🔥',
    '🔥🔥',
    '🔥',
]


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


def get_session_id():
    """Get the iTerm session ID from env or process tree."""
    session_id = os.environ.get('ITERM_SESSION_ID', '')
    if session_id and ':' in session_id:
        session_id = session_id.split(':', 1)[1]
    if not session_id:
        session_id = os.environ.get('ANIMATE_TITLE_SESSION_ID', '')
    if not session_id:
        session_id = find_session_id_by_process_tree()
    return session_id


def get_pid_file(session_id=None):
    """Get session-specific PID file."""
    if not session_id:
        session_id = get_session_id() or 'default'
    safe_id = session_id.replace(':', '_').replace('/', '_')
    return f'/tmp/iterm_animation_{safe_id}.pid'


def get_title_file(session_id=None):
    """Get session-specific title file."""
    if not session_id:
        session_id = get_session_id() or 'default'
    safe_id = session_id.replace(':', '_').replace('/', '_')
    return f'/tmp/iterm_original_title_{safe_id}.txt'

REFRESH_RATE = 0.1  # 100ms (faster spin)


def run_animation():
    """Actually run the animation loop (called in background process)."""
    import asyncio
    import iterm2

    # Get session ID from environment (passed by start())
    session_id = os.environ.get('ANIMATE_TITLE_SESSION_ID', '')
    title_file = get_title_file(session_id)

    async def animate_loop(connection):
        app = await iterm2.async_get_app(connection)

        # Find the target session
        session = app.get_session_by_id(session_id) if session_id else None
        if not session:
            # Fallback to current session
            window = app.current_window
            if window and window.current_tab:
                session = window.current_tab.current_session

        if not session:
            return

        # Save original session name
        original_name = session.name or 'Terminal'
        with open(title_file, 'w') as f:
            f.write(original_name)

        idx = 0
        while True:
            moon = MOON_PHASES[idx % len(MOON_PHASES)]

            # Build end animations
            end_section = ''.join(frames[idx % len(frames)] for frames in END_ANIMATIONS)

            title = f'{moon} {original_name} {end_section}'
            try:
                await session.async_set_name(title)
            except Exception:
                pass
            await asyncio.sleep(REFRESH_RATE)
            idx += 1

    async def main(connection):
        await animate_loop(connection)

    try:
        iterm2.run_until_complete(main, retry=True)
    except Exception:
        pass


def run_restore():
    """Actually restore the session name (called in background process)."""
    import iterm2

    session_id = os.environ.get('ANIMATE_TITLE_SESSION_ID', '')
    title_file = get_title_file(session_id)

    if not os.path.exists(title_file):
        return

    with open(title_file) as f:
        original = f.read().strip()

    async def restore(connection):
        app = await iterm2.async_get_app(connection)

        session = app.get_session_by_id(session_id) if session_id else None
        if not session:
            window = app.current_window
            if window and window.current_tab:
                session = window.current_tab.current_session

        if session:
            await session.async_set_name(original)

    try:
        iterm2.run_until_complete(restore)
    except Exception:
        pass

    try:
        os.remove(title_file)
    except FileNotFoundError:
        pass


def run_burst():
    """Play fire burst animation on both sides, then restore name."""
    import asyncio
    import iterm2

    session_id = os.environ.get('ANIMATE_TITLE_SESSION_ID', '')
    title_file = get_title_file(session_id)

    # Read original name
    if os.path.exists(title_file):
        with open(title_file) as f:
            base_title = f.read().strip()
    else:
        base_title = 'Terminal'

    async def burst_animation(connection):
        app = await iterm2.async_get_app(connection)

        session = app.get_session_by_id(session_id) if session_id else None
        if not session:
            window = app.current_window
            if window and window.current_tab:
                session = window.current_tab.current_session

        if not session:
            return

        # Play the burst on both sides
        for fire in FIRE_BURST:
            title = f'{fire} {base_title} {fire}'
            try:
                await session.async_set_name(title)
            except Exception:
                pass
            await asyncio.sleep(0.1)  # 100ms per frame

        # Restore to just the base title
        await session.async_set_name(base_title)

    try:
        iterm2.run_until_complete(burst_animation)
    except Exception:
        pass


def stop_process(session_id=None):
    """Stop any running animation process."""
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
    """Start animation as detached background process."""
    # Detect session ID BEFORE detaching
    session_id = get_session_id()

    stop_process(session_id)

    # Pass session ID to daemon via environment variable
    env = os.environ.copy()
    if session_id:
        env['ANIMATE_TITLE_SESSION_ID'] = session_id

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


def stop():
    """Stop animation and restore name (non-blocking)."""
    session_id = get_session_id()
    stop_process(session_id)

    # Pass session ID to restore process
    env = os.environ.copy()
    if session_id:
        env['ANIMATE_TITLE_SESSION_ID'] = session_id

    subprocess.Popen(
        [sys.executable, __file__, 'restore'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def burst():
    """Play fire burst animation (non-blocking)."""
    session_id = get_session_id()
    stop_process(session_id)

    # Pass session ID to burst process
    env = os.environ.copy()
    if session_id:
        env['ANIMATE_TITLE_SESSION_ID'] = session_id

    subprocess.Popen(
        [sys.executable, __file__, 'run_burst'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: animate_title.py start|stop|burst')
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == 'start':
        start()
    elif cmd == 'stop':
        stop()
    elif cmd == 'burst':
        burst()
    elif cmd == 'run':
        run_animation()
    elif cmd == 'restore':
        run_restore()
    elif cmd == 'run_burst':
        run_burst()
