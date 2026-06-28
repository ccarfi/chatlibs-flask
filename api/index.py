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

# Placeholder tokens the story is generated around, e.g. "{adjective1}", in the
# A-N-A-V-A-N order. The remix step fills these by literal substitution.
SLOTS = [w["slot"] for w in FLOW["words"]]


@app.route("/api/story", methods=["POST"])
def write_story():
    def produce():
        topic = request.get_json(force=True)["topic"]
        tokens = ", ".join("{" + s + "}" for s in SLOTS)
        prompt = (
            f"Write a creative, silly 75-word children's story about {topic}. "
            "Include characters, a conflict, rising action, a surprising "
            "resolution, and a piece of short dialogue. The story MUST contain "
            "these fill-in-the-blank placeholder tokens, each appearing EXACTLY "
            "once, placed where that part of speech fits naturally in a "
            f"sentence: {tokens}. Write each token literally with its curly "
            "braces (for example: a {adjective1} hat). Tokens named 'adjectiveN' "
            "are adjectives, 'nounN' are nouns, and 'verb' is a verb. Do not "
            "explain the tokens, and do not include a title or heading. Return "
            "only the story."
        )
        # Every blank must be present, so validate and retry; keep the best
        # attempt (fewest missing) if the model still slips.
        best, best_missing = "", len(SLOTS) + 1
        for _ in range(3):
            story_text = _strip_heading(generate_text(
                prompt, system="You are a playful children's story writer."))
            missing = sum(1 for s in SLOTS if "{" + s + "}" not in story_text)
            if missing == 0:
                return {"story": story_text}
            if missing < best_missing:
                best, best_missing = story_text, missing
        app.logger.warning("Story template missing %d blank(s)", best_missing)
        return {"story": best}

    return _ai_route(produce)


@app.route("/api/title", methods=["POST"])
def get_title():
    def produce():
        story_text = request.get_json(force=True)["story"]
        prompt = (
            "Create a catchy, creative title for this children's story. The "
            "{curly-brace} tokens are fill-in-the-blank placeholders — ignore "
            f"them. Return only the title, with no quotation marks.\n\n{story_text}"
        )
        return {"title": generate_text(prompt, max_tokens=64)}

    return _ai_route(produce)


@app.route("/api/remix", methods=["POST"])
def remix_story():
    def produce():
        data = request.get_json(force=True)
        template = data["story"]
        words = data["words"]  # {slot: value, ...}
        # True Mad Libs: drop the user's words into the blanks verbatim and leave
        # the rest of the story untouched (#25). No model rewording — purely
        # mechanical, so the original text and the incongruity are preserved.
        filled = template
        for slot, value in words.items():
            filled = filled.replace("{" + slot + "}", value)
        # Remove any blank the story step failed to fill, so no "{noun2}" leaks.
        for slot in SLOTS:
            filled = filled.replace("{" + slot + "}", "")
        return {"story": filled}

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
            "You are planning a single, fun illustration for a deliberately "
            "silly Mad Libs children's story. Based on the story below, write a "
            "2-3 sentence description of one visual scene to illustrate. The "
            "story is absurd on purpose: KEEP the weird, unexpected, and "
            "incongruous objects and qualities and depict them LITERALLY rather "
            "than normalizing them — e.g. a 'trout book' is a fish-shaped book, "
            "a 'truckytrailer' is a truck trailer, a 'foggy pencil' is a pencil "
            "wreathed in fog. Make these surprising elements prominent in the "
            "scene. Describe only what is physically visible: the characters' "
            "and objects' appearance, the setting, the action, colors, and mood. "
            "Do NOT include any dialogue, quotations, sound effects, character "
            "names, signs, or any words meant to appear as text in the image. "
            "Refer to characters by appearance, not by name. Return only the "
            f"description.\n\nStory:\n{story_text}"
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
