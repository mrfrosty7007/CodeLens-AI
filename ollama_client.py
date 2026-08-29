"""Ollama client backend for CodeLens AI."""

from __future__ import annotations

import httpx

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:7b"
TIMEOUT_SECONDS = 120.0


class OllamaClientError(Exception):
    """User-facing error raised by the Ollama helper."""


def is_running() -> bool:
    """Check whether the local Ollama server is running and reachable."""
    try:
        response = httpx.get(OLLAMA_BASE_URL, timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


def generate(prompt: str) -> str:
    """Send a prompt to the local Ollama server and return the generated text.

    Args:
        prompt: The prompt text to send to Ollama.

    Returns:
        The generated response string from the Ollama model.

    Raises:
        OllamaClientError: If Ollama is unreachable, times out, returns an HTTP
            error status, or produces an empty response.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = httpx.post(
            OLLAMA_GENERATE_URL,
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException as exc:
        raise OllamaClientError(
            f"The request to Ollama timed out after {int(TIMEOUT_SECONDS)} seconds."
        ) from exc
    except (httpx.ConnectError, httpx.NetworkError) as exc:
        raise OllamaClientError(
            "Could not reach the local Ollama server at http://localhost:11434. "
            "Make sure Ollama is running (`ollama serve`)."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise OllamaClientError(
            f"Ollama returned HTTP error {exc.response.status_code}: {exc.response.text}"
        ) from exc
    except Exception as exc:
        raise OllamaClientError(
            f"Unexpected error while communicating with Ollama: {exc}"
        ) from exc

    text = data.get("response", "")
    if not text:
        raise OllamaClientError("Ollama returned an empty response.")
    return text
