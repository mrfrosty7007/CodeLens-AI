"""Environment setup and configuration manager for CodeLens AI.

Provides API key configuration detection and environment management for Gemini AI.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

import gemini_client

ENV_PATH = Path(__file__).resolve().parent / ".env"
REQUIRED_MODEL = "gemini-3.6-flash"


def is_api_key_configured() -> bool:
    """Check whether a valid Gemini API key is configured."""
    return gemini_client.is_configured()


def save_api_key(api_key: str) -> tuple[bool, str]:
    """Save or update GEMINI_API_KEY in the .env file.

    Args:
        api_key: The Gemini API key string to store.

    Returns:
        tuple[success, message]
    """
    clean_key = api_key.strip()
    if not clean_key:
        return False, "API key cannot be empty."

    try:
        lines: list[str] = []
        found = False

        if ENV_PATH.is_file():
            existing_content = ENV_PATH.read_text(encoding="utf-8")
            for line in existing_content.splitlines():
                if line.strip().startswith("GEMINI_API_KEY="):
                    lines.append(f"GEMINI_API_KEY={clean_key}")
                    found = True
                else:
                    lines.append(line)

        if not found:
            lines.append(f"GEMINI_API_KEY={clean_key}")

        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.environ["GEMINI_API_KEY"] = clean_key
        load_dotenv(dotenv_path=ENV_PATH, override=True)
        return True, "Gemini API key saved successfully to .env."
    except Exception as exc:
        return False, f"Failed to save .env file: {exc}"


def get_system_status() -> dict:
    """Check full environment readiness for CodeLens AI."""
    api_ready = is_api_key_configured()

    return {
        "app_installed": True,
        "api_key_configured": api_ready,
        "ready": api_ready,
        "model_name": REQUIRED_MODEL,
    }
