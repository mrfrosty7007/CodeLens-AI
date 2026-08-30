"""Native Windows Launcher for CodeLens AI.

Robust production launcher implementing:
1. Strict Bundled Runtime: Always executes isolated runtime\\pythonw.exe.
2. Comprehensive Preflight & Auto-Repair:
   - Verifies Python runtime and critical package imports.
   - Detects Ollama installation and auto-installs via bundled installer / winget if missing.
   - Verifies Ollama service and auto-starts daemon if stopped.
   - Verifies default local AI model (qwen2.5-coder:3b) and auto-pulls with live progress UI.
3. Single-Instance Protection: Prevents duplicate processes and browser tab spam via Named Mutex.
4. Process Logging: Captures full stdout/stderr into logs/launcher.log.
5. HTTP 200 Health Polling: Confirms Streamlit is fully ready before opening browser EXACTLY ONCE.
6. 30-Second Timeout & Native Error Dialog: Displays [Open Logs], [Retry], [Exit] on failure.
7. Headless Execution: Launches without visible terminal or flashing CMD windows.
"""

from __future__ import annotations

import atexit
import ctypes
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import threading
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
DEFAULT_MODEL = "qwen2.5-coder:3b"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


# ==============================================================================
# Determine Logs Directory and Logging Functions
# ==============================================================================
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
# Single-Instance Mutex & Window Focus
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
# Port, PID & Server Health Management
# ==============================================================================
PID_FILE = LOG_FILE.parent / "codelens.pid"


def get_saved_pid() -> int | None:
    """Retrieve saved Streamlit server PID from pid file."""
    if PID_FILE.is_file():
        try:
            content = PID_FILE.read_text(encoding="utf-8").strip()
            if content.isdigit():
                return int(content)
        except Exception:
            pass
    return None


def write_pid(pid: int) -> None:
    """Persist active Streamlit server PID to pid file."""
    try:
        PID_FILE.write_text(str(pid), encoding="utf-8")
    except Exception:
        pass


def remove_pid() -> None:
    """Remove pid file upon server termination."""
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def is_process_running(pid: int) -> bool:
    """Check if process with given PID is currently active in the OS."""
    if sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                exit_code = ctypes.c_ulong()
                kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                kernel32.CloseHandle(handle)
                return exit_code.value == 259
            return False
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def cleanup_stale_or_zombie_backend() -> None:
    """Clean up stale PID file or unresponsive zombie processes."""
    saved_pid = get_saved_pid()
    if not saved_pid:
        return

    if is_process_running(saved_pid):
        log(f"[Process] Found unresponsive process (PID {saved_pid}) with dead HTTP server. Terminating...")
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(saved_pid)],
                    capture_output=True,
                    creationflags=CREATE_NO_WINDOW,
                )
            else:
                os.kill(saved_pid, signal.SIGKILL)
        except Exception as exc:
            log(f"[Process] Warning: Could not terminate PID {saved_pid}: {exc}")

    remove_pid()


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


def check_server_health(port: int = DEFAULT_PORT, timeout_sec: float = 2.0) -> bool:
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
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
    return False


# ==============================================================================
# Preflight Checks & Automatic Repair Pipeline
# ==============================================================================

def verify_and_repair_runtime() -> tuple[str | None, str | None]:
    """Locate and verify the bundled Python runtime.
    
    Returns:
        tuple[python_exe_path, error_message]
    """
    log("[Preflight 1/4] Verifying Python runtime...")
    runtime_dir = APP_DIR / "runtime"

    candidates: list[Path] = [
        runtime_dir / "pythonw.exe",
        runtime_dir / "python.exe",
        runtime_dir / "Scripts" / "pythonw.exe",
        runtime_dir / "Scripts" / "python.exe",
    ]

    if sys.platform != "win32":
        candidates.extend([
            APP_DIR.parent / "usr" / "bin" / "python3",
            APP_DIR / "usr" / "bin" / "python3",
            Path(sys.executable),
        ])

    if not getattr(sys, "frozen", False):
        for dev_base in [APP_DIR, APP_DIR.parent]:
            candidates.append(dev_base / ".venv" / "Scripts" / "pythonw.exe")
            candidates.append(dev_base / ".venv" / "Scripts" / "python.exe")
            candidates.append(dev_base / ".venv" / "bin" / "python3")
            candidates.append(dev_base / ".venv" / "bin" / "python")

    for candidate in candidates:
        if candidate.is_file():
            test_exe = candidate
            if test_exe.name.lower() == "pythonw.exe":
                alt = test_exe.with_name("python.exe")
                if alt.is_file():
                    test_exe = alt
            try:
                res = subprocess.run(
                    [str(test_exe), "-c", "import streamlit, pygments"],
                    capture_output=True,
                    timeout=4.0,
                    creationflags=CREATE_NO_WINDOW,
                )
                if res.returncode == 0:
                    log(f"[Runtime] Verified bundled runtime executable: {candidate}")
                    return str(candidate), None
            except Exception as exc:
                log(f"[Runtime] Verification failed for {candidate}: {exc}")

    err = (
        "The bundled Python runtime was not found or is incomplete.\n\n"
        f"Expected path: {runtime_dir / 'pythonw.exe'}\n\n"
        "Please reinstall CodeLens AI using CodeLensAI-Setup.exe."
    )
    log(f"[Fatal] {err}")
    return None, err


