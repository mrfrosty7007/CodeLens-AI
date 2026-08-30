"""Automated build pipeline for CodeLens AI Windows Installer (Phase Beta 2.1).

Architecture:
1. PyInstaller in `--onedir` mode to compile native launcher (CodeLensAI.exe).
2. Bundle official portable Python 3.12 Embeddable package directly as `runtime/`.
3. Stage and bundle OllamaSetup.exe for silent local AI runtime onboarding.
4. Package the resulting folder with NSIS into dist/CodeLensAI-Setup.exe with explicit portable runtime verification.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

ROOT_DIR = Path(__file__).resolve().parent
BUILD_DIR = ROOT_DIR / "build"
PYINSTALLER_DIST = BUILD_DIR / "pyinstaller_dist"
PYINSTALLER_WORK = BUILD_DIR / "pyinstaller_work"
PACKAGE_DIR = BUILD_DIR / "package"
PACKAGE_RUNTIME_DIR = PACKAGE_DIR / "runtime"
DIST_DIR = ROOT_DIR / "dist"
ASSETS_DIR = ROOT_DIR / "assets"
TOOLS_DIR = ROOT_DIR / "tools"
ICON_PATH = ASSETS_DIR / "icon.ico"
NSIS_SCRIPT = ROOT_DIR / "installer.nsi"
SETUP_EXE = DIST_DIR / "CodeLensAI-Setup.exe"
VENV_DIR = ROOT_DIR / ".venv"
OLLAMA_SETUP_EXE = TOOLS_DIR / "OllamaSetup.exe"
OLLAMA_DOWNLOAD_URL = "https://ollama.com/download/OllamaSetup.exe"
PYTHON_EMBED_ZIP = TOOLS_DIR / "python-3.12.10-embed-amd64.zip"
PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"


def format_rel_path(p: Path | str) -> str:
    """Format a path relative to ROOT_DIR with forward slashes for clean logs."""
    try:
        path_obj = Path(p)
        if path_obj.is_relative_to(ROOT_DIR):
            return str(path_obj.relative_to(ROOT_DIR)).replace("\\", "/")
    except Exception:
        pass
    return str(p).replace("\\", "/")


def run_command_streaming(
    cmd: list[str],
    cwd: Path | None = None,
    description: str = "",
) -> subprocess.CompletedProcess:
    """Run a subprocess command and stream its stdout/stderr in real time to avoid silent timeouts."""
    if description:
        print(f"--> {description}")

    display_cmd = [format_rel_path(arg) for arg in cmd]
    print(f"Executing: {' '.join(display_cmd)}", flush=True)

    process = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else str(ROOT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    output_lines: list[str] = []
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            clean_line = line.rstrip("\r\n")
            output_lines.append(clean_line)
            print(f"    {clean_line}", flush=True)

    ret = process.poll()
    if ret != 0:
        full_out = "\n".join(output_lines)
        raise RuntimeError(f"Command failed with exit code {ret}: {' '.join(display_cmd)}\n{full_out}")

    return subprocess.CompletedProcess(args=cmd, returncode=ret, stdout="\n".join(output_lines))


def find_makensis() -> str | None:
    """Find the makensis compiler executable."""
    found = shutil.which("makensis")
    if found:
        return found

    candidates = [
        ROOT_DIR / "tools" / "nsis-3.10" / "Bin" / "makensis.exe",
        ROOT_DIR / "tools" / "nsis" / "Bin" / "makensis.exe",
        ROOT_DIR / "tools" / "nsis-3.10" / "makensis.exe",
        ROOT_DIR / "tools" / "nsis" / "makensis.exe",
        Path("C:/Program Files (x86)/NSIS/makensis.exe"),
        Path("C:/Program Files/NSIS/makensis.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "NSIS" / "makensis.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "NSIS" / "makensis.exe",
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "NSIS" / "makensis.exe",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    return None


def calculate_sha256(file_path: Path) -> str:
    """Compute the SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def ensure_ollama_installer() -> Path:
    """Ensure OllamaSetup.exe is available in tools/ directory for NSIS bundling."""
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    if OLLAMA_SETUP_EXE.is_file() and OLLAMA_SETUP_EXE.stat().st_size > 10_000_000:
        print(f"    Found Ollama installer: {format_rel_path(OLLAMA_SETUP_EXE)} ({OLLAMA_SETUP_EXE.stat().st_size / (1024*1024):.1f} MB)", flush=True)
        return OLLAMA_SETUP_EXE

    cached_candidates = [
        Path.home() / "Downloads" / "OllamaSetup.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Temp" / "OllamaSetup.exe",
    ]
    for cand in cached_candidates:
        if cand.is_file() and cand.stat().st_size > 10_000_000:
            print(f"    Copying cached Ollama installer from {cand}...", flush=True)
            shutil.copy2(cand, OLLAMA_SETUP_EXE)
            return OLLAMA_SETUP_EXE

    print(f"    Downloading Ollama installer from {OLLAMA_DOWNLOAD_URL}...", flush=True)
    req = urllib.request.Request(OLLAMA_DOWNLOAD_URL, headers={"User-Agent": "CodeLensAI-Builder/1.0"})
    with urllib.request.urlopen(req) as resp, open(OLLAMA_SETUP_EXE, "wb") as out_f:
        total_size = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        t0 = time.time()
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out_f.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                pct = (downloaded / total_size) * 100
                mb_done = downloaded / (1024 * 1024)
                mb_tot = total_size / (1024 * 1024)
                print(f"    Downloading Ollama: {mb_done:.1f} MB / {mb_tot:.1f} MB ({pct:.1f}%)", end="\r", flush=True)

    elapsed = time.time() - t0
    print(f"\n    [OK] Ollama installer downloaded in {elapsed:.1f}s: {format_rel_path(OLLAMA_SETUP_EXE)}")
    return OLLAMA_SETUP_EXE


