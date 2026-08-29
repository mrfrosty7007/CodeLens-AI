# CodeLens AI 🧠

An AI-powered **Code Explainer** built with **Streamlit** and local **Qwen2.5-Coder 7B** via **Ollama** for the Alexa Developers SRM technical task. Paste Python, C++, Java, or JavaScript code to get beginner-friendly explanations, cleaner refactorings, and performance-focused optimizations in a single click.

Designed with a sleek, modern dark UI inspired by developer tools like Cursor and GitHub Copilot.

---

## ⚡ Quick Start

### 1. Prerequisites (Ollama)
Make sure [Ollama](https://ollama.com/) is installed and running with `qwen2.5-coder:7b`:
```bash
# Pull and test the model
ollama run qwen2.5-coder:7b
```

### 2. Setup Project
```bash
# Clone the repository
git clone https://github.com/mrfrosty7007/CodeLens-AI.git
cd CodeLens-AI

# Create virtual environment
python -m venv .venv
```

#### Windows (PowerShell)
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### macOS / Linux
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 🚀 Running the App

With your virtual environment activated and Ollama running:

```bash
streamlit run app.py
```

Then open your browser at `http://localhost:8501`.

---

## ✨ Features

- **Explain Mode:** Breaks down what the code does, how it works step-by-step, time/space complexity analysis, and a breakdown of key functions and variables.
- **Improve Mode:** Refactors the code for readability, clean naming conventions, and best practices with a concise change summary.
- **Optimize Mode:** Re-architects the snippet for performance and reduced resource usage with complexity trade-off details.
- **Multi-Language Support:** Seamlessly switches between **Python**, **C++**, **Java**, and **JavaScript** with pre-loaded algorithm samples.
- **Local AI Inference:** 100% private, offline-capable code analysis powered by local Ollama (`qwen2.5-coder:7b`) with zero external API dependencies or rate limits.
- **Export Capabilities:** Export generated Markdown explanations directly from the UI.
- **Robust Error Handling:** Automatic Ollama availability checks and clear health notifications without application crashes.

---

## 🛠️ Tech Stack

- **Frontend / UI:** [Streamlit](https://streamlit.io/)
- **LLM Engine:** [Qwen2.5-Coder 7B](https://ollama.com/library/qwen2.5-coder:7b) via local [Ollama](https://ollama.com/) API
- **HTTP Client:** [`httpx`](https://www.python-httpx.org/)
- **Syntax Highlighting:** [`Pygments`](https://pygments.org/)

---

## 📁 Repository Structure

```text
CodeLens-AI/
├── app.py              # Main Streamlit web application & UI
├── ollama_client.py    # Ollama API client & health check
├── prompts.py          # Structured prompt engineering & templates
├── styles.css          # Dark glassmorphism stylesheet
├── requirements.txt    # Python dependencies
├── .gitignore          # Git exclusion rules
├── README.md           # Project documentation
└── assets/             # Screenshots and visual assets
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

- Real-time token streaming for faster response rendering
- Code file upload support (`.py`, `.cpp`, `.java`, `.js`)
- Interactive side-by-side diff viewer for original vs. improved/optimized code
- Multi-turn conversation history for iterative questions
- PDF export for structured study notes

---

## 📄 License

This project is licensed under the MIT License.