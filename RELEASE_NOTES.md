# CodeLens AI — Release v1.0.0 (Phase H3)

**CodeLens AI** is an offline, private, desktop-grade AI Code Intelligence workspace powered locally by **Ollama** running **Qwen2.5-Coder 3B**.

---

## 🚀 Quick Download & Install (Windows)

1. Download **[`CodeLensAI-Setup.exe`](https://github.com/mrfrosty7007/CodeLens-AI/releases/download/v1.0.0/CodeLensAI-Setup.exe)** from this release.
2. Run the installer and click **Install**.
3. Launch **CodeLens AI** from your Start Menu, Desktop, or the installer finish screen.
4. Complete the guided one-time setup:
   - **Ollama Detection**: Verifies or installs Ollama automatically via Windows Package Manager.
   - **Local Inference Engine**: Automatically boots `ollama serve` in the background.
   - **AI Model Download**: Downloads `qwen2.5-coder:3b` (~1.9 GB) directly to local storage.
5. CodeLens AI opens automatically in your browser—**100% private, local, and offline**.

> **Note:** The model download (~1.9 GB) is a **one-time setup**. Afterward, CodeLens AI operates completely offline with zero internet access required.

---

## ✨ What's New in v1.0.0

### 🖥️ Native Desktop Experience (Phase H3)
- **1-Click Windows Setup (`CodeLensAI-Setup.exe`)**: Commercial-grade NSIS installer with Desktop and Start Menu shortcuts, automatic background service checks, and clean uninstaller support.
- **Headless Native Launcher (`CodeLensAI.exe`)**: Starts the local server silently in the background with zero visible CMD/terminal windows and opens your default browser automatically.
- **Zero-Friction First Launch Wizard**: Interactive setup dashboard with real-time model download progress, byte counters, and automated service startup.
- **Actionable Recovery**: Self-healing dependency manager with retry mechanics and fallback installer hooks.

### 🎨 Project Helix IDE Workspace (Phases H1 & H2)
- **Cursor & VS Code Aesthetic**: Matte graphite theme, thin cyan borders, status beacons, and active language tags.
- **High-Density Split Workspace**: 20% VS Code Explorer tree with persistent folder expansion + 80% dominant code editor with live line-number gutter.
- **Integrated Terminal & Output Dock**: Execution terminal with real-time exit codes, millisecond execution timings, and instant Markdown export.
- **Synchronized State Engine**: Instant reactive switching across **Python**, **C++**, **Java**, and **JavaScript** with zero desynchronization.

---

## 🔒 100% Offline & Private AI

- **Zero Cloud API Calls**: No data is sent to external servers or third-party APIs.
- **Zero Telemetry / Zero Tracking**: Prompts, code snippets, and analysis results never leave your machine.
- **Local Sandbox Execution**: Isolated execution sandbox with strict 5-second process timeouts and automated cleanup.

---

## 📦 Release Artifacts

| File | Type | Description |
| :--- | :--- | :--- |
| `CodeLensAI-Setup.exe` | Windows Installer | Native setup wizard (Desktop + Start Menu shortcuts) |
| `Source code (zip)` | Source Archive | Full source code for manual or cross-platform deployment |
| `Source code (tar.gz)` | Source Archive | Unix tarball |
