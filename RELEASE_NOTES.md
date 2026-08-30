# CodeLens AI v1.0 — Offline AI Code Explainer

**CodeLens AI** is an offline, private, desktop-grade AI Code Intelligence workspace powered locally by **Ollama** running **Qwen2.5-Coder 3B**.

---

## 🚀 Quick Download & Install (Windows)

1. Download **[`CodeLensAI-Setup.exe`](https://github.com/mrfrosty7007/CodeLens-AI/releases/download/v1.0.0/CodeLensAI-Setup.exe)** from this release.
2. Run the installer and click **Install**.
3. Launch **CodeLens AI** from your Start Menu, Desktop, or the installer finish screen.
4. Complete the guided one-time setup:
   - **Ollama Detection**: Verifies or installs Ollama automatically via Windows Package Manager (`winget`).
   - **Local Inference Engine**: Automatically boots `ollama serve` in the background.
   - **AI Model Download**: Downloads `qwen2.5-coder:3b` (~1.9 GB) directly to local storage.
5. CodeLens AI opens automatically in your browser—**100% private, local, and offline**.

> **Note:** The model download (~1.9 GB) is a **one-time setup**. Afterward, CodeLens AI operates completely offline with zero internet access required.

---

## ✨ Key Highlights in v1.0

### 🤖 Local Offline AI Engine
- **Ollama & Qwen2.5-Coder 3B**: 100% local inference with zero cloud dependency and zero telemetry.
- **Explain Mode**: Step-by-step logic explanations, algorithm analysis, $O(N)$ time & space complexity breakdowns, and key function/variable explanations.
- **Improve Mode**: Clean code refactoring for readability, idiomatic style, and maintainability with change summaries.
- **Optimize Mode**: Algorithmic performance optimization with auto-editor insertion and instant 1-click Undo.

### ⚡ Multi-Language Sandboxes & One-Click Installers
- **Multi-Language Support**: Safe, isolated execution for **Python**, **JavaScript** (Node.js), **Java** (JDK 17+), and **C++** (MinGW/UCRT64 GCC).
- **One-Click Runtime Installers**: In-app one-click installation and detection refresh for missing compilers and interpreters via `winget` and MSYS2.
- **Sandboxed Execution**: Subprocess isolation with real-time stdout/stderr capture, exit codes, millisecond timing, and strict 5-second timeout guards.

### 🎨 Project Helix UI Workspace
- **Modern IDE Aesthetic**: Matte graphite dark theme inspired by Cursor, VS Code, and Linear.
- **High-Density Split Layout**: 20% VS Code Explorer file tree + 80% dominant code editor with line number gutter and synchronized status bar.
- **Interactive Output Dock**: Terminal execution tab with exit codes and markdown analysis export.

### 🖥️ Commercial-Grade Windows Distribution
- **Zero-Friction Installer (`CodeLensAI-Setup.exe`)**: Compact ~97 MB installer with Start Menu and Desktop shortcuts, zero-UAC installation, and clean uninstaller.
- **Headless Native Launcher (`CodeLensAI.exe`)**: Starts background server silently with zero flashing terminal windows and opens exactly one browser tab.

---

## 📦 Release Assets & Checksums

| File | Size | SHA-256 Checksum | Description |
| :--- | :--- | :--- | :--- |
| **`CodeLensAI-Setup.exe`** | ~97 MB | `f25c21e83dcb4dd2bf820c3032778d415ea2462917de16783d67730c74e4d4bb` | Standalone Windows 1-Click Installer |
| `Source code (zip)` | — | — | Source code archive |
| `Source code (tar.gz)` | — | — | Source code tarball |

