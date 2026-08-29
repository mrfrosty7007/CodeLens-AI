# CodeLens AI 🧠

An AI-powered **Code Explainer** built with **Streamlit** and **Gemini 2.5 Flash** for the Alexa Developers SRM technical task. Paste Python, C++, Java, or JavaScript code to get beginner-friendly explanations, cleaner refactorings, and performance-focused optimizations in a single click.

Designed with a sleek, modern dark UI inspired by developer tools like Cursor and GitHub Copilot.

---

## ⚡ Quick Start

```bash
# Clone the repository
git clone https://github.com/mrfrosty7007/CodeLens-AI.git
cd CodeLens-AI

# Create virtual environment
python -m venv .venv
```

### Windows (PowerShell)
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### macOS / Linux
```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

---

## 🔑 `.env` Setup

1. Copy `.env.example` to create your local `.env` file:
   ```bash
   # Windows
   copy .env.example .env

   # macOS / Linux
   cp .env.example .env
   ```

2. Open `.env` and insert your Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey):
   ```env
   GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
   ```

> **Note:** Never commit the `.env` file. It is listed in `.gitignore` to prevent leaking API keys.

---

## 🚀 Running the App

With your virtual environment activated:

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
- **Export Capabilities:** Export generated Markdown explanations directly from the UI.
- **Robust Error Handling:** Clear alerts for missing API keys, rate limits, empty inputs, or network timeouts without application crashes.

---

## 🛠️ Tech Stack

- **Frontend / UI:** [Streamlit](https://streamlit.io/)
- **LLM Engine:** [Gemini 2.5 Flash](https://deepmind.google/technologies/gemini/) via the official [`google-genai`](https://googleapis.github.io/python-genai/) SDK
- **Configuration:** [`python-dotenv`](https://pypi.org/project/python-dotenv/)
- **Syntax Highlighting:** [`Pygments`](https://pygments.org/)

---

## 📁 Repository Structure

```text
CodeLens-AI/
├── app.py              # Main Streamlit web application & UI
├── gemini_client.py    # Google GenAI API client & error handling
├── prompts.py          # Structured prompt engineering & templates
├── styles.css          # Dark glassmorphism stylesheet
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
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