def find_ollama_executable() -> str | None:
    """Find the path to the Ollama CLI executable."""
    found = shutil.which("ollama")
    if found:
        return found

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        user_profile = os.environ.get("USERPROFILE", "")

        candidates = [
            Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe",
            Path(program_files) / "Ollama" / "ollama.exe",
            Path(program_files_x86) / "Ollama" / "ollama.exe",
            Path(user_profile) / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe",
        ]

        for candidate in candidates:
            if candidate.is_file():
                # Add directory to PATH so future invocations find it
                bin_dir = str(candidate.parent)
                current_path = os.environ.get("PATH", "")
                if bin_dir.lower() not in current_path.lower():
                    os.environ["PATH"] = bin_dir + ";" + current_path
                return str(candidate)

    return None


def verify_and_repair_ollama_installation() -> tuple[bool, str | None]:
    """Verify that Ollama is installed. If missing, attempt automatic silent installation."""
    log("[Preflight 2/4] Verifying Ollama installation...")
    exe = find_ollama_executable()
    if exe:
        log(f"[Ollama] Found Ollama executable at: {exe}")
        return True, None

    log("[Ollama] Ollama executable not found. Searching for bundled installer...")

    # Look for bundled or cached OllamaSetup.exe
    installer_candidates = [
        APP_DIR / "tools" / "OllamaSetup.exe",
        APP_DIR / "OllamaSetup.exe",
        APP_DIR / "_internal" / "OllamaSetup.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "CodeLens AI" / "tools" / "OllamaSetup.exe",
        Path.home() / "Downloads" / "OllamaSetup.exe",
        Path(os.environ.get("TEMP", "")) / "OllamaSetup.exe",
    ]

    installer_found: Path | None = None
    for cand in installer_candidates:
        if cand.is_file():
            installer_found = cand
            break

    if installer_found:
        log(f"[Ollama Auto-Repair] Installing Ollama silently via {installer_found}...")
        try:
            res = subprocess.run(
                [str(installer_found), "/silent"],
                capture_output=True,
                timeout=180,
                creationflags=CREATE_NO_WINDOW,
            )
            time.sleep(2.0)
            exe = find_ollama_executable()
            if exe:
                log(f"[Ollama Auto-Repair] Successfully installed Ollama: {exe}")
                return True, None
            log(f"[Ollama Auto-Repair] Installer finished with code {res.returncode}, rechecking path...")
        except Exception as exc:
            log(f"[Ollama Auto-Repair] Failed to execute installer: {exc}")

    # Fallback to winget if available
    winget = shutil.which("winget")
    if winget:
        log("[Ollama Auto-Repair] Attempting installation via winget...")
        try:
            res = subprocess.run(
                [winget, "install", "Ollama.Ollama", "--silent", "--accept-source-agreements", "--accept-package-agreements"],
                capture_output=True,
                timeout=180,
                creationflags=CREATE_NO_WINDOW,
            )
            time.sleep(2.0)
            exe = find_ollama_executable()
            if exe:
                log(f"[Ollama Auto-Repair] Successfully installed Ollama via winget: {exe}")
                return True, None
        except Exception as exc:
            log(f"[Ollama Auto-Repair] winget install failed: {exc}")

    err = (
        "Ollama is not installed on this computer.\n\n"
        "CodeLens AI uses Ollama to execute local AI models completely offline.\n"
        "Please install Ollama from https://ollama.com or re-run the CodeLens AI setup."
    )
    return False, err


