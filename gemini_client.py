"""Reusable Gemini client for CodeLens AI."""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"


class GeminiClientError(Exception):
    """User-facing error raised by the Gemini helper."""


def get_api_key() -> str | None:
    """Return the Gemini API key from the environment, if present."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "YOUR_API_KEY":
        return None
    return key


def _build_client() -> genai.Client:
    api_key = get_api_key()
    if not api_key:
        raise GeminiClientError(
            "Gemini API key is missing. Copy `.env.example` to `.env` and "
            "set `GEMINI_API_KEY` to your key from Google AI Studio."
        )
    return genai.Client(api_key=api_key)


def generate_response(prompt: str, *, temperature: float = 0.2) -> str:
    """Send a prompt to Gemini and return the generated text.

    Raises:
        GeminiClientError: For missing keys, rate limits, network issues,
            and other API failures. Never raises raw SDK exceptions.
    """
    try:
        client = _build_client()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=4096,
            ),
        )
    except GeminiClientError:
        raise
    except genai_errors.ClientError as exc:
        if exc.code == 429:
            raise GeminiClientError(
                "Gemini rate limit reached. Wait a moment and try again."
            ) from exc
        if exc.code in (401, 403):
            raise GeminiClientError(
                "Gemini rejected the API key. Check `GEMINI_API_KEY` in `.env`."
            ) from exc
        raise GeminiClientError(
            "Gemini could not process this request. Please try again."
        ) from exc
    except genai_errors.ServerError as exc:
        raise GeminiClientError(
            "Gemini is temporarily unavailable. Please try again shortly."
        ) from exc
    except genai_errors.APIError as exc:
        raise GeminiClientError(
            "Gemini returned an unexpected API error. Please try again."
        ) from exc
    except (httpx.TimeoutException, TimeoutError) as exc:
        raise GeminiClientError(
            "The request to Gemini timed out. Check your connection and retry."
        ) from exc
    except (httpx.ConnectError, httpx.NetworkError, OSError) as exc:
        raise GeminiClientError(
            "Could not reach Gemini. Check your internet connection and retry."
        ) from exc
    except Exception as exc:  # noqa: BLE001 — keep the UI from crashing
        raise GeminiClientError(
            "Something went wrong while contacting Gemini. Please try again."
        ) from exc

    text = (response.text or "").strip()
    if not text:
        raise GeminiClientError(
            "Gemini returned an empty response. Try again with a smaller snippet."
        )
    return text
