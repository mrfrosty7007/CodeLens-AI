"""Automated build pipeline for CodeLens AI Linux AppImage (x86_64).

Produces: dist/CodeLensAI-1.0.0-x86_64.AppImage

Architecture:
1. Portable Standalone CPython 3.12 (astral-sh/python-build-standalone for x86_64 Linux).
2. Linux x86_64 Wheels for all required dependencies (Streamlit, HTTPX, Pygments, etc.).
3. Standard XDG AppDir layout with AppRun entrypoint, desktop entry, and icons.
4. SquashFS compression via squashfs-tools-ng (gensquashfs).
5. Official AppImage Type 2 runtime header (runtime-x86_64).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BUILD_DIR = ROOT_DIR / "build"
APPIMAGE_WORK = BUILD_DIR / "appimage_work"
APPDIR = APPIMAGE_WORK / "AppDir"
DIST_DIR = ROOT_DIR / "dist"
TOOLS_DIR = ROOT_DIR / "tools" / "appimage"
ASSETS_DIR = ROOT_DIR / "assets"
ICON_PNG = ASSETS_DIR / "icon.png"

OUTPUT_APPIMAGE = DIST_DIR / "CodeLensAI-1.0.0-x86_64.AppImage"

# Download URLs
RUNTIME_URL = "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64"
SQUASHFS_TOOLS_URL = "https://infraroot.at/pub/squashfs/windows/squashfs-tools-ng-1.3.2-mingw64.zip"
PYTHON_STANDALONE_URL = "https://github.com/astral-sh/python-build-standalone/releases/download/20260825/cpython-3.12.14+20260825-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"


def download_file(url: str, dest: Path, desc: str = "") -> None:
    """Download a remote file with user-agent headers and progress logging."""
    if desc:
        print(f"--> {desc}")
    print(f"    Downloading {url} -> {dest.name}...", flush=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    req = urllib.request.Request(url, headers={"User-Agent": "CodeLensAI-Builder/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response, open(dest, "wb") as out_file:
        shutil.copyfileobj(response, out_file)
    print(f"    [OK] Downloaded {dest.name} ({dest.stat().st_size / (1024*1024):.2f} MB)", flush=True)


def calculate_sha256(file_path: Path) -> str:
    """Compute SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def step_1_prepare_tools() -> tuple[Path, Path]:
    """[1/6] Prepare gensquashfs.exe and runtime-x86_64."""
    print("\n[1/6] Preparing Linux packaging tools")
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. runtime-x86_64
    runtime_path = TOOLS_DIR / "runtime-x86_64"
    if not runtime_path.is_file() or runtime_path.stat().st_size < 100000:
        download_file(RUNTIME_URL, runtime_path, "Downloading AppImage Type 2 runtime-x86_64")
    else:
        print(f"    Found runtime-x86_64: {runtime_path.name}", flush=True)

    # 2. gensquashfs.exe
    gensquashfs_candidates = list(TOOLS_DIR.glob("**/gensquashfs.exe"))
    if not gensquashfs_candidates:
        zip_path = TOOLS_DIR / "squashfs-tools-ng.zip"
        download_file(SQUASHFS_TOOLS_URL, zip_path, "Downloading squashfs-tools-ng for Windows")
        print("    Extracting squashfs-tools-ng...", flush=True)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(TOOLS_DIR)
        zip_path.unlink(missing_ok=True)
        gensquashfs_candidates = list(TOOLS_DIR.glob("**/gensquashfs.exe"))

    if not gensquashfs_candidates:
        raise RuntimeError("gensquashfs.exe not found after extracting squashfs-tools-ng.")

    gensquashfs_exe = gensquashfs_candidates[0]
    print(f"    Found gensquashfs: {gensquashfs_exe}", flush=True)

    return runtime_path, gensquashfs_exe


