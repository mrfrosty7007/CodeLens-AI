# CodeLens AI v1.0 — Cloud AI Code Intelligence

**CodeLens AI** is a desktop-grade AI Code Intelligence workspace powered by **Google Gemini 3.6 Flash**.

---

## 🚀 Quick Download & Install (Windows)

1. Download **[`CodeLensAI-Setup.exe`](https://github.com/mrfrosty7007/CodeLens-AI/releases/download/v1.0.0/CodeLensAI-Setup.exe)** from this release.
2. Run the installer and click **Install**.
3. Launch **CodeLens AI** from your Start Menu, Desktop, or the installer finish screen.
4. Configure your Gemini API key in `.env` (`GEMINI_API_KEY=your_key`) or via the in-app setup screen.
5. CodeLens AI opens automatically in your browser.

---

## ✨ Key Highlights in v1.0

### 🤖 Google Gemini 3.6 Flash Engine
- **Powered by Gemini 3.6 Flash**: Fast, high-accuracy cloud intelligence using the official Google GenAI SDK (`google-genai`).
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

| File | Platform | Size | SHA-256 Checksum | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`CodeLensAI-Setup.exe`** | Windows x64 | ~97 MB | `f25c21e83dcb4dd2bf820c3032778d415ea2462917de16783d67730c74e4d4bb` | Standalone Windows 1-Click Installer |
| **`CodeLensAI-1.0.0-x86_64.AppImage`** | Linux x86_64 | ~149 MB | `10a49cea807093e448a33b81bbec4a72fc26837ab8979c68ef0275aeb62535e4` | Standalone Portable Linux AppImage |
| `Source code (zip)` | Any | — | — | Source code archive |
| `Source code (tar.gz)` | Any | — | — | Source code tarball |

### Linux Quick Start
```bash
chmod +x CodeLensAI-1.0.0-x86_64.AppImage
./CodeLensAI-1.0.0-x86_64.AppImage
```
