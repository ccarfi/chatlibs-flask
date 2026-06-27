"""ChatLibs — Flask backend.

Four stateless AI endpoints plus the two rendered pages. All game state and flow
live in the browser (see static/script.js); the flow itself is data (flow.py),
served to the client at /api/config. Every AI endpoint returns a uniform
envelope and turns provider failures into a clean JSON error.
"""

import os
import sys

# On Vercel the function runs from the project root, so api/ isn't on sys.path
# and the sibling imports below would fail. Add this file's directory explicitly.
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, render_template, request

from ai import AIError, generate_image, generate_text
from flow import FLOW

app = Flask(__name__)


def _ai_route(produce):
    """Run an AI step, always returning JSON so the client never sees a raw 500.

    Provider failures (AIError) and bad input map to clean messages; anything
    unexpected is logged and returned as a generic 502 rather than an HTML page.
    """
    try:
        return jsonify(produce())
    except AIError as e:
        app.logger.warning("AI step failed: %s", e)
        return jsonify({"error": str(e)}), 502
    except (KeyError, TypeError):
        return jsonify({"error": "Malformed request."}), 400
    except Exception:  # noqa: BLE001 — API boundary must always return JSON
        app.logger.exception("Unexpected error in AI step")
        return jsonify({"error": "Something went wrong. Please try again."}), 502


def _strip_heading(text):
    """Drop a leading Markdown heading line (e.g. '# Title') if the model adds
    one. The title is generated separately, so a heading in the body just shows
    up as a stray '# ...' line in the chat (#21)."""
    text = text.lstrip()
    if text.startswith("#"):
        parts = text.split("\n", 1)
        return parts[1].lstrip() if len(parts) > 1 else ""
    return text


# --- Pages ------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/story")
def story():
    # Only honor an image_url with a safe scheme. The app no longer passes one
    # (images are ephemeral), but the param is public, so refuse anything that
    # isn't an https/data URL. Jinja autoescaping covers title/description, and
    # the client URL-encodes them via encodeURIComponent.
    image_url = request.args.get("image_url", "")
    if not (image_url.startswith("https://") or image_url.startswith("data:")):
        image_url = ""
    return render_template(
        "story.html",
        image_url=image_url,
        title=request.args.get("title", "A ChatLibs Story"),
        description=request.args.get("description", ""),
    )


# --- Flow config ------------------------------------------------------------

@app.route("/api/config")
def config():
    return jsonify(FLOW)


# --- AI endpoints -----------------------------------------------------------

@app.route("/api/story", methods=["POST"])
def write_story():
    def produce():
        topic = request.get_json(force=True)["topic"]
        prompt = (
            f"Write a creative, silly 75-word children's story about {topic}. "
            "Include characters, a conflict, rising action, a surprising "
            "resolution, and a piece of short dialogue. Do not include a title "
            "or any heading — return only the story prose."
        )
        story_text = generate_text(
            prompt,
            system="You are a playful children's story writer.",
        )
        return {"story": _strip_heading(story_text)}

    return _ai_route(produce)


@app.route("/api/title", methods=["POST"])
def get_title():
    def produce():
        story_text = request.get_json(force=True)["story"]
        prompt = (
            "Create a catchy, creative title for this children's story. "
            f"Return only the title, with no quotation marks.\n\n{story_text}"
        )
        return {"title": generate_text(prompt, max_tokens=64)}

    return _ai_route(produce)


@app.route("/api/remix", methods=["POST"])
def remix_story():
    def produce():
        data = request.get_json(force=True)
        original = data["story"]
        words = data["words"]  # {slot: value, ...}; slot name encodes the part of speech
        # Label each word with its part of speech (adjective1 -> adjective) so
        # the model places it correctly.
        replacements = "\n".join(
            f"- {slot.rstrip('0123456789')}: {value}"
            for slot, value in words.items()
        )
        prompt = (
            "Rework the story below so that it naturally includes EVERY one of "
            "the words listed, each used at least once and as the indicated part "
            "of speech. This is the whole point of the game, so do NOT drop or "
            "skip any word. Prefer swapping a word of the same part of speech; "
            "if a word has no natural slot, lightly adjust that sentence so the "
            "word fits. Use each word in the exact form given where you can. "
            "Keep the story coherent, silly, family-friendly, and about the same "
            "length. Return only the updated story.\n\n"
            f"Story:\n{original}\n\n"
            f"Words that must ALL appear:\n{replacements}"
        )
        return {"story": _strip_heading(generate_text(prompt))}

    return _ai_route(produce)


@app.route("/api/image", methods=["POST"])
def get_image():
    def produce():
        story_text = request.get_json(force=True)["story"]

        # First, turn the story into a purely visual scene description — no
        # dialogue, sound effects, or names. This keeps text the image model
        # would otherwise render (quotes, "SPLAT!", character names) out of its
        # input entirely, which matters far more than prompt instructions.
        describe_prompt = (
            "You are planning a single illustration for a children's book. "
            "Based on the story below, write a 2-3 sentence description of one "
            "visual scene to illustrate. Describe only what is physically "
            "visible: the characters' appearance, the setting, the action, "
            "colors, and mood. Do NOT include any dialogue, quotations, sound "
            "effects, onomatopoeia, character names, signs, or any words meant "
            "to appear as text. Refer to characters by appearance, not by name. "
            f"Return only the description.\n\nStory:\n{story_text}"
        )
        scene = generate_text(
            describe_prompt,
            system="You write concise, vivid visual scene descriptions.",
            max_tokens=256,
        )

        prompt = (
            "A single whimsical, colorful children's-book illustration of one "
            "cohesive scene. The image must contain absolutely no text, words, "
            "letters, captions, labels, or speech bubbles — a purely wordless "
            f"picture.\n\nScene: {scene}"
        )
        return {"image": generate_image(prompt)}

    return _ai_route(produce)


if __name__ == "__main__":
    app.run(debug=True)