def check_ollama_service_health() -> bool:
    """Check if Ollama local HTTP API returns HTTP 200."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", headers={"User-Agent": "CodeLensAI-Launcher/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE_URL}/", headers={"User-Agent": "CodeLensAI-Launcher/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False


def verify_and_repair_ollama_service() -> tuple[bool, str | None]:
    """Verify that Ollama service is active. If offline, start it headlessly and wait for readiness."""
    log("[Preflight 3/4] Verifying Ollama background service...")
    if check_ollama_service_health():
        log("[Ollama Service] Service is online and responsive.")
        return True, None

    exe = find_ollama_executable()
    if not exe:
        return False, "Cannot start Ollama service because ollama.exe was not found."

    log(f"[Ollama Service] Service is offline. Starting '{exe} serve' in background...")
    try:
        subprocess.Popen(
            [exe, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
            close_fds=True,
        )
    except Exception as exc:
        log(f"[Ollama Service] Failed to launch service process: {exc}")
        return False, f"Failed to start Ollama background process: {exc}"

    # Poll for service readiness (up to 15 seconds)
    log("[Ollama Service] Waiting for service to respond on port 11434...")
    for i in range(30):
        time.sleep(0.5)
        if check_ollama_service_health():
            log(f"[Ollama Service] Ollama service became active in {(i + 1) * 0.5:.1f}s.")
            return True, None

    err = "Ollama service was launched but did not respond on http://127.0.0.1:11434 within 15 seconds."
    log(f"[Ollama Service] {err}")
    return False, err


def get_installed_ollama_models() -> list[str]:
    """Retrieve list of model names currently installed in Ollama."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", headers={"User-Agent": "CodeLensAI-Launcher/1.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                return [m.get("name", "") for m in models if m.get("name")]
    except Exception as exc:
        log(f"[Model] Error fetching installed models: {exc}")
    return []


def is_model_available(target_model: str = DEFAULT_MODEL) -> bool:
    """Check if the target model is present in Ollama model storage."""
    installed = get_installed_ollama_models()
    target_clean = target_model.lower()
    target_base = target_clean.split(":")[0]

    for m in installed:
        m_lower = m.lower()
        if (
            m_lower == target_clean
            or m_lower.startswith(f"{target_clean}:")
            or m_lower == f"{target_base}:latest"
            or m_lower == target_base
            or target_clean in m_lower
        ):
            return True
    return False


def show_model_download_ui_and_pull(target_model: str = DEFAULT_MODEL) -> tuple[bool, str | None]:
    """Pull the required Ollama model while displaying a modern Tkinter progress window."""
    log(f"[Model Download] Pulling model '{target_model}'...")
    download_success = False
    download_error: str | None = None
    pull_thread_done = False

    # Check if Tkinter is available for GUI progress
    has_gui = True
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        has_gui = False

    if not has_gui:
        # Fallback to headless / CLI pull
        log("[Model Download] Tkinter GUI unavailable, pulling in background...")
        try:
            payload = json.dumps({"name": target_model, "stream": False}).encode("utf-8")
            req = urllib.request.Request(
                f"{OLLAMA_BASE_URL}/api/pull",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=600.0) as resp:
                if resp.status == 200:
                    log(f"[Model Download] Successfully pulled '{target_model}'.")
                    return True, None
        except Exception as exc:
            return False, f"Failed to download model '{target_model}': {exc}"

    # Tkinter Progress UI
    root = tk.Tk()
    root.title("CodeLens AI - Setup")
    root.geometry("520x220")
    root.resizable(False, False)
    root.configure(bg="#18181b")
    root.attributes("-topmost", True)

    icon_path = APP_DIR / "assets" / "icon.ico"
    if icon_path.is_file():
        try:
            root.iconbitmap(str(icon_path))
        except Exception:
            pass

    # Header
    hdr = tk.Label(
        root,
        text="🤖 Downloading Local AI Model",
        font=("Segoe UI", 12, "bold"),
        fg="#38bdf8",
        bg="#18181b",
        anchor="w",
    )
    hdr.pack(fill="x", padx=20, pady=(18, 2))

    sub = tk.Label(
        root,
        text=f"Downloading {target_model} (~1.9 GB) for zero-latency offline intelligence.",
        font=("Segoe UI", 9),
        fg="#a1a1aa",
        bg="#18181b",
        anchor="w",
    )
    sub.pack(fill="x", padx=20, pady=(0, 14))

    # Progress bar container
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Custom.Horizontal.TProgressbar",
        troughcolor="#27272a",
        background="#3b82f6",
        thickness=14,
    )

    prog_bar = ttk.Progressbar(
        root,
        style="Custom.Horizontal.TProgressbar",
        orient="horizontal",
        mode="determinate",
        maximum=100,
    )
    prog_bar.pack(fill="x", padx=20, pady=(0, 8))

    status_var = tk.StringVar(value="Connecting to Ollama model library...")
    status_lbl = tk.Label(
        root,
        textvariable=status_var,
        font=("Segoe UI", 9),
        fg="#e4e4e7",
        bg="#18181b",
        anchor="w",
    )
    status_lbl.pack(fill="x", padx=20, pady=(0, 16))

    # Center window
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    ws, hs = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"+{(ws - w) // 2}+{(hs - h) // 2}")

    def pull_worker() -> None:
        nonlocal download_success, download_error, pull_thread_done
        try:
            payload = json.dumps({"name": target_model, "stream": True}).encode("utf-8")
            req = urllib.request.Request(
                f"{OLLAMA_BASE_URL}/api/pull",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=900.0) as resp:
                for raw_line in resp:
                    if not raw_line or not raw_line.strip():
                        continue
                    try:
                        chunk = json.loads(raw_line.decode("utf-8"))
                    except Exception:
                        continue

                    st_text = chunk.get("status", "")
                    completed = chunk.get("completed", 0)
                    total = chunk.get("total", 0)

                    if total > 0:
                        pct = (completed / total) * 100.0
                        gb_done = completed / (1024**3)
                        gb_tot = total / (1024**3)
                        status_msg = f"{st_text} • {gb_done:.2f} GB / {gb_tot:.2f} GB ({int(pct)}%)"
                        prog_bar["value"] = pct
                        status_var.set(status_msg)
                    else:
                        status_var.set(st_text)

                    if chunk.get("error"):
                        download_error = chunk["error"]
                        break

                    if "success" in st_text.lower():
                        download_success = True
                        break

            if not download_error:
                download_success = True
        except Exception as exc:
            download_error = str(exc)
        finally:
            pull_thread_done = True

    worker = threading.Thread(target=pull_worker, daemon=True)
    worker.start()

    def check_loop() -> None:
        if pull_thread_done:
            root.destroy()
        else:
            root.after(100, check_loop)

    root.after(100, check_loop)
    root.mainloop()

    if download_success:
        log(f"[Model Download] Completed successfully: {target_model}")
        return True, None
    else:
        err = f"Failed to download model '{target_model}': {download_error}"
        log(f"[Model Download] {err}")
        return False, err