def step_2_prepare_python_runtime() -> None:
    """[2/6] Download and extract standalone Linux CPython 3.12 runtime."""
    print("\n[2/6] Preparing standalone Linux Python 3.12 runtime")
    usr_dir = APPDIR / "usr"
    if usr_dir.exists():
        shutil.rmtree(usr_dir, ignore_errors=True)
    usr_dir.mkdir(parents=True, exist_ok=True)

    tar_path = TOOLS_DIR / "cpython-3.12-linux.tar.gz"
    if not tar_path.is_file() or tar_path.stat().st_size < 10000000:
        download_file(PYTHON_STANDALONE_URL, tar_path, "Downloading Python 3.12 standalone (Linux x86_64)")
    else:
        print(f"    Using cached Python tarball: {tar_path.name}", flush=True)

    print("    Extracting Python runtime into AppDir/usr/...", flush=True)
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(APPDIR)
    
    # python-build-standalone extracts to APPDIR/python/
    extracted_python = APPDIR / "python"
    if extracted_python.is_dir():
        for item in extracted_python.iterdir():
            dest = usr_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
        shutil.rmtree(extracted_python, ignore_errors=True)

    print(f"    [OK] Linux Python 3.12 runtime established at {usr_dir}", flush=True)


def step_3_install_linux_dependencies() -> None:
    """[3/6] Install Linux x86_64 wheels for Streamlit and dependencies into AppDir site-packages."""
    print("\n[3/6] Installing Linux x86_64 Python dependencies")
    site_packages = APPDIR / "usr" / "lib" / "python3.12" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)

    # Read requirements.txt
    req_file = ROOT_DIR / "requirements.txt"
    packages = [
        "streamlit>=1.30.0",
        "httpx>=0.27.0",
        "pygments>=2.17.0",
    ]

    print(f"    Installing dependencies via pip target: {', '.join(packages)}...", flush=True)
    venv_python = ROOT_DIR / ".venv" / "Scripts" / "python.exe"

    cmd = [
        str(venv_python),
        "-m",
        "pip",
        "install",
        "--platform",
        "manylinux2014_x86_64",
        "--target",
        str(site_packages),
        "--only-binary=:all:",
        "--implementation",
        "cp",
        "--python-version",
        "3.12",
        "--upgrade",
    ] + packages

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"    [!] Pip binary install warning: {res.stderr}\nRetrying with no-deps binary...")
        # Fallback install
        cmd_fallback = [
            str(venv_python),
            "-m",
            "pip",
            "install",
            "--platform",
            "manylinux2014_x86_64",
            "--target",
            str(site_packages),
            "--only-binary=:all:",
            "--python-version",
            "3.12",
            "-r",
            str(req_file),
        ]
        res_fb = subprocess.run(cmd_fallback, capture_output=True, text=True)
        if res_fb.returncode != 0:
            raise RuntimeError(f"Pip install failed:\n{res_fb.stderr}\n{res_fb.stdout}")

    pkg_count = sum(1 for _ in site_packages.iterdir())
    print(f"    [OK] Installed {pkg_count} packages/modules into site-packages.", flush=True)


