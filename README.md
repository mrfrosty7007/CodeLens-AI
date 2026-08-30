# CodeLens AI 🧠

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Windows: x64 Installer](https://img.shields.io/badge/Windows-CodeLensAI--Setup.exe-0078D6?logo=windows&logoColor=white)](https://github.com/mrfrosty7007/CodeLens-AI/releases)
[![Python: 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_Inference-000000?logo=ollama&logoColor=white)](https://ollama.com/)
[![Model: Qwen2.5-Coder 3B](https://img.shields.io/badge/Model-Qwen2.5--Coder_3B-8A2BE2)](https://ollama.com/library/qwen2.5-coder:3b)
[![Offline AI](https://img.shields.io/badge/Offline_AI-100%25_Private-success)](https://github.com/mrfrosty7007/CodeLens-AI)

**CodeLens AI** is an offline, private, desktop AI code assistant built with **Streamlit** and powered locally by **Ollama** running **Qwen2.5-Coder 3B**. It empowers developers to understand, refactor, optimize, and safely execute code across **Python**, **C++**, **Java**, and **JavaScript**—all without sending a single line of code or prompt to external cloud APIs.

Featuring a high-density, matte-graphite developer interface (Project Helix) inspired by Cursor, VS Code, and Linear.

---

## 📑 Table of Contents

- [CodeLens AI 🧠](#codelens-ai-)
  - [📑 Table of Contents](#-table-of-contents)
  - [🚀 Windows 1-Click Setup (Zero-Friction)](#-windows-1-click-setup-zero-friction)
  - [✨ Features](#-features)
  - [🔒 100% Offline & Private Architecture](#-100-offline--private-architecture)
  - [🛠️ Tech Stack](#️-tech-stack)
  - [⚙️ Multi-Language Runtime Sandbox](#️-multi-language-runtime-sandbox)
  - [⚡ Developer Quick Start (Source Code)](#-developer-quick-start-source-code)
  - [📦 Building the Windows Installer](#-building-the-windows-installer)
  - [📁 Repository Structure](#-repository-structure)
  - [📄 License](#-license)

---

## 🌐 Live Demo

Experience CodeLens AI instantly without installing any dependencies or setting up local environments:

> **Open CodeLens AI:** **[[https://codelens-ai.streamlit.app](https://codelens-ai-uqyhaddbzbnjmzzxm8izhr.streamlit.app)]([https://codelens-ai.streamlit.app](https://codelens-ai-uqyhaddbzbnjmzzxm8izhr.streamlit.app))**

---

## 🚀 Windows 1-Click Setup (Zero-Friction)

No manual terminal commands or manual Python installation required.

1. **Download:** Grab **`CodeLensAI-Setup.exe`** from [GitHub Releases](https://github.com/mrfrosty7007/CodeLens-AI/releases).
2. **Install:** Run the setup wizard to install CodeLens AI with Desktop and Start Menu shortcuts.
3. **Launch:** Open CodeLens AI. The application starts silently in the background with zero visible terminal windows.
4. **Guided One-Time Onboarding:**
   - **Ollama Detection:** Automatically verifies or installs Ollama via Windows Package Manager (`winget`).
   - **Service Initialization:** Automatically boots `ollama serve` in the background.
   - **Model Download:** Downloads `qwen2.5-coder:3b` (~1.9 GB) with real-time percentage and byte progress.
5. **Start Coding:** Transition directly into the IDE workspace. CodeLens AI now operates completely offline.

> [!NOTE]
> The model download (~1.9 GB) is a **one-time setup**. Once downloaded, all code explanations, refactorings, optimizations, and executions work 100% offline with zero internet connectivity.

---

## ✨ Features

- **🧠 Explain Mode:** Generates beginner-friendly step-by-step breakdowns, algorithm logic explanations, time & space complexity ($O(N)$ analysis), and key variable/function roles.
- **✨ Improve Mode:** Refactors code for enhanced readability, clean naming conventions, modern idiomatic standards, and maintainability with a concise change summary.
- **⚡ Optimize Mode:** Re-architects code for optimal execution speed and minimal memory footprint, including big-O efficiency comparisons.
- **🔄 Auto Replace & ↩️ Instant Undo:** Automatically updates the code editor with the AI-optimized code, with an instant one-click rollback button to revert anytime.
- **▶️ Multi-Language Code Runner:** Safely execute Python, C++, Java, and JavaScript directly from the UI with real-time stdout, stderr, exit codes, and execution duration.
- **🛡️ Sandboxed Process Isolation:** Runs code within isolated temporary workspaces with a strict 5-second timeout and automated cleanup.
- **📂 VS Code Explorer Tree:** Persistent folder expansion with active file tracking and glowing status indicators.
- **📥 One-Click Markdown Export:** Download full AI reports, complexity analyses, and documentation as formatted `.md` files.

---

## 🔒 100% Offline & Private Architecture

```text
┌───────────────────────────────────────────────────────────┐
│                      Your Computer                        │
│                                                           │
│  ┌───────────────┐     Local REST     ┌────────────────┐  │
│  │  CodeLens AI  │ ◄────────────────► │  Ollama Server │  │
│  │   (Streamlit) │   localhost:11434  │   (Local Daemon)│  │
│  └───────┬───────┘                    └───────┬────────┘  │
│          │                                    │           │
│          ▼                                    ▼           │
│   Sandboxed Runner                    Qwen 2.5 Coder 3B   │
│   (Py/C++/Java/JS)                    (Local GPU / CPU)   │
└───────────────────────────────────────────────────────────┘
                            ▲
                            │  ZERO Data Sent to Cloud
                       [Firewall / Air-Gapped]
```

- **Zero Cloud API Calls:** All inference runs on your local CPU / GPU.
- **Zero Telemetry / Zero Tracking:** Prompts and source files never leave your machine.
- **Air-Gapped Friendly:** After the initial model pull, CodeLens AI operates with no network connection.

---

## 🛠️ Tech Stack

- **Frontend & UI:** [Streamlit](https://streamlit.io/) with custom Project Helix matte-graphite CSS
- **Local Inference Engine:** [Ollama](https://ollama.com/) running [Qwen2.5-Coder 3B](https://ollama.com/library/qwen2.5-coder:3b)
- **HTTP Client:** [`httpx`](https://www.python-httpx.org/) with streaming progress & response parsing
- **Installer & Packaging:** [NSIS](https://nsis.sourceforge.io/) & [PyInstaller](https://pyinstaller.org/)
- **Multi-Language Sandbox:** Python `subprocess` engine with tempfile isolation and runtime toolchain detection

---

## ⚙️ Multi-Language Runtime Sandbox

CodeLens AI executes supported languages locally on your machine.

| Language | Execution Engine | Runtime Dependency |
| :--- | :--- | :--- |
| **Python** | Virtual Environment | Bundled Python interpreter (`sys.executable`) |
| **JavaScript** | V8 Engine | [Node.js](https://nodejs.org/) (`node` on system `PATH`) |
| **C++** | Native Binary (g++) | GCC / Clang (`g++` or `clang++` on system `PATH`) |
| **Java** | JVM / Bytecode (javac) | OpenJDK / Oracle JDK (`javac` & `java` on system `PATH`) |

> [!TIP]
> If a compiler/interpreter for a specific language (e.g. `g++` or `javac`) is not installed, AI code analysis (Explain, Improve, Optimize) will still work completely. The execution runner will guide you only if you click `▶ Run` for that specific language.

---

## ⚡ Developer Quick Start (Source Code)

### 1. Prerequisites (Ollama)

```bash
# Ensure Ollama is running
ollama serve

# Pull the required model
ollama pull qwen2.5-coder:3b
```

### 2. Clone & Install Dependencies

```bash
git clone https://github.com/mrfrosty7007/CodeLens-AI.git
cd CodeLens-AI

# Create virtual environment
python -m venv .venv

# Activate and install dependencies
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# macOS / Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Launch the Application

```bash
# Run via headless launcher (auto-opens browser)
python launcher.py

# Or directly with Streamlit:
streamlit run app.py
```

---

## 📦 Building the Windows Installer

To build `CodeLensAI-Setup.exe` from source:

```powershell
# 1. Install build dependencies
pip install pyinstaller

# 2. Run the automated build pipeline
python build_installer.py
```

The compiled installer will be output to:
```text
dist/CodeLensAI-Setup.exe
```

---

## 📁 Repository Structure

```text
CodeLens-AI/
├── app.py                # Main Streamlit web application & IDE interface
├── setup_manager.py      # Background dependency manager & one-time setup
├── runtime_manager.py    # Multi-language runtime detection & one-click installers
├── launcher.py           # Native headless Windows launcher
├── code_runner.py        # Multi-language code execution engine & sandbox
├── ollama_client.py      # Ollama REST client & inference helper
├── prompts.py            # Structured prompt templates
├── styles.css            # Project Helix dark matte-graphite styling
├── installer.nsi         # NSIS Windows installer definition
├── build_installer.py    # Automated packaging & build script
├── generate_icons.py     # Multi-resolution icon asset generator
├── requirements.txt      # Python dependencies
├── RELEASE_NOTES.md      # GitHub Release notes & changelog
└── assets/               # Application icons & branding assets
    ├── icon.png
    └── icon.ico
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