def verify_and_repair_default_model(model_name: str = DEFAULT_MODEL) -> tuple[bool, str | None]:
    """Verify that the default local AI model is present. If missing, auto-pull it."""
    log(f"[Preflight 4/4] Verifying default model '{model_name}'...")
    if is_model_available(model_name):
        log(f"[Model] Default model '{model_name}' is verified and ready.")
        return True, None

    log(f"[Model] Required model '{model_name}' is not in local storage. Initiating auto-pull...")
    ok, err = show_model_download_ui_and_pull(model_name)
    if ok and is_model_available(model_name):
        return True, None
    return False, err or f"Model '{model_name}' is not available."


def run_preflight_checks() -> tuple[str | None, str | None]:
    """Run all preflight checks (Runtime, Ollama, Service, Model) with automatic repair.
    
    Returns:
        tuple[python_exe, error_message]
    """
    log("=" * 60)
    log("CodeLens AI Launcher - Executing Preflight Verification & Repair")
    log(f"APP_DIR     : {APP_DIR}")
    log(f"APP_SCRIPT  : {APP_SCRIPT}")
    log(f"LOG_FILE    : {LOG_FILE}")
    log("=" * 60)

    # 1. Verify app.py exists
    if not APP_SCRIPT.is_file():
        err = f"Application script '{APP_SCRIPT}' was not found in the installation directory."
        log(f"[Fatal] {err}")
        return None, err

    # 2. Verify Python runtime
    python_exe, err = verify_and_repair_runtime()
    if not python_exe or err:
        return None, err

    # 3. Verify Ollama installation
    ollama_ok, err = verify_and_repair_ollama_installation()
    if not ollama_ok:
        return None, err

    # 4. Verify Ollama service
    service_ok, err = verify_and_repair_ollama_service()
    if not service_ok:
        return None, err

    # 5. Verify Default Model
    model_ok, err = verify_and_repair_default_model(DEFAULT_MODEL)
    if not model_ok:
        return None, err

    log("[Preflight] All 4 preflight checks passed successfully! Launching desktop engine...")
    return python_exe, None


