"""Native Windows Launcher for CodeLens AI.

Robust production launcher implementing:
1. Strict Bundled Runtime: Always executes isolated runtime\\pythonw.exe (no system Python or pip).
2. Single-Instance Protection: Prevents duplicate processes and browser tab spam via Named Mutex.
3. Process Logging: Captures full stdout/stderr into logs/launcher.log.
4. HTTP 200 Health Polling: Confirms Streamlit is fully ready before opening browser EXACTLY ONCE.
5. 30-Second Timeout & Native Error Dialog: Displays [Open Logs], [Retry], [Exit] on failure.
6. Headless Execution: Launches without visible terminal or flashing CMD windows.
"""

from __future__ import annotations

import atexit
import ctypes
from datetime import datetime
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

# Resolve Base Application Directory
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

APP_SCRIPT = APP_DIR / "app.py"
HOST = "127.0.0.1"
DEFAULT_PORT = 8501
STARTUP_TIMEOUT = 30.0  # seconds
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


# Determine Logs Directory and File
def get_log_file() -> Path:
    """Resolve writable logs/launcher.log path."""
    primary_log_dir = APP_DIR / "logs"
    try:
        primary_log_dir.mkdir(parents=True, exist_ok=True)
        test_file = primary_log_dir / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return primary_log_dir / "launcher.log"
    except Exception:
        fallback_log_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CodeLens AI" / "logs"
        fallback_log_dir.mkdir(parents=True, exist_ok=True)
        return fallback_log_dir / "launcher.log"


LOG_FILE = get_log_file()


