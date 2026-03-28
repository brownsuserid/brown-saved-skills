---
name: using-gamma
description: Creates presentations, slide decks, documents, social posts, and webpages via the Gamma API. Use whenever the user wants to generate a deck, pitch presentation, one-pager, landing page, social media visual, or any visual content from a topic or existing text. Gamma generates polished visual content from scratch (create-only, no editing). Also triggers for "make me slides", "build a deck", "create a presentation about", "generate a one-pager", PPTX/PDF export of generated content, or any request for AI-generated visual documents. Do NOT use for editing existing Google Slides (use using-gog instead).
---

# Gamma

Use the `gamma.py` wrapper to generate presentations, documents, social posts, and webpages via the Gamma public API. Gamma is create-only: there is no API for editing existing content.

## Setup

1. Get an API key from [gamma.app/settings/developers](https://gamma.app/settings/developers)
2. Set the env var: `export GAMMA_API_KEY=<your-key>`

## Cost Awareness

Gamma uses credit-based pricing:
- **3-4 credits per card** for standard generation
- **More credits for AI-generated images** (`--image-source aiGenerated`)
- Check your balance at gamma.app before bulk generation

---

## Choosing Parameters

Before running a command, translate the user's request into the right parameters.

### Format

Pick based on what the user actually wants:
- `presentation` — slide decks, pitch decks, keynotes, any "slides" request
- `document` — one-pagers, reports, written docs with visual layout
- `social` — social media posts, short visual content
- `webpage` — landing pages, web content

### Text Mode

This controls how Gamma uses the input you provide:
- `generate` — you have a **topic or short prompt** and want Gamma to write the content. Use this when the user says "make a presentation about X."
- `condense` — you have **long-form content** (an article, notes, transcript) and want Gamma to distill it into cards. Use this when the user provides a file or large block of text.
- `preserve` — you have **exact text** the user wants kept verbatim across the cards. Rare, but useful when wording matters (legal, compliance).

### Number of Cards

Match the format and content density:
- **Presentations:** 8-15 cards (10 is a solid default for most decks)
- **Documents:** 5-10 cards
- **Social posts:** 1-3 cards
- **Webpages:** 3-8 cards

When the user specifies a length ("keep it short", "make it detailed"), adjust accordingly.

---

## Generate a Presentation

```bash
uv run ~/.openclaw/skills/using-gamma/scripts/gamma.py generate \
  --text "Content or prompt here" \
  --format presentation \
  --text-mode generate \
  --num-cards 10
```

With export:
```bash
uv run ~/.openclaw/skills/using-gamma/scripts/gamma.py generate \
  --text "Quarterly business review for Q1 2026" \
  --format presentation \
  --text-mode generate \
  --num-cards 12 \
  --export-as pptx \
  --tone "professional" \
  --audience "investors"
```

From a file:
```bash
uv run ~/.openclaw/skills/using-gamma/scripts/gamma.py generate \
  --text-file /tmp/content.md \
  --format presentation \
  --text-mode condense \
  --num-cards 8
```

## Generate from Template

```bash
uv run ~/.openclaw/skills/using-gamma/scripts/gamma.py from-template \
  --gamma-id <gammaId> \
  --prompt "Customize with this content"
```

## List Themes

```bash
uv run ~/.openclaw/skills/using-gamma/scripts/gamma.py themes
```

## List Folders

```bash
uv run ~/.openclaw/skills/using-gamma/scripts/gamma.py folders
```

## Check Generation Status

```bash
uv run ~/.openclaw/skills/using-gamma/scripts/gamma.py status --id <generationId>
```

Note: `generate` and `from-template` auto-poll until completion. Use `status` only if you need to check a previous generation manually.

---

## Parameters Reference

| Parameter | Values | Default | Description |
|-----------|--------|---------|-------------|
| `--format` | presentation, document, social, webpage | presentation | Output format |
| `--text-mode` | generate, condense, preserve | generate | How Gamma uses your input text |
| `--num-cards` | 1-60 | 10 | Number of cards/slides |
| `--card-split` | auto, inputTextBreaks | auto | How to split content across cards |
| `--export-as` | pdf, pptx | *(none)* | Export format (optional) |
| `--tone` | e.g. professional, casual, formal | *(none)* | Tone of generated text |
| `--audience` | e.g. investors, team, customers | *(none)* | Target audience |
| `--language` | e.g. English, Spanish | *(none)* | Output language |
| `--amount` | e.g. concise, detailed | *(none)* | Text verbosity |
| `--image-source` | aiGenerated, pexels, noImages, googleImages, aiAndWeb | *(none)* | Image source |
| `--image-model` | e.g. imagen-4-pro | *(none)* | AI image model (only with aiGenerated source) |
| `--image-style` | e.g. photorealistic | *(none)* | Style for AI-generated images |
| `--additional-instructions` | string (1-2000 chars) | *(none)* | Custom directives for generation |
| `--theme-id` | string | *(none)* | Theme ID from `themes` command |

## Limitations

- **Create-only**, no API for editing, updating, or deleting existing presentations
- **Async generation**, presentations take 30-120s to generate; the script auto-polls
- **Credit-based**, each generation costs credits; AI images cost more
- **Rate limits**, respect Gamma's rate limits for bulk generation

## Notes

- All output is JSON for programmatic use
- The script auto-polls after creation until the generation completes
- Use `--json-pretty` for human-readable JSON output
