"""Automated build pipeline for CodeLens AI Windows Installer (Phase H3.4).

Architecture:
1. PyInstaller in `--onedir` mode to compile native launcher (CodeLensAI.exe).
2. Bundle the existing `.venv` directly as `runtime/`.
3. Launch using: `runtime\\Scripts\\pythonw.exe -m streamlit run app.py`
4. Package the resulting folder with NSIS into dist/CodeLensAI-Setup.exe.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BUILD_DIR = ROOT_DIR / "build"
PYINSTALLER_DIST = BUILD_DIR / "pyinstaller_dist"
PYINSTALLER_WORK = BUILD_DIR / "pyinstaller_work"
PACKAGE_DIR = BUILD_DIR / "package"
PACKAGE_RUNTIME_DIR = PACKAGE_DIR / "runtime"
DIST_DIR = ROOT_DIR / "dist"
ASSETS_DIR = ROOT_DIR / "assets"
ICON_PATH = ASSETS_DIR / "icon.ico"
NSIS_SCRIPT = ROOT_DIR / "installer.nsi"
SETUP_EXE = DIST_DIR / "CodeLensAI-Setup.exe"
VENV_DIR = ROOT_DIR / ".venv"


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
    for req_file in ["launcher.py", "app.py", "setup_manager.py", "runtime_manager.py", "code_runner.py", "ollama_client.py", "prompts.py"]:
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

    # 4. Check NSIS
    makensis = find_makensis()
    if makensis:
        print(f"    Found NSIS compiler: {makensis}", flush=True)
    else:
        print("    [!] Warning: makensis not found. Final installer step will require NSIS.", flush=True)

    # 5. Clean build work directories
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
        "--hidden-import=urllib.request",
        "--hidden-import=ctypes",
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


def step_4_bundle_venv_runtime() -> None:
    """[4/7] Bundling existing .venv as runtime/ into build/package/runtime/."""
    print("\n[4/7] Bundling .venv as runtime/")
    if PACKAGE_RUNTIME_DIR.exists():
        shutil.rmtree(PACKAGE_RUNTIME_DIR, ignore_errors=True)

    def ignore_patterns(path: str, names: list[str]) -> set[str]:
        ignored = set()
        for name in names:
            if name == "__pycache__" or name.endswith(".pyc"):
                ignored.add(name)
        return ignored

    print(f"    Copying {format_rel_path(VENV_DIR)} -> {format_rel_path(PACKAGE_RUNTIME_DIR)}...", flush=True)
    t0 = time.time()
    shutil.copytree(VENV_DIR, PACKAGE_RUNTIME_DIR, ignore=ignore_patterns, dirs_exist_ok=True)
    elapsed = time.time() - t0

    target_pyw = PACKAGE_RUNTIME_DIR / "Scripts" / "pythonw.exe"
    target_py = PACKAGE_RUNTIME_DIR / "Scripts" / "python.exe"
    if not target_pyw.is_file() or not target_py.is_file():
        raise RuntimeError(f"Bundled runtime missing python executables in {format_rel_path(PACKAGE_RUNTIME_DIR / 'Scripts')}")

    item_count = sum(1 for _ in PACKAGE_RUNTIME_DIR.rglob("*"))
    print(f"[OK] Bundled {item_count} runtime files in {elapsed:.2f}s: {format_rel_path(target_pyw)}")


def step_5_verify_runtime() -> None:
    """[5/7] Verifying bundled Streamlit runtime and package imports."""
    print("\n[5/7] Verifying bundled runtime")
    pkg_py = PACKAGE_RUNTIME_DIR / "Scripts" / "python.exe"

    # 1. Verify Streamlit CLI execution
    print(f"    Testing: {format_rel_path(pkg_py)} -m streamlit --version", flush=True)
    res = subprocess.run(
        [str(pkg_py), "-m", "streamlit", "--version"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Streamlit verification failed:\nStderr: {res.stderr}\nStdout: {res.stdout}")
    print(f"    [OK] Streamlit version: {res.stdout.strip()}", flush=True)

    # 2. Verify all application imports within package environment
    print("    Testing application module imports...", flush=True)
    test_import_cmd = [
        str(pkg_py),
        "-c",
        "import streamlit, httpx, pygments, app, setup_manager, runtime_manager, code_runner, ollama_client, prompts; print('__PACKAGE_READY__')",
    ]
    res_import = subprocess.run(
        test_import_cmd,
        cwd=str(PACKAGE_DIR),
        capture_output=True,
        text=True,
        timeout=15,
    )
    if res_import.returncode != 0 or "__PACKAGE_READY__" not in res_import.stdout:
        raise RuntimeError(
            f"Import validation failed:\nStderr: {res_import.stderr}\nStdout: {res_import.stdout}"
        )
    print(f"[OK] Runtime and dependencies verified successfully.")


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
    print("CodeLens AI -- Packaging Pipeline Complete")
    print("=" * 60)
    if setup_path and setup_path.is_file():
        size_mb = setup_path.stat().st_size / (1024 * 1024)
        checksum = calculate_sha256(setup_path)
        print(f"Installer Executable : {format_rel_path(setup_path)}")
        print(f"Installer Size       : {size_mb:.2f} MB")
        print(f"SHA-256 Checksum     : {checksum}")
        print("\n100% Standalone - Ready for one-click deployment.")
    else:
        print(f"Standalone Package   : {format_rel_path(PACKAGE_DIR)}")
        print("Run CodeLensAI.exe inside build/package/ to launch.")
    print("=" * 60)


def main() -> None:
    total_t0 = time.time()
    step_1_verify_prerequisites()
    launcher_exe = step_2_compile_launcher()
    step_3_assemble_package(launcher_exe)
    step_4_bundle_venv_runtime()
    step_5_verify_runtime()
    setup_path = step_6_build_nsis_installer()
    step_7_build_summary(setup_path)
    total_elapsed = time.time() - total_t0
    print(f"\nTotal Pipeline Execution Time: {total_elapsed:.2f} seconds\n")


if __name__ == "__main__":
    main()
