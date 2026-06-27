# chatlibs-flask

A Mad-Libs–meets-AI children's story generator. Pick a topic, the AI writes a
silly 75-word story, you supply six words blind, the AI swaps them into the
story, and you get an illustrated, shareable result.

This is a ground-up rewrite of the original. The front end (look, fonts, flow,
mobile behavior) is unchanged; the backend is new.

## Architecture

- **Flask** app (`api/index.py`), deployable as a Vercel serverless function.
- **Provider-agnostic AI layer** (`api/ai.py`): text and image generation each
  dispatch to a pluggable backend chosen by env var. Today: Anthropic Claude
  (text) + Google Imagen 4 (image). Swapping models/vendors is a config change.
- **Config-driven flow** (`api/flow.py`): the steps, prompts, and word slots
  live in one data structure served to the client at `/api/config`. The browser
  orchestrates the flow off that config — change the game design in one place.
- **Stateless endpoints**: `/api/story`, `/api/title`, `/api/remix`,
  `/api/image` each wrap one AI call and return a uniform JSON envelope with
  real error handling. `/` and `/story` render the two pages.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY and GOOGLE_API_KEY
```

The static image assets (`chatlibs-logo.png`, `chatlibs-share.png`,
`donors-choose-ad.png`) carry over from the original repo — keep them in
`api/static/`.

## Run locally

```bash
export $(grep -v '^#' .env | xargs)   # or use your preferred env loader
python api/index.py
# open http://localhost:5000
```

## Configuration

| Env var          | Default                   | Notes |
|------------------|---------------------------|-------|
| `ANTHROPIC_API_KEY` | —                      | required for text |
| `TEXT_MODEL`     | `claude-sonnet-4-6`       | `claude-haiku-4-5` is cheaper; `claude-opus-4-8` is max quality |
| `GOOGLE_API_KEY` | —                         | required for image (`GEMINI_API_KEY` also accepted) |
| `IMAGE_MODEL`    | `imagen-4.0-generate-001` | |
| `TEXT_PROVIDER`  | `anthropic`               | |
| `IMAGE_PROVIDER` | `google`                  | |

## Notes

- Images are returned as `data:` URIs and shown in-app only (ephemeral, by
  design). The shareable `/story` page carries the title and story text; its
  social-preview image falls back to the brand share image.