def step_4_assemble_appdir() -> None:
    """[4/6] Copy application source files and generate AppRun, desktop entry, and icon."""
    print("\n[4/6] Assembling AppDir structure")
    app_dir = APPDIR / "app"
    app_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy application files
    app_files = [
        "app.py",
        "styles.css",
        "code_runner.py",
        "runtime_manager.py",
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
            shutil.copy2(src, app_dir / fname)

    # 2. Copy assets
    if ASSETS_DIR.exists():
        shutil.copytree(ASSETS_DIR, app_dir / "assets", dirs_exist_ok=True)

    # 3. Application icon
    if ICON_PNG.is_file():
        shutil.copy2(ICON_PNG, APPDIR / "codelens-ai.png")
        shutil.copy2(ICON_PNG, APPDIR / ".DirIcon")

    # 4. Desktop Entry (codelens-ai.desktop)
    desktop_content = """[Desktop Entry]
Type=Application
Name=CodeLens AI
GenericName=AI Code Intelligence
Comment=AI code explainer, refactorer, and runner powered by Google Gemini 3.6 Flash
Exec=AppRun %F
Icon=codelens-ai
Categories=Development;IDE;
Terminal=false
StartupWMClass=CodeLens AI
"""
    (APPDIR / "codelens-ai.desktop").write_text(desktop_content, encoding="utf-8")

    # 5. AppRun script (POSIX shell entrypoint)
    apprun_content = """#!/usr/bin/env bash
# ==============================================================================
# CodeLens AI - Portable Linux AppImage AppRun Entrypoint
# ==============================================================================
set -e

# Resolve base AppDir path
HERE="$(dirname "$(readlink -f "${0}")")"

export PATH="$HERE/usr/bin:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/lib:$LD_LIBRARY_PATH"
export PYTHONHOME="$HERE/usr"
export PYTHONPATH="$HERE/usr/lib/python3.12/site-packages:$HERE/app:$PYTHONPATH"
export PYTHONUNBUFFERED=1
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Launch application via Python launcher (or directly via Streamlit)
cd "$HERE/app"
exec "$HERE/usr/bin/python3" launcher.py "$@"
"""
    apprun_path = APPDIR / "AppRun"
    apprun_path.write_bytes(apprun_content.replace("\r\n", "\n").encode("utf-8"))

    print(f"    [OK] AppDir assembled with AppRun, desktop entry, and icon.", flush=True)


def step_5_create_appimage(runtime_path: Path, gensquashfs_exe: Path) -> Path:
    """[5/6] Pack SquashFS filesystem and concatenate with AppImage runtime."""
    print("\n[5/6] Building SquashFS image and AppImage")
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    squashfs_img = APPIMAGE_WORK / "squashfs.img"
    if squashfs_img.exists():
        squashfs_img.unlink(missing_ok=True)

    print("    Compressing AppDir with gensquashfs (xz/zstd)...", flush=True)
    cmd = [
        str(gensquashfs_exe),
        "--pack-dir",
        str(APPDIR),
        "-c",
        "gzip",
        str(squashfs_img),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"gensquashfs failed (code {res.returncode}):\n{res.stderr}\n{res.stdout}")

    sqfs_size_mb = squashfs_img.stat().st_size / (1024 * 1024)
    print(f"    [OK] SquashFS image created ({sqfs_size_mb:.2f} MB)", flush=True)

    print("    Concatenating runtime-x86_64 and SquashFS filesystem...", flush=True)
    with open(OUTPUT_APPIMAGE, "wb") as out_f:
        # 1. Write AppImage runtime ELF binary
        with open(runtime_path, "rb") as rt_f:
            shutil.copyfileobj(rt_f, out_f)
        # 2. Append SquashFS data
        with open(squashfs_img, "rb") as sq_f:
            shutil.copyfileobj(sq_f, out_f)

    if not OUTPUT_APPIMAGE.is_file():
        raise RuntimeError(f"Failed to create {OUTPUT_APPIMAGE}")

    print(f"    [OK] Generated {OUTPUT_APPIMAGE.name}", flush=True)
    return OUTPUT_APPIMAGE


def step_6_summary(appimage_path: Path) -> None:
    """[6/6] Print build summary and verification hash."""
    size_mb = appimage_path.stat().st_size / (1024 * 1024)
    checksum = calculate_sha256(appimage_path)

    print("\n" + "=" * 60)
    print("CodeLens AI -- Linux AppImage Build Complete")
    print("=" * 60)
    print(f"AppImage File    : {appimage_path.name}")
    print(f"Full Path        : {appimage_path}")
    print(f"File Size        : {size_mb:.2f} MB ({appimage_path.stat().st_size:,} bytes)")
    print(f"SHA-256 Checksum : {checksum}")
    print("Architecture     : x86_64 (Linux)")
    print("Portable         : 100% Self-Contained (Runs without installation)")
    print("AI Backend       : Google Gemini API (gemini-3.6-flash)")
    print("=" * 60 + "\n")


def main() -> None:
    t0 = time.time()
    runtime_path, gensquashfs_exe = step_1_prepare_tools()
    step_2_prepare_python_runtime()
    step_3_install_linux_dependencies()
    step_4_assemble_appdir()
    appimage = step_5_create_appimage(runtime_path, gensquashfs_exe)
    step_6_summary(appimage)
    print(f"Total Linux Build Execution Time: {time.time() - t0:.2f} seconds\n")


if __name__ == "__main__":
    main()
