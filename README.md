# CodeLens AI 🧠

[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit_Cloud-FF4B4B?logo=streamlit&logoColor=white)](https://codelens-ai.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Windows: x64 Installer](https://img.shields.io/badge/Windows-CodeLensAI--Setup.exe-0078D6?logo=windows&logoColor=white)](https://github.com/mrfrosty7007/CodeLens-AI/releases)
[![Linux: x86_64 AppImage](https://img.shields.io/badge/Linux-CodeLensAI--1.0.0--x86__64.AppImage-FCC624?logo=linux&logoColor=black)](https://github.com/mrfrosty7007/CodeLens-AI/releases)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Model: Gemini 3.6 Flash](https://img.shields.io/badge/Model-Gemini_3.6_Flash-8A2BE2?logo=google&logoColor=white)](https://ai.google.dev/)
[![Cloud AI](https://img.shields.io/badge/Cloud_AI-Google_GenAI-success)](https://github.com/mrfrosty7007/CodeLens-AI)

**CodeLens AI** is an AI code intelligence workspace built with **Streamlit** and powered by **Google Gemini 3.6 Flash** (`google-genai`). It empowers developers to understand, refactor, optimize, and safely execute code across **Python**, **C++**, **Java**, and **JavaScript**.

Featuring a high-density, matte-graphite developer interface (Project Helix) inspired by Cursor, VS Code, and Linear.

---

## 🌐 Live Demo

Experience CodeLens AI instantly in your browser on Streamlit Community Cloud:

🔗 **[https://codelens-ai.streamlit.app](https://codelens-ai.streamlit.app)**

> [!TIP]
> To deploy your own private instance in 2 minutes, see the [Streamlit Cloud Deployment Guide](DEPLOYMENT.md).

---

## 📑 Table of Contents

- [CodeLens AI 🧠](#codelens-ai-)
  - [🌐 Live Demo](#-live-demo)
  - [📑 Table of Contents](#-table-of-contents)
  - [✨ Features](#-features)
  - [🏗️ System Architecture](#️-system-architecture)
  - [🛠️ Tech Stack](#️-tech-stack)
  - [⚙️ Multi-Language Runtime Sandbox](#️-multi-language-runtime-sandbox)
  - [⚡ Quick Start (Local)](#-quick-start-local)
  - [☁️ Streamlit Cloud Deployment](#️-streamlit-cloud-deployment)
  - [📦 Building the Windows Installer](#-building-the-windows-installer)
  - [📁 Repository Structure](#-repository-structure)
  - [📄 License](#-license)

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

## 🏗️ System Architecture

```text
┌───────────────────────────────────────────────────────────┐
│                      Your Browser / Host                  │
│                                                           │
│  ┌───────────────┐     HTTPS API      ┌────────────────┐  │
│  │  CodeLens AI  │ ─────────────────► │ Google Gemini  │  │
│  │   (Streamlit) │ ◄───────────────── │  (3.6 Flash)   │  │
│  └───────┬───────┘                    └────────────────┘  │
│          │                                                │
│          ▼                                                │
│   Sandboxed Runner                                        │
│   (Py/C++/Java/JS)                                        │
└───────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

- **Frontend & UI:** [Streamlit](https://streamlit.io/) with custom Project Helix matte-graphite CSS
- **AI Backend:** [Google Gemini API](https://ai.google.dev/) (`gemini-3.6-flash`) via the official [`google-genai`](https://pypi.org/project/google-genai/) SDK
- **Environment & Secrets:** [`python-dotenv`](https://pypi.org/project/python-dotenv/) & `st.secrets`
- **Syntax Highlighting:** [`Pygments`](https://pygments.org/)
- **Multi-Language Sandbox:** Python `subprocess` engine with tempfile isolation and runtime toolchain detection
- **Installer & Packaging:** [NSIS](https://nsis.sourceforge.io/) & [PyInstaller](https://pyinstaller.org/)

---

## ⚙️ Multi-Language Runtime Sandbox

CodeLens AI executes supported languages locally or within the hosting container.

| Language | Execution Engine | Runtime Dependency |
| :--- | :--- | :--- |
| **Python** | Virtual Environment / Container | Python interpreter (`sys.executable`) |
| **JavaScript** | V8 Engine | [Node.js](https://nodejs.org/) (`node` on system `PATH`) |
| **C++** | Native Binary (g++) | GCC / Clang (`g++` or `clang++` on system `PATH`) |
| **Java** | JVM / Bytecode (javac) | OpenJDK / Oracle JDK (`javac` & `java` on system `PATH`) |

> [!TIP]
> If a compiler/interpreter for a specific language (e.g. `g++` or `javac`) is not installed in the environment, AI code analysis (Explain, Improve, Optimize) will still work completely. The execution runner will guide you only if you click `▶ Run` for that specific language.

---

## ⚡ Quick Start (Local)

### Prerequisites

- **Python 3.11+**
- **Internet connection required** (for Google Gemini API access)
- **Gemini API key required** (Get a free API key from [Google AI Studio](https://aistudio.google.com/))

### Windows (PowerShell)

```powershell
git clone https://github.com/mrfrosty7007/CodeLens-AI.git
cd CodeLens-AI
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

### Linux / macOS

```bash
git clone https://github.com/mrfrosty7007/CodeLens-AI.git
cd CodeLens-AI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

> [!NOTE]
> Open `.env` and set your `GEMINI_API_KEY`:
> ```env
> GEMINI_API_KEY=AIzaSy...your_actual_key_here
> ```
> You can also enter or update your API key directly inside the CodeLens AI setup interface (⚙️).

---

## ☁️ Streamlit Cloud Deployment

Deploy CodeLens AI to **Streamlit Community Cloud** in 3 steps:

1. Fork or push this repository to your GitHub account.
2. Go to [share.streamlit.io](https://share.streamlit.io/), create a new app pointing to `app.py`.
3. In **Advanced Settings** -> **Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your_actual_key_here"
   ```

For detailed instructions, see the complete [Streamlit Cloud Deployment Guide](DEPLOYMENT.md).

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
├── app.py                  # Main Streamlit web application & IDE interface
├── gemini_client.py        # Google Gemini GenAI SDK backend client
├── setup_manager.py        # Environment setup & configuration manager
├── runtime_manager.py      # Multi-language runtime detection & one-click installers
├── launcher.py             # Native headless Windows launcher
├── code_runner.py          # Multi-language code execution engine & sandbox
├── prompts.py              # Structured prompt templates
├── styles.css              # Project Helix dark matte-graphite styling
├── .env.example            # Environment variables template
├── DEPLOYMENT.md           # Streamlit Community Cloud deployment guide
├── installer.nsi           # NSIS Windows installer definition
├── build_installer.py      # Automated Windows packaging & build script
├── build_linux_appimage.py # Automated Linux AppImage packaging script
├── generate_icons.py       # Multi-resolution icon asset generator
├── requirements.txt        # Python dependencies
├── RELEASE_NOTES.md        # GitHub Release notes & changelog
└── assets/                 # Application icons & branding assets
    ├── icon.png
    └── icon.ico
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.