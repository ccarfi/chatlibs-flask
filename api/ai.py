"""Provider-agnostic AI layer.

Text and image generation are each dispatched to a pluggable backend selected by
environment variable, so swapping models or vendors later is a config change, not
a rewrite. Today: Anthropic Claude for text, Google Imagen 4 for images.

Env vars:
    TEXT_PROVIDER   default "anthropic"
    TEXT_MODEL      default "claude-sonnet-4-6" (drop to "claude-haiku-4-5" to
                    cut cost further, or "claude-opus-4-8" for max quality)
    ANTHROPIC_API_KEY   required for the anthropic provider

    IMAGE_PROVIDER  default "google"
    IMAGE_MODEL     default "imagen-4.0-generate-001"
    GOOGLE_API_KEY  (or GEMINI_API_KEY) required for the google provider
"""

import os

TEXT_PROVIDER = os.getenv("TEXT_PROVIDER", "anthropic")
TEXT_MODEL = os.getenv("TEXT_MODEL", "claude-sonnet-4-6")

IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "google")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "imagen-4.0-generate-001")


class AIError(Exception):
    """Raised for any provider failure; routes turn this into a clean 502."""


# --- Text -------------------------------------------------------------------

def generate_text(prompt, system="You are a helpful assistant.", max_tokens=1024):
    """Generate text from the configured text provider."""
    if TEXT_PROVIDER == "anthropic":
        return _anthropic_text(prompt, system, max_tokens)
    raise AIError(f"Unknown TEXT_PROVIDER: {TEXT_PROVIDER!r}")


def _anthropic_text(prompt, system, max_tokens):
    import anthropic

    try:
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the env
        # Thinking is left off: these are short, creative completions where
        # latency matters more than deep reasoning. Flip on adaptive thinking
        # here if you ever move to a harder text task.
        resp = client.messages.create(
            model=TEXT_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        raise AIError(f"Claude request failed: {e}") from e

    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if not text:
        raise AIError("Claude returned an empty response.")
    return text


# --- Image ------------------------------------------------------------------

def generate_image(prompt):
    """Generate an image and return it as raw JPEG bytes.

    The caller decides how to deliver it (upload to Blob for a durable URL, or
    inline as a data URI)."""
    if IMAGE_PROVIDER == "google":
        return _google_image(prompt)
    raise AIError(f"Unknown IMAGE_PROVIDER: {IMAGE_PROVIDER!r}")


def _google_image(prompt):
    from google import genai
    from google.genai import types

    # Note: negative_prompt is NOT supported on the Gemini Developer API
    # (API-key mode) — it's Vertex/Enterprise-only and 400s here. Text is kept
    # out of images via the sanitized scene description built in the route.
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_images(
            model=IMAGE_MODEL,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
            ),
        )
    except Exception as e:  # google-genai raises a variety of error types
        raise AIError(f"Imagen request failed: {e}") from e

    images = getattr(resp, "generated_images", None) or []
    if not images:
        # Most commonly a safety filter blocked the prompt.
        raise AIError("No image was generated (it may have been filtered).")

    return images[0].image.image_bytes