def ensure_python_embed_package() -> Path:
    """Ensure Python 3.12 64-bit embeddable package is downloaded in tools/."""
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    if PYTHON_EMBED_ZIP.is_file() and PYTHON_EMBED_ZIP.stat().st_size > 5_000_000:
        print(f"    Found Python embeddable zip: {format_rel_path(PYTHON_EMBED_ZIP)} ({PYTHON_EMBED_ZIP.stat().st_size / (1024*1024):.1f} MB)", flush=True)
        return PYTHON_EMBED_ZIP

    print(f"    Downloading Python 3.12 embeddable package from {PYTHON_EMBED_URL}...", flush=True)
    req = urllib.request.Request(PYTHON_EMBED_URL, headers={"User-Agent": "CodeLensAI-Builder/1.0"})
    with urllib.request.urlopen(req) as resp, open(PYTHON_EMBED_ZIP, "wb") as out_f:
        shutil.copyfileobj(resp, out_f)
    print(f"    [OK] Python embeddable package downloaded: {format_rel_path(PYTHON_EMBED_ZIP)}")
    return PYTHON_EMBED_ZIP


# ==============================================================================
# Build Pipeline Stages (1 to 7)
# ==============================================================================

def step_1_verify_prerequisites() -> None:
    """[1/7] Verifying prerequisites and preparing build directories."""
    print("\n[1/7] Verifying build prerequisites")

    # 1. Verify virtual environment exists
    venv_py = VENV_DIR / "Scripts" / "python.exe"
    venv_pyw = VENV_DIR / "Scripts" / "pythonw.exe"
    if not venv_py.is_file():
        raise RuntimeError(f"Virtual environment python not found at {format_rel_path(venv_py)}")
    if not venv_pyw.is_file():
        raise RuntimeError(f"Virtual environment pythonw not found at {format_rel_path(venv_pyw)}")
    print(f"    Found virtual environment: {format_rel_path(VENV_DIR)}", flush=True)

    # 2. Verify launcher and app source files
    for req_file in ["launcher.py", "app.py", "setup_manager.py", "runtime_manager.py", "code_runner.py", "prompts.py", "ollama_client.py"]:
        p = ROOT_DIR / req_file
        if not p.is_file():
            raise RuntimeError(f"Required source file missing: {format_rel_path(p)}")
    print("    Verified core application source files.", flush=True)

    # 3. Ensure icon exists
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    if not ICON_PATH.is_file():
        print("    Generating application icons...", flush=True)
        import generate_icons
        generate_icons.main()
    print(f"    Application icon: {format_rel_path(ICON_PATH)}", flush=True)

    # 4. Stage Ollama & Python embed installers
    ensure_ollama_installer()
    ensure_python_embed_package()

    # 5. Check NSIS compiler
    makensis = find_makensis()
    if makensis:
        print(f"    Found NSIS compiler: {makensis}", flush=True)
    else:
        print("    [!] Warning: makensis not found. Final installer step will require NSIS.", flush=True)

    # 6. Clean build work directories
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR, ignore_errors=True)
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    print("[OK] Prerequisites verified.")


