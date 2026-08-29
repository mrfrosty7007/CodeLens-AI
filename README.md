# CodeLens AI 🧠

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_Inference-000000?logo=ollama&logoColor=white)](https://ollama.com/)
[![Model: Qwen2.5-Coder 7B](https://img.shields.io/badge/Model-Qwen2.5--Coder_7B-8A2BE2)](https://ollama.com/library/qwen2.5-coder:7b)
[![Offline AI](https://img.shields.io/badge/Offline_AI-100%25_Private-success)](https://github.com/mrfrosty7007/CodeLens-AI)

**CodeLens AI** is an offline, private, AI-powered code assistant built with **Streamlit** and powered locally by **Ollama** running **Qwen2.5-Coder 7B**. It empowers developers to understand, refactor, optimize, and safely execute code across **Python**, **C++**, **Java**, and **JavaScript**—all without sending a single line of code to external cloud APIs.

Designed with a sleek, modern dark glassmorphism interface inspired by developer environments like Cursor and GitHub Copilot.

---

## 📑 Table of Contents

- [CodeLens AI 🧠](#codelens-ai-)
  - [📑 Table of Contents](#-table-of-contents)
  - [✨ Features](#-features)
  - [🛠️ Tech Stack](#️-tech-stack)
  - [⚙️ Runtime Support](#️-runtime-support)
  - [⚡ Quick Start](#-quick-start)
    - [1. Prerequisites (Ollama)](#1-prerequisites-ollama)
    - [2. Clone the Repository](#2-clone-the-repository)
    - [3. Setup Virtual Environment & Install Dependencies](#3-setup-virtual-environment--install-dependencies)
      - [Windows (PowerShell)](#windows-powershell)
      - [macOS / Linux](#macos--linux)
    - [4. Launch the Application](#4-launch-the-application)
  - [📁 Repository Structure](#-repository-structure)
  - [📸 Screenshots](#-screenshots)
  - [🔮 Future Enhancements](#-future-enhancements)
  - [📄 License](#-license)

---

## ✨ Features

- **🧠 Explain Mode:** Generates beginner-friendly step-by-step breakdowns, algorithm logic explanations, time & space complexity ($O(N)$ analysis), and key variable/function roles.
- **✨ Improve Mode:** Refactors code for enhanced readability, clean naming conventions, modern idiomatic standards, and maintainability with a concise change summary.
- **⚡ Optimize Mode:** Re-architects code for optimal execution speed and minimal memory footprint, including big-O efficiency comparisons.
- **🔄 Automatic Optimize → Replace Editor:** Automatically updates the code editor with the optimized code upon generation for seamless iteration.
- **↩️ Undo Optimize:** Instant one-click rollback mechanism allowing you to revert back to your original code snippet anytime.
- **▶️ Live Code Execution:** Safely execute Python, C++, Java, and JavaScript directly from the UI with real-time stdout, stderr, and execution duration metrics.
- **🛡️ Sandboxed Execution:** Runs code within isolated temporary workspaces with a strict 5-second timeout and automated cleanup.
- **🔍 Runtime Detection:** Automatically inspects host environment toolchains (Node.js, g++, JDK) and provides helpful, non-blocking guidance if a compiler or interpreter is missing.
- **🔒 100% Offline & Private AI:** Local inference via Ollama ensures zero cloud dependencies, zero data tracking, zero API costs, and zero rate limits.
- **📥 Markdown Export:** Download complete AI-generated reports and documentation as structured `.md` files in a single click.

---

## 🛠️ Tech Stack

- **Frontend & UI:** [Streamlit](https://streamlit.io/) with custom dark glassmorphic CSS
- **LLM Engine:** [Qwen2.5-Coder 7B](https://ollama.com/library/qwen2.5-coder:7b) via local [Ollama](https://ollama.com/) REST API
- **HTTP Client:** [`httpx`](https://www.python-httpx.org/) for fast, robust communication with Ollama
- **Execution Sandbox:** Python `subprocess` engine with tempfile isolation, process timeouts, and runtime detection
- **Syntax Highlighting:** [`Pygments`](https://pygments.org/)

---

## ⚙️ Runtime Support

CodeLens AI executes supported languages locally on your machine. The execution engine detects installed toolchains and reports clear status banners in the UI.

| Language | Execution Engine | Runtime Dependency |
| :--- | :--- | :--- |
| **Python** | Virtual Environment | Bundled Python interpreter (`sys.executable`) |
| **JavaScript** | V8 Engine | [Node.js](https://nodejs.org/) (`node` on system `PATH`) |
| **C++** | Native Binary (g++) | GCC / Clang (`g++` or `clang++` on system `PATH`) |
| **Java** | JVM / Bytecode (javac) | OpenJDK / Oracle JDK (`javac` & `java` on system `PATH`) |

> [!NOTE]
> If a runtime for a specific language (e.g., `g++` or `node`) is not installed, code analysis (Explain, Improve, Optimize) will still work completely. The app will gracefully inform you only when attempting to run code for that specific language.

---

## ⚡ Quick Start

### 1. Prerequisites (Ollama)

1. Download and install **[Ollama](https://ollama.com/)**.
2. Pull the **Qwen2.5-Coder 7B** model:
   ```bash
   ollama pull qwen2.5-coder:7b
   ```
3. Ensure the Ollama service is running:
   ```bash
   ollama serve
   ```

### 2. Clone the Repository

```bash
git clone https://github.com/mrfrosty7007/CodeLens-AI.git
cd CodeLens-AI
```

### 3. Setup Virtual Environment & Install Dependencies

#### Windows (PowerShell)

```powershell
# Create virtual environment
python -m venv .venv

# Install dependencies using the venv executable directly
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

#### macOS / Linux

```bash
# Create virtual environment
python3 -m venv .venv

# Activate and install dependencies
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Launch the Application

#### Windows (PowerShell)

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

#### macOS / Linux

```bash
streamlit run app.py
```

Once launched, open your browser and navigate to:
```
http://localhost:8501
```

---

## 📁 Repository Structure

```text
CodeLens-AI/
├── app.py              # Main Streamlit web application & user interface
├── code_runner.py      # Multi-language code execution engine & sandbox
├── ollama_client.py    # Ollama REST API client & health check
├── prompts.py          # Structured prompt engineering & system instructions
├── styles.css          # Dark glassmorphic design system
├── requirements.txt    # Project dependencies
├── README.md           # Documentation & setup guide
├── .gitignore          # Git exclusion rules
└── assets/             # Screenshots and visual documentation
    └── .gitkeep
```

---

## 📸 Screenshots

Add your app screenshots to the `assets/` directory:

| Hero & Code Input | Explain Result |
| :---: | :---: |
| ![Hero & Editor](assets/screenshot-hero.png) | ![Explain Output](assets/screenshot-explain.png) |

| Improve Mode | Optimize Mode |
| :---: | :---: |
| ![Improve Output](assets/screenshot-improve.png) | ![Optimize Output](assets/screenshot-optimize.png) |

---

## 🔮 Future Enhancements

- **Project Helix UI Redesign:** Comprehensive interface modernization and high-density developer layout.
- **Automatic Language Detection:** Real-time source code classification without manual dropdown selection.
- **Side-by-Side Diff Viewer:** Visual side-by-side comparison between original and AI-modified code.
- **File Upload Support:** Direct multi-file upload for `.py`, `.cpp`, `.java`, and `.js` source files.
- **Streaming AI Responses:** Real-time token streaming for instantaneous response display.
- **Session History:** Searchable local history of past prompts, analyses, and benchmarks.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.