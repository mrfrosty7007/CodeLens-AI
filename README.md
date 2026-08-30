# CodeLens AI

> AI-powered code explanation, optimization, and sandboxed execution — directly in your browser.

[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit_Cloud-FF4B4B?logo=streamlit&logoColor=white)](https://codelens-ai-uqyhaddbzbnjmzzxm8izhr.streamlit.app)
[![Python: 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit: 1.40+](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Model: Gemini 3.6 Flash](https://img.shields.io/badge/Model-Gemini_3.6_Flash-8A2BE2?logo=google&logoColor=white)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🌐 Live Demo

Experience CodeLens AI instantly without installing any dependencies or setting up local environments:

> **Open CodeLens AI:** **[https://codelens-ai-uqyhaddbzbnjmzzxm8izhr.streamlit.app](https://codelens-ai-uqyhaddbzbnjmzzxm8izhr.streamlit.app)**

---

## 🏆 ADS Judge Experience

Judges can evaluate CodeLens AI in seconds directly in the browser:

* **Open the Live App:** Navigate to **[https://codelens-ai-uqyhaddbzbnjmzzxm8izhr.streamlit.app](https://codelens-ai-uqyhaddbzbnjmzzxm8izhr.streamlit.app)**.
* **Paste code:** Select your language (**Python**, **JavaScript**, **C++**, or **Java**) and paste any snippet.
* **Click action:** Click **Explain**, **Improve**, **Optimize**, or **▶ Run**.
* **No installation.**
* **No Git.**
* **No Python.**
* **No API key required** *(pre-configured securely via Streamlit Community Cloud Secrets)*.

---

## 🎬 Demo

![CodeLens AI Interactive Demo](assets/demo.gif)
*(Interactive workspace demo preview — `assets/demo.gif`)*

---

## 💡 Why CodeLens AI

Modern developers regularly work with unfamiliar codebases, legacy algorithms, and multi-language repositories. Switching between separate documentation tabs, AI chat windows, refactoring assistants, and local terminal sandboxes creates friction and breaks flow.

**CodeLens AI** unifies the entire workflow into a single, high-density browser workspace. Developers can **paste unfamiliar code**, **understand its structure and complexity**, **optimize its performance**, and **execute it in a secure sandbox** — all without leaving their browser.

---

## ✨ Features

- 🧠 **Explain Code:** Generates beginner-friendly step-by-step breakdowns, algorithm logic explanations, time & space complexity ($O(N)$ analysis), and key variable/function roles.
- ✨ **Improve Code:** Refactors code for enhanced readability, clean naming conventions, modern idiomatic standards, and maintainability with change summaries.
- ⚡ **Optimize Code:** Re-architects code for optimal execution speed and minimal memory footprint, with automated code editor insertion and instant one-click Undo.
- ▶️ **Sandboxed Execution:** Safely executes code with real-time stdout/stderr capture, millisecond runtime metrics, and 5-second process isolation.
- 🌐 **Multi-Language Runtimes:** Full support for **Python**, **JavaScript**, **C++**, and **Java**.
- 🎨 **VS Code-Inspired Interface:** Project Helix high-density matte-graphite theme with explorer file tree, line gutter, and synchronized status dock.
- 🤖 **Powered by Gemini Cloud AI:** Low-latency cloud intelligence using Google Gemini 3.6 Flash via the official `google-genai` SDK.
- 📥 **One-Click Markdown Export:** Download comprehensive AI reports and documentation as formatted `.md` files.

---

## 🏗️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          Judge / Developer Browser                     │
│                                                                        │
│  ┌──────────────────────┐    HTTPS API    ┌─────────────────────────┐  │
│  │   CodeLens AI Web    │ ──────────────► │    Google Gemini API    │  │
│  │   (Streamlit Cloud)  │ ◄────────────── │ (gemini-3.6-flash Cloud)│  │
│  └──────────┬───────────┘                 └─────────────────────────┘  │
│             │                                                          │
│             ▼                                                          │
│   Sandboxed Runner Host                                                │
│   (Python / Node.js / GCC / JDK)                                       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📸 Screenshots

| Workspace | AI Explanation |
| :---: | :---: |
| ![Workspace](assets/screenshots/workspace.png)<br>*Project Helix IDE Workspace* | ![AI Explanation](assets/screenshots/explain.png)<br>*Structured AI Code Breakdown* |

| Optimization & Instant Undo | Code Execution Sandbox |
| :---: | :---: |
| ![Optimization](assets/screenshots/optimize.png)<br>*Algorithmic Optimization & Auto-Replace* | ![Code Execution](assets/screenshots/execute.png)<br>*Sandboxed Multi-Language Execution* |

---

## 🚀 Quick Start (Web)

The fastest and recommended way to use CodeLens AI is directly on the web:

1. **Open the Live Demo:** Navigate to **[https://codelens-ai-uqyhaddbzbnjmzzxm8izhr.streamlit.app](https://codelens-ai-uqyhaddbzbnjmzzxm8izhr.streamlit.app)**.
2. **Select Language & Paste Code:** Choose Python, JavaScript, C++, or Java and enter your snippet (or use the pre-loaded starter examples).
3. **Analyze or Run:** Click **Explain**, **Improve**, **Optimize**, or **▶ Run** to inspect results instantly in the output dock.

---

## 💻 Local Development

Contributors and developers can run CodeLens AI locally with Python 3.11+:

### 1. Clone & Setup Environment

```powershell
git clone https://github.com/mrfrosty7007/CodeLens-AI.git
cd CodeLens-AI

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

### 2. Configure Local API Key

For local development, add your Google Gemini API key to `.env`:

```env
GEMINI_API_KEY=your_api_key_here
```

> [!NOTE]
> The `GEMINI_API_KEY` is only required for local development and self-hosted instances. Get a free API key from [Google AI Studio](https://aistudio.google.com/).

---

## ☁️ Deployment

CodeLens AI is optimized for 1-click deployment to **Streamlit Community Cloud**:

1. Fork or push this repository to GitHub.
2. Create a new app on [share.streamlit.io](https://share.streamlit.io/) pointing to `app.py`.
3. In **Advanced Settings** -> **Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your_gemini_api_key_here"
   ```
4. Click **Deploy!**

For detailed deployment instructions and secrets configuration, see [`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## 🛠️ Tech Stack

- **Frontend & UI:** [Streamlit](https://streamlit.io/) with custom Project Helix matte-graphite CSS
- **AI Backend:** [Google Gemini API](https://ai.google.dev/) (`gemini-3.6-flash`) via the official [`google-genai`](https://pypi.org/project/google-genai/) SDK
- **Core Runtime:** Python 3.11+ / 3.12+
- **Syntax & Output:** [`Pygments`](https://pygments.org/) & Markdown rendering
- **Sandbox Execution:** Subprocess engine with temporary filesystem isolation and timeout guards
- **Configuration & Secrets:** `st.secrets` (Cloud) & [`python-dotenv`](https://pypi.org/project/python-dotenv/) (Local)

---

## 📁 Project Structure

```text
CodeLens-AI/
├── app.py                  # Main Streamlit web application & IDE interface
├── gemini_client.py        # Google Gemini GenAI SDK backend client
├── setup_manager.py        # Environment setup & configuration manager
├── runtime_manager.py      # Multi-language runtime detection & installers
├── code_runner.py          # Multi-language code execution engine & sandbox
├── prompts.py              # Structured prompt templates
├── styles.css              # Project Helix dark matte-graphite styling
├── .env.example            # Environment variables template
├── DEPLOYMENT.md           # Streamlit Community Cloud deployment guide
├── requirements.txt        # Runtime Python dependencies
├── assets/                 # Application branding & media assets
│   ├── demo.gif            # Interactive demo asset
│   ├── icon.png            # App logo
│   ├── icon.ico            # App icon
│   └── screenshots/        # UI screenshot gallery
│       ├── workspace.png
│       ├── explain.png
│       ├── optimize.png
│       └── execute.png
└── README.md               # Project documentation
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