def step_2_compile_launcher() -> Path:
    """[2/7] Compiling native launcher via PyInstaller in --onedir mode."""
    print("\n[2/7] Compiling native launcher (PyInstaller --onedir)")
    venv_py = VENV_DIR / "Scripts" / "python.exe"

    cmd = [
        str(venv_py),
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--icon={ICON_PATH}",
        "--name=CodeLensAI",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=urllib.request",
        "--hidden-import=urllib.error",
        "--hidden-import=json",
        "--hidden-import=threading",
        "--hidden-import=ctypes",
        "--hidden-import=socket",
        "--distpath",
        str(PYINSTALLER_DIST),
        "--workpath",
        str(PYINSTALLER_WORK),
        str(ROOT_DIR / "launcher.py"),
    ]

    t0 = time.time()
    run_command_streaming(cmd, description="Compiling launcher.py into CodeLensAI.exe")
    elapsed = time.time() - t0

    launcher_exe = PYINSTALLER_DIST / "CodeLensAI" / "CodeLensAI.exe"
    if not launcher_exe.is_file():
        raise RuntimeError(f"PyInstaller build failed to create {launcher_exe}")

    print(f"[OK] Native launcher compiled in {elapsed:.2f}s: {format_rel_path(launcher_exe)}")
    return launcher_exe


def step_3_assemble_package(launcher_exe: Path) -> None:
    """[3/7] Assembling distribution package structure in build/package/."""
    print("\n[3/7] Assembling package structure")

    # 1. Copy PyInstaller output folder contents
    launcher_dir = launcher_exe.parent
    print(f"    Copying launcher binaries from {format_rel_path(launcher_dir)}...", flush=True)
    for item in launcher_dir.iterdir():
        dest = PACKAGE_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    # 2. Copy core application files
    print("    Copying application files...", flush=True)
    app_files = [
        "app.py",
        "styles.css",
        "code_runner.py",
        "runtime_manager.py",
        "ollama_client.py",
        "gemini_client.py",
        "prompts.py",
        "setup_manager.py",
        "launcher.py",
        "requirements.txt",
        "README.md",
    ]
    for fname in app_files:
        src = ROOT_DIR / fname
        if src.is_file():
            shutil.copy2(src, PACKAGE_DIR / fname)

    # 3. Copy assets
    if ASSETS_DIR.exists():
        print("    Copying assets...", flush=True)
        shutil.copytree(ASSETS_DIR, PACKAGE_DIR / "assets", dirs_exist_ok=True)

    print(f"[OK] Package files assembled in {format_rel_path(PACKAGE_DIR)}")


