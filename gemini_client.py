"""Gemini client backend for CodeLens AI."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import errors

# Load .env file from the application directory
_ENV_PATH = Path(__file__).resolve().parent / ".env"
if _ENV_PATH.is_file():
    load_dotenv(dotenv_path=_ENV_PATH, override=True)
else:
    load_dotenv(override=True)

DEFAULT_MODEL = "gemini-3.6-flash"


class GeminiClientError(Exception):
    """User-facing error raised by the Gemini client."""


def get_api_key() -> str | None:
    """Retrieve GEMINI_API_KEY in priority order:
    1. Streamlit Secrets (st.secrets["GEMINI_API_KEY"]) for Streamlit Community Cloud
    2. .env file / os.environ for local development

    Returns:
        The valid API key string, or None if not configured.
    """
    # 1. Streamlit Secrets (Streamlit Community Cloud deployment)
    try:
        import streamlit as st

        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            secret_key = str(st.secrets["GEMINI_API_KEY"]).strip()
            if secret_key and secret_key != "your_api_key_here":
                return secret_key
    except Exception:
        pass

    # 2. Environment variables / .env file (Local development)
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key or key == "your_api_key_here":
        if _ENV_PATH.is_file():
            load_dotenv(dotenv_path=_ENV_PATH, override=True)
            key = os.environ.get("GEMINI_API_KEY", "").strip()

    if key and key != "your_api_key_here":
        return key

    return None


def is_configured() -> bool:
    """Check whether a valid Gemini API key is configured."""
    return get_api_key() is not None


def generate(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Send a prompt to the Gemini API and return the generated text.

    Args:
        prompt: The prompt text to send to Gemini.
        model: Model name to use (default: gemini-3.6-flash).

    Returns:
        The generated response string from Gemini.

    Raises:
        GeminiClientError: If GEMINI_API_KEY is missing, network is unreachable,
            authentication fails, or Gemini returns an error / empty response.
    """
    api_key = get_api_key()
    if not api_key:
        raise GeminiClientError(
            "GEMINI_API_KEY is not configured. Please add your Gemini API key to Streamlit secrets or the .env file."
        )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
    except errors.APIError as exc:
        msg = getattr(exc, "message", str(exc))
        code = getattr(exc, "code", None)
        if code == 400 and "API_KEY_INVALID" in str(msg):
            raise GeminiClientError("Invalid Gemini API key. Please verify your GEMINI_API_KEY in Streamlit secrets or .env.") from exc
        if code == 429 or "RESOURCE_EXHAUSTED" in str(msg):
            raise GeminiClientError("Gemini API quota or rate limit exceeded. Please try again in a moment.") from exc
        raise GeminiClientError(f"Gemini API error ({code or 'API'}): {msg}") from exc
    except (errors.ClientError, errors.ServerError) as exc:
        raise GeminiClientError(f"Gemini service error: {exc}") from exc
    except Exception as exc:
        exc_str = str(exc)
        if any(keyword in exc_str.lower() for keyword in ("connect", "network", "timeout", "dns", "getaddrinfo", "socket")):
            raise GeminiClientError(
                f"Network error: Unable to reach Gemini API. Please check your internet connection: {exc_str}"
            ) from exc
        raise GeminiClientError(f"Unexpected error communicating with Gemini API: {exc_str}") from exc

    text = getattr(response, "text", "") or ""
    if not text.strip():
        raise GeminiClientError("Gemini returned an empty response.")
    return text
