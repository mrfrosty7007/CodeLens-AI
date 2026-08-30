"""Setup and background dependency manager for CodeLens AI.

Provides one-time setup detection, automated Ollama installation, service
management, and model download with real-time progress streaming.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Generator

import httpx

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"
OLLAMA_PULL_URL = f"{OLLAMA_BASE_URL}/api/pull"
REQUIRED_MODEL = "qwen2.5-coder:3b"
OLLAMA_INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"

# Windows flags for headless execution
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

_CLIENT: httpx.Client | None = None
_EXECUTABLE_CACHE: str | None = None


def get_http_client() -> httpx.Client:
    """Return a shared persistent HTTP client with connection pooling."""
    global _CLIENT
    if _CLIENT is None or _CLIENT.is_closed:
        _CLIENT = httpx.Client(
            base_url=OLLAMA_BASE_URL,
            timeout=3.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    return _CLIENT


def get_ollama_executable() -> str | None:
    """Find the path to the Ollama executable on the system."""
    global _EXECUTABLE_CACHE
    if _EXECUTABLE_CACHE and Path(_EXECUTABLE_CACHE).is_file():
        return _EXECUTABLE_CACHE

    # 1. System PATH
    found = shutil.which("ollama")
    if found:
        _EXECUTABLE_CACHE = found
        return found

    # 2. Windows standard installation locations
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
                _EXECUTABLE_CACHE = str(candidate)
                return _EXECUTABLE_CACHE

    return None


def is_ollama_installed() -> bool:
    """Check whether Ollama is installed on the host machine."""
    return get_ollama_executable() is not None


def is_ollama_service_running() -> bool:
    """Check whether the Ollama local HTTP API is responsive."""
    try:
        client = get_http_client()
        response = client.get("/", timeout=1.5)
        return response.status_code == 200
    except Exception:
        return False


def start_ollama_service() -> tuple[bool, str]:
    """Start the local Ollama background service if not already running."""
    if is_ollama_service_running():
        return True, "Ollama service is already active."

    exe = get_ollama_executable()
    if not exe:
        return False, "Ollama is not installed. Please install Ollama first."

    try:
        # Launch headless in background
        subprocess.Popen(
            [exe, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
            close_fds=True,
        )
    except Exception as exc:
        return False, f"Failed to start Ollama background process: {exc}"

    # Poll for service readiness (up to 8 seconds)
    for _ in range(16):
        time.sleep(0.5)
        if is_ollama_service_running():
            return True, "Ollama service started successfully."

    return False, "Ollama was launched but did not become responsive on port 11434 within 8 seconds."


def install_ollama_winget() -> tuple[bool, str]:
    """Attempt silent installation of Ollama via Windows Package Manager (winget)."""
    winget = shutil.which("winget")
    if not winget:
        return False, "winget is not available on this system."

    try:
        cmd = [
            winget,
            "install",
            "Ollama.Ollama",
            "--accept-source-agreements",
            "--accept-package-agreements",
            "--silent",
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=180,
        )
        if result.returncode == 0:
            return True, "Ollama installed successfully via winget."
        return False, f"winget install failed (exit {result.returncode}): {result.stderr or result.stdout}"
    except subprocess.TimeoutExpired:
        return False, "winget installation timed out after 3 minutes."
    except Exception as exc:
        return False, f"Error executing winget: {exc}"


def download_and_launch_installer() -> tuple[bool, str]:
    """Download the official Ollama Windows installer and launch it."""
    try:
        temp_dir = Path(tempfile.gettempdir())
        installer_path = temp_dir / "OllamaSetup.exe"

        # Download with httpx
        with httpx.stream("GET", OLLAMA_INSTALLER_URL, follow_redirects=True, timeout=60.0) as response:
            if response.status_code != 200:
                return False, f"Failed to download installer (HTTP {response.status_code})."
            with open(installer_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=65536):
                    f.write(chunk)

        # Launch the installer
        if sys.platform == "win32":
            os.startfile(str(installer_path))
        else:
            subprocess.Popen([str(installer_path)])

        return True, "Launched official Ollama installer. Please follow the on-screen prompt."
    except Exception as exc:
        return False, f"Failed to download and launch installer: {exc}"


def get_installed_models() -> list[str]:
    """Query the local Ollama daemon for a list of downloaded model names."""
    try:
        client = get_http_client()
        response = client.get("/api/tags", timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            names = [m.get("name", "") for m in models if m.get("name")]
            return names
    except Exception:
        pass
    return []


def is_model_installed(target_model: str = REQUIRED_MODEL) -> bool:
    """Check if the required AI model is present in the local Ollama library."""
    installed = get_installed_models()
    target_clean = target_model.lower()
    target_base = target_clean.split(":")[0]

    for m in installed:
        m_lower = m.lower()
        if m_lower == target_clean or m_lower.startswith(f"{target_clean}:"):
            return True
        if m_lower == f"{target_base}:latest" or m_lower == target_base:
            return True
        if target_clean in m_lower:
            return True

    return False


def pull_model_stream(
    target_model: str = REQUIRED_MODEL,
) -> Generator[dict, None, None]:
    """Stream model pull progress from Ollama API.

    Yields:
        dict: {
            "status": str,
            "completed": int,
            "total": int,
            "percent": float (0.0 to 1.0),
            "done": bool,
            "error": str | None
        }
    """
    if not is_ollama_service_running():
        yield {
            "status": "Ollama service is offline.",
            "completed": 0,
            "total": 0,
            "percent": 0.0,
            "done": False,
            "error": "Ollama service is not running.",
        }
        return

    payload = {"name": target_model, "stream": True}

    try:
        with httpx.Client(base_url=OLLAMA_BASE_URL, timeout=None).stream(
            "POST",
            "/api/pull",
            json=payload,
        ) as response:
            if response.status_code != 200:
                yield {
                    "status": f"HTTP {response.status_code}",
                    "completed": 0,
                    "total": 0,
                    "percent": 0.0,
                    "done": False,
                    "error": f"Failed to pull model: HTTP {response.status_code}",
                }
                return

            for line in response.iter_lines():
                if not line or not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue

                status = data.get("status", "")
                completed = data.get("completed", 0)
                total = data.get("total", 0)
                percent = (completed / total) if total > 0 else 0.0

                is_success = status.lower() == "success" or "success" in status.lower()

                yield {
                    "status": status,
                    "completed": completed,
                    "total": total,
                    "percent": min(1.0, max(0.0, percent)),
                    "done": is_success,
                    "error": data.get("error"),
                }

                if is_success:
                    break

    except Exception as exc:
        yield {
            "status": f"Connection error: {exc}",
            "completed": 0,
            "total": 0,
            "percent": 0.0,
            "done": False,
            "error": str(exc),
        }


def get_system_status() -> dict:
    """Check full environment readiness for CodeLens AI."""
    exe_path = get_ollama_executable()
    installed = exe_path is not None
    running = False
    model_ready = False

    if installed:
        models = get_installed_models()
        if models:
            running = True
            target_clean = REQUIRED_MODEL.lower()
            target_base = target_clean.split(":")[0]
            for m in models:
                m_lower = m.lower()
                if (
                    m_lower == target_clean
                    or m_lower.startswith(f"{target_clean}:")
                    or m_lower == f"{target_base}:latest"
                    or m_lower == target_base
                    or target_clean in m_lower
                ):
                    model_ready = True
                    break
        else:
            running = is_ollama_service_running()

    return {
        "app_installed": True,
        "ollama_installed": installed,
        "ollama_running": running,
        "model_installed": model_ready,
        "ready": installed and running and model_ready,
        "model_name": REQUIRED_MODEL,
        "ollama_path": exe_path,
    }