def log(message: str) -> None:
    """Append a timestamped message to logs/launcher.log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    formatted = f"[{timestamp}] {message}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8", buffering=1) as f:
            f.write(formatted)
    except Exception:
        pass


def get_recent_log_tail(max_lines: int = 15) -> str:
    """Read the last few lines from the launcher log file."""
    if not LOG_FILE.is_file():
        return "(No log output available)"
    try:
        lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = lines[-max_lines:] if len(lines) > max_lines else lines
        return "\n".join(tail) if tail else "(Log file is empty)"
    except Exception as exc:
        return f"(Could not read log: {exc})"


# ==============================================================================
# Single-Instance Mutex & Window Focus (Fix 4)
# ==============================================================================
class SingleInstanceLock:
    """Windows Named Mutex to prevent multiple concurrent launcher instances."""

    MUTEX_NAME = "Local\\CodeLensAI_SingleInstance_Mutex"
    ERROR_ALREADY_EXISTS = 183

    def __init__(self) -> None:
        self.handle = None
        self.already_running = False

    def acquire(self) -> bool:
        """Attempt to acquire named mutex. Returns True if this is the first instance."""
        if sys.platform != "win32":
            return True
        try:
            kernel32 = ctypes.windll.kernel32
            self.handle = kernel32.CreateMutexW(None, True, self.MUTEX_NAME)
            last_err = kernel32.GetLastError()
            if last_err == self.ERROR_ALREADY_EXISTS:
                self.already_running = True
                return False
            return True
        except Exception as exc:
            log(f"[SingleInstance] Warning: Failed to create mutex: {exc}")
            return True

    def release(self) -> None:
        """Release and close mutex handle on exit."""
        if self.handle and sys.platform == "win32":
            try:
                ctypes.windll.kernel32.ReleaseMutex(self.handle)
                ctypes.windll.kernel32.CloseHandle(self.handle)
            except Exception:
                pass
            self.handle = None


def try_focus_existing_window() -> bool:
    """Attempt to bring any existing CodeLens AI browser or window to front."""
    if sys.platform != "win32":
        return False
    try:
        user32 = ctypes.windll.user32
        found_window = False

        def enum_handler(hwnd: int, extra: int) -> bool:
            nonlocal found_window
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                if "CodeLens AI" in title or "localhost:8501" in title:
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    user32.SetForegroundWindow(hwnd)
                    found_window = True
                    return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumWindows(WNDENUMPROC(enum_handler), 0)
        return found_window
    except Exception:
        return False


# ==============================================================================
# Port Management & Server Health Checking (Fix 1)
# ==============================================================================
def find_free_port(starting_port: int = DEFAULT_PORT) -> int:
    """Find an available TCP port starting from starting_port."""
    for port in range(starting_port, starting_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((HOST, port))
                return port
            except OSError:
                continue
    return starting_port


def check_server_health(port: int) -> bool:
    """Check whether Streamlit HTTP server returns HTTP 200 on health / root."""
    endpoints = [
        f"http://{HOST}:{port}/_stcore/health",
        f"http://{HOST}:{port}/",
    ]
    for url in endpoints:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CodeLensAI-Launcher/1.0"},
            )
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
    return False


# ==============================================================================
# Bundled Python Runtime Resolution (H3.4)
# ==============================================================================
def resolve_python_runtime() -> tuple[str | None, str | None]:
    """Locate the bundled Python runtime (runtime\\Scripts\\pythonw.exe or runtime\\Scripts\\python.exe).

    Strictly uses the bundled runtime inside APP_DIR / 'runtime'.
    System Python discovery and runtime pip installation are explicitly disabled.

    Returns:
        tuple[python_exe, error_message]
    """
    runtime_dir = APP_DIR / "runtime"

    # Search candidates strictly within bundled runtime (and local dev fallback if not packaged)
    candidates: list[Path] = [
        runtime_dir / "Scripts" / "pythonw.exe",
        runtime_dir / "Scripts" / "python.exe",
        runtime_dir / "pythonw.exe",
        runtime_dir / "python.exe",
    ]

    # In Linux / AppImage or POSIX environments, check bundled usr/bin/python3 and sys.executable
    if sys.platform != "win32":
        candidates.extend([
            APP_DIR.parent / "usr" / "bin" / "python3",
            APP_DIR / "usr" / "bin" / "python3",
            Path(sys.executable),
        ])

    # In local developer workspace mode (running uncompiled launcher.py), allow local .venv
    if not getattr(sys, "frozen", False):
        for dev_base in [APP_DIR, APP_DIR.parent]:
            candidates.append(dev_base / ".venv" / "Scripts" / "pythonw.exe")
            candidates.append(dev_base / ".venv" / "Scripts" / "python.exe")
            candidates.append(dev_base / ".venv" / "bin" / "python3")
            candidates.append(dev_base / ".venv" / "bin" / "python")

    for candidate in candidates:
        if candidate.is_file():
            # Verify that this runtime can import streamlit
            test_exe = candidate
            if test_exe.name.lower() == "pythonw.exe":
                alt = test_exe.with_name("python.exe")
                if alt.is_file():
                    test_exe = alt
            try:
                res = subprocess.run(
                    [str(test_exe), "-c", "import streamlit, google.genai, pygments"],
                    capture_output=True,
                    timeout=3.0,
                    creationflags=CREATE_NO_WINDOW,
                )
                if res.returncode == 0:
                    log(f"[Runtime] Verified bundled runtime executable: {candidate}")
                    return str(candidate), None
            except Exception as exc:
                log(f"[Runtime] Verification failed for {candidate}: {exc}")

    err = (
        "The bundled Python runtime was not found or is incomplete.\n\n"
        f"Expected path: {runtime_dir / 'Scripts' / 'pythonw.exe'}\n\n"
        "Please reinstall CodeLens AI using CodeLensAI-Setup.exe."
    )
    log(f"[Fatal] {err}")
    return None, err


# ==============================================================================
# Native Dialog for Errors & Timeout (Fix 5)
# ==============================================================================
def show_native_dialog(
    headline: str,
    message: str,
    log_path: Path,
) -> str:
    """Display a native Windows error dialog with buttons: [Open Logs], [Retry], [Exit].

    Returns:
        str: 'retry' or 'exit'
    """
    chosen_action = "exit"

    try:
        import tkinter as tk

        root = tk.Tk()
        root.title("CodeLens AI")
        root.geometry("560x420")
        root.minsize(500, 360)
        root.configure(bg="#18181b")
        root.attributes("-topmost", True)

        # Set window icon if available
        icon_path = APP_DIR / "assets" / "icon.ico"
        if icon_path.is_file():
            try:
                root.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Header Frame
        header_frame = tk.Frame(root, bg="#18181b")
        header_frame.pack(fill="x", padx=24, pady=(20, 10))

        title_lbl = tk.Label(
            header_frame,
            text=f"⚠️ {headline}",
            font=("Segoe UI", 13, "bold"),
            fg="#ef4444",
            bg="#18181b",
            anchor="w",
        )
        title_lbl.pack(fill="x")

        sub_lbl = tk.Label(
            header_frame,
            text="The desktop application encountered a problem during startup.",
            font=("Segoe UI", 9),
            fg="#a1a1aa",
            bg="#18181b",
            anchor="w",
        )
        sub_lbl.pack(fill="x", pady=(2, 0))

        # Details / Log box
        content_frame = tk.Frame(root, bg="#27272a", bd=1, relief="solid")
        content_frame.pack(fill="both", expand=True, padx=24, pady=10)

        text_widget = tk.Text(
            content_frame,
            bg="#09090b",
            fg="#e4e4e7",
            insertbackground="#ffffff",
            font=("Consolas", 9),
            wrap="word",
            padx=10,
            pady=8,
            relief="flat",
        )
        text_widget.pack(fill="both", expand=True)

        full_details = f"{message}\n\n--- [Log file: {log_path}] ---\n{get_recent_log_tail(12)}"
        text_widget.insert("1.0", full_details)
        text_widget.configure(state="disabled")

        # Button Actions
        def on_open_logs() -> None:
            try:
                if log_path.is_file():
                    os.startfile(str(log_path))
            except Exception:
                pass

        def on_retry() -> None:
            nonlocal chosen_action
            chosen_action = "retry"
            root.destroy()

        def on_exit() -> None:
            nonlocal chosen_action
            chosen_action = "exit"
            root.destroy()

        # Button Bar
        btn_bar = tk.Frame(root, bg="#18181b")
        btn_bar.pack(fill="x", padx=24, pady=(5, 20))

        btn_logs = tk.Button(
            btn_bar,
            text="📄 Open Logs",
            command=on_open_logs,
            font=("Segoe UI", 9),
            bg="#27272a",
            fg="#f4f4f5",
            activebackground="#3f3f46",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
        )
        btn_logs.pack(side="left")

        btn_exit = tk.Button(
            btn_bar,
            text="❌ Exit",
            command=on_exit,
            font=("Segoe UI", 9),
            bg="#27272a",
            fg="#f4f4f5",
            activebackground="#3f3f46",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
        )
        btn_exit.pack(side="right")

        btn_retry = tk.Button(
            btn_bar,
            text="🔄 Retry",
            command=on_retry,
            font=("Segoe UI", 9, "bold"),
            bg="#3b82f6",
            fg="#ffffff",
            activebackground="#2563eb",
            activeforeground="#ffffff",
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
        )
        btn_retry.pack(side="right", padx=(0, 10))

        # Center on screen
        root.update_idletasks()
        w = root.winfo_width()
        h = root.winfo_height()
        ws = root.winfo_screenwidth()
        hs = root.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        root.geometry(f"+{x}+{y}")

        root.protocol("WM_DELETE_WINDOW", on_exit)
        root.mainloop()
        return chosen_action

    except Exception as exc:
        log(f"[Dialog] Tkinter dialog fallback due to: {exc}")
        if sys.platform == "win32":
            MB_CANCELTRYCONTINUE = 0x00000006
            IDCANCEL = 2
            IDTRYAGAIN = 10
            IDCONTINUE = 11

            full_box_text = f"{headline}\n\n{message}\n\nLogs: {log_path}\n\nClick [Try Again] to retry or [Cancel] to exit."
            res = ctypes.windll.user32.MessageBoxW(
                0,
                full_box_text,
                "CodeLens AI - Startup Error",
                MB_CANCELTRYCONTINUE | 0x00000010,
            )
            if res == IDTRYAGAIN:
                return "retry"
            return "exit"
        return "exit"


# ==============================================================================
# Main Launcher Execution Loop
# ==============================================================================
def start_codelens_server() -> tuple[subprocess.Popen | None, int, str | None]:
    """Start the Streamlit background process and wait for HTTP 200 readiness.

    Returns:
        tuple[process, port, error_message]
    """
    log("=" * 60)
    log("CodeLens AI Launcher - Initializing Startup")
    log(f"APP_DIR     : {APP_DIR}")
    log(f"APP_SCRIPT  : {APP_SCRIPT}")
    log(f"LOG_FILE    : {LOG_FILE}")
    log("=" * 60)

    # 1. Verify app.py existence
    if not APP_SCRIPT.is_file():
        err = f"Application script '{APP_SCRIPT}' was not found in the installation directory."
        log(f"[Fatal] {err}")
        return None, 0, err

    # 2. Locate bundled Python runtime strictly
    python_exe, python_err = resolve_python_runtime()
    if not python_exe or python_err:
        log(f"[Fatal] {python_err}")
        return None, 0, python_err

    # 3. Find free TCP port
    port = find_free_port(DEFAULT_PORT)
    url = f"http://{HOST}:{port}"
    log(f"[Network] Target URL: {url}")

    # 4. Prepare Streamlit command using bundled runtime
    cmd = [
        python_exe,
        "-m",
        "streamlit",
        "run",
        str(APP_SCRIPT),
        f"--server.port={port}",
        f"--server.address={HOST}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--server.runOnSave=false",
        "--global.developmentMode=false",
    ]

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"

    log(f"[Process] Launching bundled command: {' '.join(cmd)}")

    # 5. Open log file for stdout/stderr streaming
    try:
        log_handle = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
        log_handle.write(f"\n--- CodeLens AI Server Output [{datetime.now()}] ---\n")
    except Exception as exc:
        log(f"[Warning] Could not redirect stdout to log file: {exc}")
        log_handle = subprocess.DEVNULL

    # 6. Launch process headlessly
    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(APP_DIR),
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception as exc:
        err = f"Failed to spawn Streamlit server process: {exc}"
        log(f"[Fatal] {err}")
        return None, port, err

    # 7. Poll for HTTP 200 readiness (Max 30s timeout)
    log(f"[Polling] Waiting up to {STARTUP_TIMEOUT}s for HTTP 200 from {url}...")
    start_time = time.time()
    browser_opened = False

    while time.time() - start_time < STARTUP_TIMEOUT:
        # Check if process terminated prematurely
        poll_res = process.poll()
        if poll_res is not None:
            err = f"Streamlit server process exited unexpectedly with return code {poll_res}."
            log(f"[Fatal] {err}")
            return None, port, err

        # Check HTTP health
        if check_server_health(port):
            elapsed = time.time() - start_time
            log(f"[Ready] Server responsive with HTTP 200 in {elapsed:.2f}s!")

            # Open browser EXACTLY ONCE
            if not browser_opened:
                log(f"[Browser] Opening user default browser to: {url}")
                webbrowser.open(url)
                browser_opened = True

            return process, port, None

        time.sleep(0.35)

    # 8. Timeout handling
    log(f"[Timeout] Server did not become ready within {STARTUP_TIMEOUT} seconds.")
    try:
        process.terminate()
        process.wait(timeout=2.0)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass

    err = f"CodeLens AI server did not become responsive on port {port} within {int(STARTUP_TIMEOUT)} seconds."
    return None, port, err


def main() -> None:
    # --------------------------------------------------------------------------
    # Fix 4: Single-Instance Protection
    # --------------------------------------------------------------------------
    lock = SingleInstanceLock()
    if not lock.acquire():
        log("[SingleInstance] Another instance of CodeLens AI is already active.")
        focused = try_focus_existing_window()
        log(f"[SingleInstance] Focus existing window result: {focused}. Exiting secondary launcher.")
        sys.exit(0)

    def on_exit_cleanup() -> None:
        lock.release()

    atexit.register(on_exit_cleanup)

    # --------------------------------------------------------------------------
    # Main Launch & Retry Loop
    # --------------------------------------------------------------------------
    active_process: subprocess.Popen | None = None

    def terminate_active_process() -> None:
        nonlocal active_process
        if active_process and active_process.poll() is None:
            log("[Shutdown] Terminating background Streamlit process...")
            try:
                active_process.terminate()
                active_process.wait(timeout=2.5)
            except Exception:
                try:
                    active_process.kill()
                except Exception:
                    pass

    atexit.register(terminate_active_process)

    while True:
        process, port, error = start_codelens_server()
        if process and not error:
            active_process = process
            log("[Main] CodeLens AI is running actively. Entering wait loop.")
            try:
                active_process.wait()
                log(f"[Main] Streamlit server exited with code {active_process.returncode}.")
            except (KeyboardInterrupt, SystemExit):
                terminate_active_process()
            break
        else:
            # Startup failed or timed out (Fix 5)
            log(f"[Main] Startup failure: {error}")
            action = show_native_dialog(
                headline="CodeLens AI couldn't start",
                message=error or "Unknown startup error.",
                log_path=LOG_FILE,
            )
            if action == "retry":
                log("[Main] User requested Retry. Restarting launch sequence...")
                time.sleep(0.5)
                continue
            else:
                log("[Main] User chose Exit. Terminating launcher.")
                break

    sys.exit(0)


if __name__ == "__main__":
    main()
