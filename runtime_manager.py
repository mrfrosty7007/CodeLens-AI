"""Runtime auto-detection and dependency installer for CodeLens AI.

Provides detection for Python, Java (JDK 17+), C++ (MinGW/Clang/MSVC), and JavaScript (Node.js),
with caching, version extraction, winget automated installation, and Windows Registry PATH synchronization.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path

# Windows flags for headless execution
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

CACHE_TTL_SECONDS = 5.0

@dataclass
class RuntimeInfo:
    name: str
    installed: bool
    version: str | None
    executable_path: str | None
    compiler_path: str | None
    winget_package: str
    official_url: str
    display_desc: str
    missing_reason: str | None = None

    @property
    def status_badge(self) -> str:
        if self.installed:
            return f"🟢 Ready ({self.version})" if self.version else "🟢 Ready"
        return "🔴 Missing"

    @property
    def version_display(self) -> str:
        if not self.installed:
            return f"{self.name} (Missing)"
        if self.version:
            return f"{self.name} {self.version}"
        return self.name


# In-memory detection cache
_DETECTION_CACHE: dict[str, tuple[float, RuntimeInfo]] = {}


def clear_runtime_cache() -> None:
    """Clear cached runtime detection results."""
    global _DETECTION_CACHE
    _DETECTION_CACHE.clear()


def refresh_system_path() -> None:
    """Synchronize process PATH environment variable from Windows Registry and standard toolchain dirs."""
    if sys.platform != "win32":
        return

    try:
        import winreg

        new_paths: list[str] = []

        # 1. System Environment PATH (HKLM)
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            ) as key:
                system_path, _ = winreg.QueryValueEx(key, "Path")
                new_paths.extend(system_path.split(";"))
        except Exception:
            pass

        # 2. User Environment PATH (HKCU)
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Environment",
            ) as key:
                user_path, _ = winreg.QueryValueEx(key, "Path")
                new_paths.extend(user_path.split(";"))
        except Exception:
            pass

        # 3. Known standard installation directories in prioritized order
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        user_profile = os.environ.get("USERPROFILE", "")

        candidates = [
            Path(r"C:\msys64\ucrt64\bin"),
            Path(r"C:\msys64\mingw64\bin"),
            Path(r"C:\msys64\clang64\bin"),
            Path(r"C:\MinGW\bin"),
            Path(program_files) / "nodejs",
            Path(program_files) / "Eclipse Adoptium",
            Path(program_files) / "Java",
            Path(local_app_data) / "Programs" / "Python",
            Path(user_profile) / "AppData" / "Local" / "Microsoft" / "WindowsApps",
        ]

        # Scan subdirectories for Java JDKs (e.g. C:\Program Files\Eclipse Adoptium\jdk-17.*\bin)
        for base in [Path(program_files) / "Eclipse Adoptium", Path(program_files) / "Java"]:
            if base.is_dir():
                for sub in base.iterdir():
                    bin_dir = sub / "bin"
                    if bin_dir.is_dir():
                        new_paths.append(str(bin_dir))

        for c in candidates:
            if c.is_dir():
                new_paths.append(str(c))

        # Merge with current PATH, preserving order and removing duplicates
        current_paths = os.environ.get("PATH", "").split(";")
        combined = []
        seen = set()

        for p in new_paths + current_paths:
            p_clean = p.strip()
            if p_clean and p_clean.lower() not in seen:
                seen.add(p_clean.lower())
                combined.append(p_clean)

        os.environ["PATH"] = ";".join(combined)
    except Exception:
        pass


def _extract_version(output: str) -> str | None:
    """Extract a semantic version string from command output."""
    if not output:
        return None
    match = re.search(r"(\d+\.\d+(?:\.\d+)?)", output)
    if match:
        return match.group(1)
    return None


def detect_python() -> RuntimeInfo:
    """Detect Python interpreter availability and version."""
    exe = sys.executable or shutil.which("python") or shutil.which("python3")
    if not exe:
        return RuntimeInfo(
            name="Python",
            installed=False,
            version=None,
            executable_path=None,
            compiler_path=None,
            winget_package="Python.Python.3.12",
            official_url="https://www.python.org/downloads/",
            display_desc="Python 3.10+ is required to run Python scripts and desktop runtime.",
            missing_reason="Python interpreter not found in system PATH.",
        )

    version_str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return RuntimeInfo(
        name="Python",
        installed=True,
        version=version_str,
        executable_path=exe,
        compiler_path=None,
        winget_package="Python.Python.3.12",
        official_url="https://www.python.org/downloads/",
        display_desc="Python interpreter is active and verified.",
    )


def detect_javascript() -> RuntimeInfo:
    """Detect Node.js JavaScript runtime availability and version."""
    node_exe = shutil.which("node")
    if not node_exe and sys.platform == "win32":
        candidate = Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "nodejs" / "node.exe"
        if candidate.is_file():
            node_exe = str(candidate)

    if not node_exe:
        return RuntimeInfo(
            name="JavaScript",
            installed=False,
            version=None,
            executable_path=None,
            compiler_path=None,
            winget_package="OpenJS.NodeJS.LTS",
            official_url="https://nodejs.org/en/download",
            display_desc="Node.js (LTS) is required to execute JavaScript programs.",
            missing_reason="Node.js runtime (node) not found in system PATH.",
        )

    version_str = None
    try:
        proc = subprocess.run(
            [node_exe, "-v"],
            capture_output=True,
            text=True,
            timeout=2.0,
            creationflags=CREATE_NO_WINDOW,
        )
        if proc.returncode == 0:
            version_str = _extract_version(proc.stdout.strip())
    except Exception:
        pass

    return RuntimeInfo(
        name="JavaScript",
        installed=True,
        version=version_str or "LTS",
        executable_path=node_exe,
        compiler_path=None,
        winget_package="OpenJS.NodeJS.LTS",
        official_url="https://nodejs.org/en/download",
        display_desc="Node.js JavaScript engine is active and ready.",
    )


def detect_java() -> RuntimeInfo:
    """Detect Java Development Kit (JDK 17+) availability and version."""
    javac_exe = shutil.which("javac")
    java_exe = shutil.which("java")

    # Search standard Windows JDK directories if not found in PATH
    if (not javac_exe or not java_exe) and sys.platform == "win32":
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        search_dirs = [
            Path(program_files) / "Eclipse Adoptium",
            Path(program_files) / "Java",
            Path(program_files) / "Microsoft",
        ]
        for base in search_dirs:
            if base.is_dir():
                for sub in base.iterdir():
                    candidate_javac = sub / "bin" / "javac.exe"
                    candidate_java = sub / "bin" / "java.exe"
                    if candidate_javac.is_file() and candidate_java.is_file():
                        javac_exe = str(candidate_javac)
                        java_exe = str(candidate_java)
                        # Prepend to PATH for child processes
                        os.environ["PATH"] = str(sub / "bin") + ";" + os.environ.get("PATH", "")
                        break
            if javac_exe and java_exe:
                break

    if not javac_exe or not java_exe:
        return RuntimeInfo(
            name="Java",
            installed=False,
            version=None,
            executable_path=java_exe,
            compiler_path=javac_exe,
            winget_package="EclipseAdoptium.Temurin.17.JDK",
            official_url="https://adoptium.net/temurin/releases/?version=17",
            display_desc="Java Development Kit (JDK 17+) is required to compile (javac) and execute (java) Java programs.",
            missing_reason="Java compiler (javac) or runtime (java) is not installed or not found in system PATH.",
        )

    version_str = None
    try:
        proc = subprocess.run(
            [javac_exe, "-version"],
            capture_output=True,
            text=True,
            timeout=2.0,
            creationflags=CREATE_NO_WINDOW,
        )
        out = proc.stdout if proc.stdout else proc.stderr
        version_str = _extract_version(out)
    except Exception:
        pass

    return RuntimeInfo(
        name="Java",
        installed=True,
        version=version_str or "17+",
        executable_path=java_exe,
        compiler_path=javac_exe,
        winget_package="EclipseAdoptium.Temurin.17.JDK",
        official_url="https://adoptium.net/temurin/releases/?version=17",
        display_desc="Java JDK compiler and runtime are verified.",
    )


def detect_cpp() -> RuntimeInfo:
    """Detect C++ compiler in prioritized candidate locations and PATH.

    Searches in order:
    1. C:\\msys64\\ucrt64\\bin\\g++.exe
    2. C:\\msys64\\mingw64\\bin\\g++.exe
    3. C:\\msys64\\clang64\\bin\\clang++.exe
    4. C:\\MinGW\\bin\\g++.exe
    5. System PATH (g++, clang++, cl)
    """
    search_locations = [
        Path(r"C:\msys64\ucrt64\bin\g++.exe"),
        Path(r"C:\msys64\mingw64\bin\g++.exe"),
        Path(r"C:\msys64\clang64\bin\clang++.exe"),
        Path(r"C:\MinGW\bin\g++.exe"),
    ]

    compiler_exe: str | None = None

    # 1. Search candidate locations in strict order
    if sys.platform == "win32":
        for candidate in search_locations:
            if candidate.is_file():
                compiler_exe = str(candidate)
                # Prepend the compiler's bin directory to process PATH so DLLs and includes resolve
                bin_dir = str(candidate.parent)
                current_path = os.environ.get("PATH", "")
                if bin_dir.lower() not in current_path.lower():
                    os.environ["PATH"] = bin_dir + ";" + current_path
                break

    # 2. Search system PATH (g++, clang++, cl)
    if not compiler_exe:
        compiler_exe = shutil.which("g++") or shutil.which("clang++") or shutil.which("cl")

    if not compiler_exe:
        # Check if MSYS2 exists on the system
        msys2_pacman = Path(r"C:\msys64\usr\bin\pacman.exe")
        msys2_installed = msys2_pacman.is_file() or Path(r"C:\msys64").is_dir()

        if msys2_installed:
            return RuntimeInfo(
                name="C++",
                installed=False,
                version=None,
                executable_path=None,
                compiler_path=None,
                winget_package="mingw-w64-ucrt-x86_64-gcc",
                official_url="https://www.msys2.org/",
                display_desc="MSYS2 is installed, but the UCRT64 GCC toolchain (mingw-w64-ucrt-x86_64-gcc) is missing.",
                missing_reason="MSYS2 is installed, but the UCRT64 C++ toolchain (g++.exe) is missing.",
            )

        return RuntimeInfo(
            name="C++",
            installed=False,
            version=None,
            executable_path=None,
            compiler_path=None,
            winget_package="MSYS2.MSYS2",
            official_url="https://www.msys2.org/",
            display_desc="A C++ compiler (MinGW g++, Clang++, or MSVC) is required to compile and execute C++ programs.",
            missing_reason="C++ compiler (g++, clang++, or cl) is not installed or not found in system PATH.",
        )

    # Compiler was found! Extract version
    version_str = None
    try:
        proc = subprocess.run(
            [compiler_exe, "--version"],
            capture_output=True,
            text=True,
            timeout=2.0,
            creationflags=CREATE_NO_WINDOW,
        )
        if proc.returncode == 0:
            first_line = proc.stdout.splitlines()[0] if proc.stdout else ""
            version_str = _extract_version(first_line)
    except Exception:
        pass

    compiler_type = "g++"
    if "clang" in Path(compiler_exe).name.lower():
        compiler_type = "clang++"
    elif "cl" in Path(compiler_exe).name.lower():
        compiler_type = "MSVC"

    return RuntimeInfo(
        name="C++",
        installed=True,
        version=f"{compiler_type} {version_str}" if version_str else compiler_type,
        executable_path=compiler_exe,
        compiler_path=compiler_exe,
        winget_package="mingw-w64-ucrt-x86_64-gcc",
        official_url="https://www.msys2.org/",
        display_desc=f"{compiler_type} C++ toolchain is active and ready.",
    )


def detect_runtime(language: str, use_cache: bool = True) -> RuntimeInfo:
    """Get runtime detection info for a specific programming language with TTL caching."""
    lang_key = language.strip().lower()
    now = time.perf_counter()

    if use_cache and lang_key in _DETECTION_CACHE:
        cached_time, cached_info = _DETECTION_CACHE[lang_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_info

    if lang_key in ("python", "py"):
        info = detect_python()
    elif lang_key in ("javascript", "js", "node"):
        info = detect_javascript()
    elif lang_key in ("java",):
        info = detect_java()
    elif lang_key in ("c++", "cpp", "c"):
        info = detect_cpp()
    else:
        info = RuntimeInfo(
            name=language,
            installed=False,
            version=None,
            executable_path=None,
            compiler_path=None,
            winget_package="",
            official_url="",
            display_desc=f"Unknown runtime: {language}",
            missing_reason=f"No toolchain configuration for {language}",
        )

    _DETECTION_CACHE[lang_key] = (now, info)
    return info


def detect_all_runtimes(use_cache: bool = True) -> dict[str, RuntimeInfo]:
    """Return detection info for all supported languages."""
    return {
        "Python": detect_runtime("Python", use_cache=use_cache),
        "JavaScript": detect_runtime("JavaScript", use_cache=use_cache),
        "C++": detect_runtime("C++", use_cache=use_cache),
        "Java": detect_runtime("Java", use_cache=use_cache),
    }


def is_winget_available() -> bool:
    """Check if Windows Package Manager (winget) is installed and operational."""
    return shutil.which("winget") is not None


def install_runtime_winget(language: str) -> tuple[bool, str]:
    """Install missing language toolchain using MSYS2 pacman or winget with automatic PATH synchronization."""
    lang_key = language.strip().lower()

    # Special handling for C++ when MSYS2 is already installed
    if lang_key in ("c++", "cpp", "c"):
        pacman_exe = Path(r"C:\msys64\usr\bin\pacman.exe")

        if pacman_exe.is_file():
            try:
                cmd = [str(pacman_exe), "-S", "--noconfirm", "--needed", "mingw-w64-ucrt-x86_64-gcc"]
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=CREATE_NO_WINDOW,
                    timeout=300,
                )

                refresh_system_path()
                clear_runtime_cache()
                post_check = detect_runtime("C++", use_cache=False)
                if post_check.installed:
                    return True, f"✨ UCRT64 C++ toolchain installed successfully ({post_check.version})!"

                if result.returncode == 0 or Path(r"C:\msys64\ucrt64\bin\g++.exe").is_file():
                    refresh_system_path()
                    return True, "✨ UCRT64 GCC toolchain installed successfully! Please refresh detection."

                return False, f"pacman install failed (exit {result.returncode}): {result.stderr or result.stdout}"
            except subprocess.TimeoutExpired:
                return False, "C++ toolchain installation timed out after 5 minutes."
            except Exception as exc:
                return False, f"Error running MSYS2 pacman: {exc}"

    info = detect_runtime(language, use_cache=False)
    if info.installed:
        return True, f"{info.name} is already installed and operational ({info.version})."

    package_id = info.winget_package
    if not package_id:
        return False, f"No package configured for {language}."

    winget = shutil.which("winget")
    if not winget:
        return False, "Windows Package Manager (winget) was not found on your system."

    try:
        cmd = [
            winget,
            "install",
            package_id,
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
            timeout=300,
        )

        # If we just installed MSYS2 via winget, immediately install the GCC package
        if lang_key in ("c++", "cpp", "c") and Path(r"C:\msys64\usr\bin\pacman.exe").is_file():
            subprocess.run(
                [r"C:\msys64\usr\bin\pacman.exe", "-S", "--noconfirm", "--needed", "mingw-w64-ucrt-x86_64-gcc"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=CREATE_NO_WINDOW,
                timeout=300,
            )

        refresh_system_path()
        clear_runtime_cache()

        post_check = detect_runtime(language, use_cache=False)
        if post_check.installed:
            return True, f"✨ {info.name} installed successfully ({post_check.version})!"

        if result.returncode == 0:
            return True, f"✨ {info.name} package installed successfully! Please refresh detection."

        return (
            False,
            f"winget install failed (exit code {result.returncode}): {result.stderr or result.stdout}",
        )
    except subprocess.TimeoutExpired:
        return False, f"Installation for {info.name} timed out after 5 minutes."
    except Exception as exc:
        return False, f"Error executing winget installer: {exc}"


def open_official_download(language: str) -> None:
    """Launch the official toolchain download portal in the user's default browser."""
    info = detect_runtime(language)
    if info.official_url:
        webbrowser.open(info.official_url)
