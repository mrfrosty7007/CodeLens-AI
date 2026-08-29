"""Code execution engine for Python, C++, Java, and JavaScript."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int | None
    execution_time_ms: float
    error_message: str | None = None
    is_timeout: bool = False
    is_missing_toolchain: bool = False

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0 and not self.error_message and not self.is_timeout


def run_code(language: str, code: str, timeout: float = 5.0) -> ExecutionResult:
    """Execute code for supported languages in a temporary directory with a timeout."""
    lang = language.strip().lower()
    start_time = time.perf_counter()

    if not code.strip():
        return ExecutionResult(
            stdout="",
            stderr="",
            exit_code=None,
            execution_time_ms=0.0,
            error_message="No code provided to execute.",
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            if lang in ("python", "py"):
                return _run_python(code, temp_dir, timeout, start_time)
            elif lang in ("c++", "cpp"):
                return _run_cpp(code, temp_dir, timeout, start_time)
            elif lang in ("java",):
                return _run_java(code, temp_dir, timeout, start_time)
            elif lang in ("javascript", "js"):
                return _run_javascript(code, temp_dir, timeout, start_time)
            else:
                return ExecutionResult(
                    stdout="",
                    stderr="",
                    exit_code=None,
                    execution_time_ms=0.0,
                    error_message=f"Unsupported language: {language}",
                )
        except Exception as exc:
            duration = (time.perf_counter() - start_time) * 1000
            return ExecutionResult(
                stdout="",
                stderr=str(exc),
                exit_code=-1,
                execution_time_ms=duration,
                error_message=f"Execution error: {exc}",
            )


def _run_python(code: str, temp_dir: str, timeout: float, start_time: float) -> ExecutionResult:
    python_exe = sys.executable or shutil.which("python") or shutil.which("python3")
    if not python_exe:
        return ExecutionResult(
            stdout="",
            stderr="",
            exit_code=None,
            execution_time_ms=0.0,
            error_message="Python interpreter not found in system PATH.",
            is_missing_toolchain=True,
        )

    file_path = os.path.join(temp_dir, "script.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        proc = subprocess.run(
            [python_exe, file_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            cwd=temp_dir,
        )
        duration = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.returncode,
            execution_time_ms=duration,
        )
    except subprocess.TimeoutExpired:
        duration = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            stdout="",
            stderr=f"Execution timed out after {int(timeout)} seconds.",
            exit_code=None,
            execution_time_ms=duration,
            is_timeout=True,
            error_message=f"Execution timed out after {int(timeout)} seconds.",
        )


def _run_cpp(code: str, temp_dir: str, timeout: float, start_time: float) -> ExecutionResult:
    compiler = shutil.which("g++") or shutil.which("clang++")
    if not compiler:
        return ExecutionResult(
            stdout="",
            stderr="",
            exit_code=None,
            execution_time_ms=0.0,
            error_message="C++ compiler (g++ or clang++) is not installed or not found in system PATH.",
            is_missing_toolchain=True,
        )

    src_file = os.path.join(temp_dir, "main.cpp")
    exe_name = "main.exe" if os.name == "nt" else "main"
    exe_file = os.path.join(temp_dir, exe_name)

    with open(src_file, "w", encoding="utf-8") as f:
        f.write(code)

    # Compile
    try:
        compile_proc = subprocess.run(
            [compiler, "-O2", "-std=c++17", "-o", exe_file, src_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            cwd=temp_dir,
        )
    except subprocess.TimeoutExpired:
        duration = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            stdout="",
            stderr=f"Compilation timed out after {int(timeout)} seconds.",
            exit_code=None,
            execution_time_ms=duration,
            is_timeout=True,
            error_message=f"Compilation timed out after {int(timeout)} seconds.",
        )

    if compile_proc.returncode != 0:
        duration = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            stdout=compile_proc.stdout,
            stderr=compile_proc.stderr,
            exit_code=compile_proc.returncode,
            execution_time_ms=duration,
            error_message="C++ compilation failed.",
        )

    # Run executable
    try:
        run_proc = subprocess.run(
            [exe_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            cwd=temp_dir,
        )
        duration = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            stdout=run_proc.stdout,
            stderr=run_proc.stderr,
            exit_code=run_proc.returncode,
            execution_time_ms=duration,
        )
    except subprocess.TimeoutExpired:
        duration = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            stdout="",
            stderr=f"Execution timed out after {int(timeout)} seconds.",
            exit_code=None,
            execution_time_ms=duration,
            is_timeout=True,
            error_message=f"Execution timed out after {int(timeout)} seconds.",
        )


def _run_java(code: str, temp_dir: str, timeout: float, start_time: float) -> ExecutionResult:
    javac = shutil.which("javac")
    java = shutil.which("java")
    if not javac or not java:
        return ExecutionResult(
            stdout="",
            stderr="",
            exit_code=None,
            execution_time_ms=0.0,
            error_message="Java compiler (javac) or runtime (java) is not installed or not found in system PATH.",
            is_missing_toolchain=True,
        )

    # Detect class name from code
    match = re.search(r"\bpublic\s+class\s+([A-Za-z0-9_]+)", code)
    if not match:
        match = re.search(r"\bclass\s+([A-Za-z0-9_]+)", code)
    class_name = match.group(1) if match else "Main"

    src_file = os.path.join(temp_dir, f"{class_name}.java")
    with open(src_file, "w", encoding="utf-8") as f:
        f.write(code)

    # Compile
    try:
        compile_proc = subprocess.run(
            [javac, src_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            cwd=temp_dir,
        )
    except subprocess.TimeoutExpired:
        duration = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            stdout="",
            stderr=f"Compilation timed out after {int(timeout)} seconds.",
            exit_code=None,
            execution_time_ms=duration,
            is_timeout=True,
            error_message=f"Compilation timed out after {int(timeout)} seconds.",
        )

    if compile_proc.returncode != 0:
        duration = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            stdout=compile_proc.stdout,
            stderr=compile_proc.stderr,
            exit_code=compile_proc.returncode,
            execution_time_ms=duration,
            error_message="Java compilation failed.",
        )

    # Run
    try:
        run_proc = subprocess.run(
            [java, "-cp", temp_dir, class_name],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            cwd=temp_dir,
        )
        duration = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            stdout=run_proc.stdout,
            stderr=run_proc.stderr,
            exit_code=run_proc.returncode,
            execution_time_ms=duration,
        )
    except subprocess.TimeoutExpired:
        duration = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            stdout="",
            stderr=f"Execution timed out after {int(timeout)} seconds.",
            exit_code=None,
            execution_time_ms=duration,
            is_timeout=True,
            error_message=f"Execution timed out after {int(timeout)} seconds.",
        )


def _run_javascript(code: str, temp_dir: str, timeout: float, start_time: float) -> ExecutionResult:
    node = shutil.which("node")
    if not node:
        return ExecutionResult(
            stdout="",
            stderr="",
            exit_code=None,
            execution_time_ms=0.0,
            error_message="Node.js (node) runtime is not installed or not found in system PATH.",
            is_missing_toolchain=True,
        )

    src_file = os.path.join(temp_dir, "script.js")
    with open(src_file, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        run_proc = subprocess.run(
            [node, src_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            cwd=temp_dir,
        )
        duration = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            stdout=run_proc.stdout,
            stderr=run_proc.stderr,
            exit_code=run_proc.returncode,
            execution_time_ms=duration,
        )
    except subprocess.TimeoutExpired:
        duration = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            stdout="",
            stderr=f"Execution timed out after {int(timeout)} seconds.",
            exit_code=None,
            execution_time_ms=duration,
            is_timeout=True,
            error_message=f"Execution timed out after {int(timeout)} seconds.",
        )
