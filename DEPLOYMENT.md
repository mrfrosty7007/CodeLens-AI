# Deploying CodeLens AI to Streamlit Community Cloud 🚀

This guide provides step-by-step instructions for deploying **CodeLens AI** to **Streamlit Community Cloud** with zero friction.

---

## 📋 Prerequisites

1. A [GitHub](https://github.com/) account.
2. A free Google Gemini API key from [Google AI Studio](https://aistudio.google.com/).
3. A [Streamlit Community Cloud](https://share.streamlit.io/) account (linked with your GitHub).

---

## 🚀 Step-by-Step Deployment Guide

### 1. Push or Fork the Repository

Ensure your repository contains the latest CodeLens AI code with `app.py`, `requirements.txt`, and `gemini_client.py`.

```bash
git clone https://github.com/mrfrosty7007/CodeLens-AI.git
```

### 2. Create a New App on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io/) and log in.
2. Click the **"Create app"** or **"New app"** button.
3. Choose **"I already have an app"** (or select your repository directly).
4. Configure your repository details:
   - **Repository:** `your-username/CodeLens-AI` (or `mrfrosty7007/CodeLens-AI`)
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** (Choose your custom subdomain or keep the default)

---

### 3. Configure Gemini API Key Secrets

Before deploying, configure your Gemini API Key in Streamlit Cloud Secrets so the app can authenticate securely without exposing your credentials:

1. In the deployment modal, expand **"Advanced settings..."**.
2. Under the **Secrets** (TOML format) section, add:

```toml
GEMINI_API_KEY = "AIzaSyYourActualGeminiAPIKeyHere"
```

> [!TIP]
> If your app is already deployed, you can add or update secrets at any time by opening your app dashboard -> **Settings** (⚙️) -> **Secrets**.

---

### 4. Deploy!

1. Click **"Deploy!"**.
2. Streamlit Cloud will install dependencies from `requirements.txt` (`streamlit`, `google-genai`, `python-dotenv`, `Pygments`).
3. Within 1–2 minutes, your live CodeLens AI workspace will be active and ready to share!

---

## ⚙️ Environment Configuration Precedence

CodeLens AI retrieves the Gemini API key in the following priority order:

1. **Streamlit Secrets (`st.secrets["GEMINI_API_KEY"]`)**: Automatically utilized in Streamlit Community Cloud.
2. **Local Environment / `.env` (`GEMINI_API_KEY`)**: Utilized during local development (`.env`).
3. **In-App Setup Modal (⚙️)**: Allows interactive key entry and verification during live sessions.

---

## 🔍 Verifying the Deployment

Once deployed:
1. Open the public Streamlit app URL.
2. Verify that the header displays **"Powered by Gemini 3.6 Flash"** with a green **Online** status indicator.
3. Test **Explain**, **Improve**, and **Optimize** on sample snippets.
4. Test the **▶ Run** button to execute Python code in the sandbox.

---

## 🛠️ Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **"GEMINI_API_KEY is not configured"** | Ensure `GEMINI_API_KEY = "..."` is added under App Settings -> Secrets in Streamlit Cloud. |
| **"Invalid Gemini API key"** | Verify that your key is copied correctly without trailing spaces from [Google AI Studio](https://aistudio.google.com/). |
| **Quota / Rate Limits** | Ensure your Google AI Studio project has active quota for `gemini-3.6-flash`. |