# ==============================================================================
# Native Dialog for Errors & Timeout
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

        root.update_idletasks()
        w = root.winfo_width()
        h = root.winfo_height()
        ws = root.winfo_screenwidth()
        hs = root.winfo_screenheight()
        root.geometry(f"+{(ws - w) // 2}+{(hs - h) // 2}")

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
    """Run preflight verification & repair, start Streamlit server, and wait for HTTP 200.

    Returns:
        tuple[process, port, error_message]
    """
    # Run all preflight checks and auto-repairs
    python_exe, preflight_err = run_preflight_checks()
    if not python_exe or preflight_err:
        return None, 0, preflight_err

    # Find free TCP port
    port = find_free_port(DEFAULT_PORT)
    url = f"http://{HOST}:{port}"
    log(f"[Network] Target URL: {url}")

    # Prepare Streamlit command using verified runtime
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

    try:
        log_handle = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
        log_handle.write(f"\n--- CodeLens AI Server Output [{datetime.now()}] ---\n")
    except Exception as exc:
        log(f"[Warning] Could not redirect stdout to log file: {exc}")
        log_handle = subprocess.DEVNULL

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

    log(f"[Polling] Waiting up to {STARTUP_TIMEOUT}s for HTTP 200 from {url}...")
    start_time = time.time()
    browser_opened = False

    while time.time() - start_time < STARTUP_TIMEOUT:
        poll_res = process.poll()
        if poll_res is not None:
            err = f"Streamlit server process exited unexpectedly with return code {poll_res}."
            log(f"[Fatal] {err}")
            return None, port, err

        if check_server_health(port, timeout_sec=0.5):
            elapsed = time.time() - start_time
            log(f"[Ready] Server responsive with HTTP 200 in {elapsed:.2f}s!")

            if not browser_opened:
                log(f"[Browser] Opening user default browser to: {url}")
                webbrowser.open(url)
                browser_opened = True

            write_pid(process.pid)
            return process, port, None

        time.sleep(0.35)

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
    target_url = f"http://{HOST}:{DEFAULT_PORT}"

    # 1. Single-Instance Check: If server is already responding on port 8501, immediately open browser and exit
    log(f"[Main] Checking if CodeLens AI is already active on port {DEFAULT_PORT}...")
    if check_server_health(DEFAULT_PORT, timeout_sec=2.0):
        log(f"[SingleInstance] Active server detected at {target_url}. Reopening browser session.")
        try_focus_existing_window()
        webbrowser.open(target_url)
        sys.exit(0)

    # 2. Server is not responding: Clean up any stale PID file or unresponsive zombie process
    cleanup_stale_or_zombie_backend()

    # 3. Single-Instance Mutex: Prevent duplicate concurrent launching sequences
    lock = SingleInstanceLock()
    if not lock.acquire():
        # Another launcher instance is actively starting the backend; wait up to 8s for it to become ready
        log("[SingleInstance] Another launcher instance is in progress. Waiting for server readiness...")
        start_wait = time.time()
        while time.time() - start_wait < 8.0:
            if check_server_health(DEFAULT_PORT, timeout_sec=1.0):
                log(f"[SingleInstance] Server became ready. Opening browser to {target_url}.")
                webbrowser.open(target_url)
                sys.exit(0)
            time.sleep(0.5)

        try_focus_existing_window()
        sys.exit(0)

    def on_exit_cleanup() -> None:
        lock.release()
        remove_pid()

    atexit.register(on_exit_cleanup)

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
        remove_pid()

    atexit.register(terminate_active_process)

    while True:
        process, port, error = start_codelens_server()
        if process and not error:
            active_process = process
            write_pid(process.pid)
            log(f"[Main] CodeLens AI (PID {process.pid}) is running on port {port}. Entering wait loop.")
            try:
                active_process.wait()
                log(f"[Main] Streamlit server exited with code {active_process.returncode}.")
            except (KeyboardInterrupt, SystemExit):
                terminate_active_process()
            break
        else:
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