def step_4_bundle_portable_runtime() -> None:
    """[4/7] Bundling official Python 3.12 Embeddable package into build/package/runtime/."""
    print("\n[4/7] Bundling portable Python 3.12 embeddable runtime")
    if PACKAGE_RUNTIME_DIR.exists():
        shutil.rmtree(PACKAGE_RUNTIME_DIR, ignore_errors=True)
    PACKAGE_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Extract official embeddable Python package
    embed_zip = ensure_python_embed_package()
    print(f"    Extracting {format_rel_path(embed_zip)} -> {format_rel_path(PACKAGE_RUNTIME_DIR)}...", flush=True)
    with zipfile.ZipFile(embed_zip, "r") as z:
        z.extractall(PACKAGE_RUNTIME_DIR)

    # 2. Configure ._pth file to enable site-packages and full importlib support
    pth_files = list(PACKAGE_RUNTIME_DIR.glob("python*._pth"))
    pth_file = pth_files[0] if pth_files else PACKAGE_RUNTIME_DIR / "python312._pth"

    pth_content = "python312.zip\n.\nLib\nLib/site-packages\n\nimport site\n"
    pth_file.write_text(pth_content, encoding="utf-8")
    print(f"    Configured runtime search paths in {pth_file.name}", flush=True)

    # 3. Copy site-packages from local .venv to runtime/Lib/site-packages
    site_packages_src = VENV_DIR / "Lib" / "site-packages"
    site_packages_dst = PACKAGE_RUNTIME_DIR / "Lib" / "site-packages"
    site_packages_dst.mkdir(parents=True, exist_ok=True)

    def ignore_patterns(path: str, names: list[str]) -> set[str]:
        ignored = set()
        for name in names:
            n_lower = name.lower()
            if n_lower in ("__pycache__", "tests", "test", "testing", "pip", "pkg_resources", "pyinstaller"):
                ignored.add(name)
            elif n_lower.endswith((".pyc", ".pyo", ".h", ".c", ".lib", ".pdb", ".map")):
                ignored.add(name)
        return ignored

    print(f"    Copying packages: {format_rel_path(site_packages_src)} -> {format_rel_path(site_packages_dst)}...", flush=True)
    t0 = time.time()
    shutil.copytree(site_packages_src, site_packages_dst, ignore=ignore_patterns, dirs_exist_ok=True)
    elapsed = time.time() - t0

    # 4. Copy Tkinter/Tcl DLLs and tcl support directory from Python standard installation if available
    local_py_bases = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" / "Python312",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Python312",
        Path("C:/Python312"),
    ]
    for local_py in local_py_bases:
        if (local_py / "tcl").is_dir():
            shutil.copytree(local_py / "tcl", PACKAGE_RUNTIME_DIR / "tcl", dirs_exist_ok=True)
        if (local_py / "DLLs" / "_tkinter.pyd").is_file():
            shutil.copy2(local_py / "DLLs" / "_tkinter.pyd", PACKAGE_RUNTIME_DIR / "_tkinter.pyd")
        if (local_py / "DLLs" / "tcl86t.dll").is_file():
            shutil.copy2(local_py / "DLLs" / "tcl86t.dll", PACKAGE_RUNTIME_DIR / "tcl86t.dll")
        if (local_py / "DLLs" / "tk86t.dll").is_file():
            shutil.copy2(local_py / "DLLs" / "tk86t.dll", PACKAGE_RUNTIME_DIR / "tk86t.dll")

    # 5. Ensure NO pyvenv.cfg exists in runtime
    pyvenv_cfg = PACKAGE_RUNTIME_DIR / "pyvenv.cfg"
    if pyvenv_cfg.exists():
        pyvenv_cfg.unlink(missing_ok=True)

    target_py = PACKAGE_RUNTIME_DIR / "python.exe"
    target_pyw = PACKAGE_RUNTIME_DIR / "pythonw.exe"
    if not target_py.is_file() or not target_pyw.is_file():
        raise RuntimeError(f"Portable runtime missing python executables in {format_rel_path(PACKAGE_RUNTIME_DIR)}")

    item_count = sum(1 for _ in PACKAGE_RUNTIME_DIR.rglob("*") if _.is_file())
    size_mb = sum(f.stat().st_size for f in PACKAGE_RUNTIME_DIR.rglob("*") if f.is_file()) / (1024 * 1024)
    print(f"[OK] Portable embeddable runtime assembled in {elapsed:.2f}s ({item_count} files, {size_mb:.1f} MB)")


def step_5_verify_runtime() -> None:
    """[5/7] Verifying bundled portable runtime in two stages with diagnostics."""
    print("\n[5/7] Verifying bundled portable runtime")
    pkg_py = PACKAGE_RUNTIME_DIR / "python.exe"

    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    # Stage 1: Basic Python execution (timeout: 10s)
    print(f"    Testing: {format_rel_path(pkg_py)} -c \"print('PY_OK')\"", flush=True)
    try:
        res1 = subprocess.run(
            [str(pkg_py), "-c", "print('PY_OK')"],
            cwd=str(PACKAGE_RUNTIME_DIR),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Stage 1 verification timed out after 10 seconds.")

    if res1.returncode != 0 or "PY_OK" not in res1.stdout:
        raise RuntimeError(f"Stage 1 failed (exit code {res1.returncode}):\nStderr: {res1.stderr}\nStdout: {res1.stdout}")
    print(f"    [OK] {res1.stdout.strip()}", flush=True)

    # Stage 2: Package imports verification (timeout: 60s)
    print(f"    Testing: {format_rel_path(pkg_py)} -c \"import streamlit, google.genai, pygments; print('IMPORT_OK')\"", flush=True)
    try:
        res2 = subprocess.run(
            [str(pkg_py), "-c", "import streamlit, google.genai, pygments; print('IMPORT_OK')"],
            cwd=str(PACKAGE_RUNTIME_DIR),
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        print("\n[!] Stage 2 timed out after 60 seconds. Collecting diagnostic information...", flush=True)
        diag = subprocess.run(
            [str(pkg_py), "-c", "import sys, site; print('sys.path:', sys.path); print('site.getsitepackages():', getattr(site, 'getsitepackages', lambda: 'N/A')())"],
            cwd=str(PACKAGE_RUNTIME_DIR),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            stdin=subprocess.DEVNULL,
        )
        print(f"Diagnostics:\nStdout: {diag.stdout}\nStderr: {diag.stderr}", flush=True)
        raise RuntimeError("Stage 2 package import verification timed out after 60 seconds.")

    if res2.returncode != 0 or "IMPORT_OK" not in res2.stdout:
        print("\n[!] Stage 2 import verification failed. Collecting diagnostic information...", flush=True)
        diag = subprocess.run(
            [str(pkg_py), "-c", "import sys, site; print('sys.path:', sys.path); print('site.getsitepackages():', getattr(site, 'getsitepackages', lambda: 'N/A')())"],
            cwd=str(PACKAGE_RUNTIME_DIR),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            stdin=subprocess.DEVNULL,
        )
        print(f"Diagnostics:\nStdout: {diag.stdout}\nStderr: {diag.stderr}", flush=True)
        raise RuntimeError(f"Stage 2 package imports failed (exit code {res2.returncode}):\nStderr: {res2.stderr}\nStdout: {res2.stdout}")

    print(f"    [OK] {res2.stdout.strip()}", flush=True)
    print(f"[OK] Portable runtime and all dependencies verified successfully.")


def step_6_build_nsis_installer() -> Path | None:
    """[6/7] Building NSIS installer (dist/CodeLensAI-Setup.exe)."""
    print("\n[6/7] Building NSIS installer")
    makensis = find_makensis()
    if not makensis:
        print("\n[!] makensis.exe not found on system PATH or standard folders.", flush=True)
        print("    Please install NSIS or ensure tools/nsis-3.10/makensis.exe exists.", flush=True)
        return None

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [makensis, str(NSIS_SCRIPT)]
    t0 = time.time()
    run_command_streaming(cmd, description="Compiling NSIS Setup Executable")
    elapsed = time.time() - t0

    if not SETUP_EXE.is_file():
        raise RuntimeError(f"NSIS compiler completed but {SETUP_EXE} was not found.")

    print(f"[OK] Standalone installer built in {elapsed:.2f}s: {format_rel_path(SETUP_EXE)}")
    return SETUP_EXE


def step_7_build_summary(setup_path: Path | None) -> None:
    """[7/7] Build summary report."""
    print("\n[7/7] Build summary")
    print("=" * 60)
    print("CodeLens AI -- Packaging Pipeline Complete (Beta 2.1)")
    print("=" * 60)
    if setup_path and setup_path.is_file():
        size_mb = setup_path.stat().st_size / (1024 * 1024)
        checksum = calculate_sha256(setup_path)
        print(f"Installer Executable : {format_rel_path(setup_path)}")
        print(f"Installer Size       : {size_mb:.2f} MB")
        print(f"SHA-256 Checksum     : {checksum}")
        print("\n100% Standalone Portable Runtime - Ready for one-click deployment.")
    else:
        print(f"Standalone Package   : {format_rel_path(PACKAGE_DIR)}")
        print("Run CodeLensAI.exe inside build/package/ to launch.")
    print("=" * 60)


def main() -> None:
    total_t0 = time.time()
    step_1_verify_prerequisites()
    launcher_exe = step_2_compile_launcher()
    step_3_assemble_package(launcher_exe)
    step_4_bundle_portable_runtime()
    step_5_verify_runtime()
    setup_path = step_6_build_nsis_installer()
    step_7_build_summary(setup_path)
    total_elapsed = time.time() - total_t0
    print(f"\nTotal Pipeline Execution Time: {total_elapsed:.2f} seconds\n")


if __name__ == "__main__":
    main()
