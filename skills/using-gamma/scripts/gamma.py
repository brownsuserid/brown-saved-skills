#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///
"""Thin CLI wrapper around the Gamma public REST API.

Usage:
    uv run gamma.py generate --text "..." [options]
    uv run gamma.py from-template --template-id ID --prompt "..." [options]
    uv run gamma.py status --id GENERATION_ID
    uv run gamma.py themes
    uv run gamma.py folders
"""

import argparse
import json
import os
import sys
import time

import requests

from gamma_config import (
    API_BASE_URL,
    DEFAULT_CARD_SPLIT,
    DEFAULT_FORMAT,
    DEFAULT_NUM_CARDS,
    DEFAULT_TEXT_MODE,
    POLL_INTERVAL_SECONDS,
    POLL_TIMEOUT_SECONDS,
    VALID_CARD_SPLITS,
    VALID_EXPORT_FORMATS,
    VALID_FORMATS,
    VALID_IMAGE_MODELS,
    VALID_IMAGE_SOURCES,
    VALID_IMAGE_STYLES,
    VALID_TEXT_MODES,
    get_headers,
)


def poll_generation(generation_id: str, headers: dict) -> dict:
    """Poll a generation until it completes or times out."""
    url = f"{API_BASE_URL}/generations/{generation_id}"
    elapsed = 0
    while elapsed < POLL_TIMEOUT_SECONDS:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "unknown")
        if status == "completed":
            return data
        if status in ("failed", "error"):
            print(
                json.dumps({"error": "Generation failed", "details": data}),
                file=sys.stderr,
            )
            sys.exit(1)
        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS
    print(
        json.dumps({"error": "Generation timed out", "generationId": generation_id}),
        file=sys.stderr,
    )
    sys.exit(1)


def cmd_generate(args):
    """Generate a presentation/document from text."""
    text = args.text
    if args.text_file:
        if not os.path.isfile(args.text_file):
            print(
                f"Error: File not found: {args.text_file}",
                file=sys.stderr,
            )
            sys.exit(1)
        with open(args.text_file, "r") as f:
            text = f.read()
    if not text:
        print("Error: --text or --text-file is required.", file=sys.stderr)
        sys.exit(1)

    body = {
        "inputText": text,
        "format": args.format,
        "textMode": args.text_mode,
        "numCards": args.num_cards,
        "cardSplit": args.card_split,
    }

    # Optional text options
    text_options = {}
    if args.tone:
        text_options["tone"] = args.tone
    if args.audience:
        text_options["audience"] = args.audience
    if args.language:
        text_options["language"] = args.language
    if args.amount:
        text_options["amount"] = args.amount
    if text_options:
        body["textOptions"] = text_options

    # Image options (nested object)
    image_options = {}
    if args.image_source:
        image_options["source"] = args.image_source
    if args.image_model:
        image_options["model"] = args.image_model
    if args.image_style:
        image_options["style"] = args.image_style
    if image_options:
        body["imageOptions"] = image_options

    if args.theme_id:
        body["themeId"] = args.theme_id
    if args.additional_instructions:
        body["additionalInstructions"] = args.additional_instructions
    if args.export_as:
        body["exportAs"] = args.export_as

    headers = get_headers()
    resp = requests.post(
        f"{API_BASE_URL}/generations", json=body, headers=headers, timeout=30
    )
    resp.raise_for_status()
    data = resp.json()

    generation_id = data.get("id") or data.get("generationId")
    if not generation_id:
        output(data, args.json_pretty)
        return

    # Auto-poll until complete
    result = poll_generation(generation_id, headers)
    output(result, args.json_pretty)


def cmd_from_template(args):
    """Generate from a Gamma template."""
    body = {
        "gammaId": args.gamma_id,
    }
    if args.prompt:
        body["prompt"] = args.prompt
    if args.export_as:
        body["exportAs"] = args.export_as
    if args.theme_id:
        body["themeId"] = args.theme_id

    headers = get_headers()
    resp = requests.post(
        f"{API_BASE_URL}/generations/from-template",
        json=body,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    generation_id = data.get("id") or data.get("generationId")
    if not generation_id:
        output(data, args.json_pretty)
        return

    result = poll_generation(generation_id, headers)
    output(result, args.json_pretty)


def cmd_status(args):
    """Check generation status."""
    headers = get_headers()
    resp = requests.get(
        f"{API_BASE_URL}/generations/{args.id}", headers=headers, timeout=30
    )
    resp.raise_for_status()
    output(resp.json(), args.json_pretty)


def cmd_themes(args):
    """List available themes."""
    headers = get_headers()
    params = {}
    if args.query:
        params["query"] = args.query
    if args.limit:
        params["limit"] = args.limit
    resp = requests.get(
        f"{API_BASE_URL}/themes", headers=headers, params=params, timeout=30
    )
    resp.raise_for_status()
    output(resp.json(), args.json_pretty)


def cmd_folders(args):
    """List folders."""
    headers = get_headers()
    params = {}
    if args.query:
        params["query"] = args.query
    if args.limit:
        params["limit"] = args.limit
    resp = requests.get(
        f"{API_BASE_URL}/folders", headers=headers, params=params, timeout=30
    )
    resp.raise_for_status()
    output(resp.json(), args.json_pretty)


def output(data, pretty: bool = False):
    """Print JSON output."""
    if pretty:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data))


def add_common_args(parser):
    """Add args shared across subcommands."""
    parser.add_argument(
        "--json-pretty", action="store_true", help="Pretty-print JSON output"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Gamma API CLI — generate presentations, documents, and more"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate
    gen = subparsers.add_parser("generate", help="Generate from text")
    gen.add_argument("--text", help="Input text/prompt")
    gen.add_argument("--text-file", help="Read input text from file")
    gen.add_argument(
        "--format",
        choices=VALID_FORMATS,
        default=DEFAULT_FORMAT,
        help=f"Output format (default: {DEFAULT_FORMAT})",
    )
    gen.add_argument(
        "--text-mode",
        choices=VALID_TEXT_MODES,
        default=DEFAULT_TEXT_MODE,
        help=f"How Gamma uses input text (default: {DEFAULT_TEXT_MODE})",
    )
    gen.add_argument(
        "--num-cards",
        type=int,
        default=DEFAULT_NUM_CARDS,
        help=f"Number of cards (1-60, default: {DEFAULT_NUM_CARDS})",
    )
    gen.add_argument(
        "--card-split",
        choices=VALID_CARD_SPLITS,
        default=DEFAULT_CARD_SPLIT,
        help=f"Card split mode (default: {DEFAULT_CARD_SPLIT})",
    )
    gen.add_argument(
        "--export-as",
        choices=VALID_EXPORT_FORMATS,
        help="Export format (pdf or pptx)",
    )
    gen.add_argument("--tone", help="Tone of generated text")
    gen.add_argument("--audience", help="Target audience")
    gen.add_argument("--language", help="Output language")
    gen.add_argument("--amount", help="Text verbosity (e.g. concise, detailed)")
    gen.add_argument(
        "--image-source",
        choices=VALID_IMAGE_SOURCES,
        help="Image source",
    )
    gen.add_argument(
        "--image-model",
        choices=VALID_IMAGE_MODELS,
        help="AI image model (e.g. imagen-4-pro)",
    )
    gen.add_argument(
        "--image-style",
        choices=VALID_IMAGE_STYLES,
        help="Image style (e.g. photorealistic)",
    )
    gen.add_argument("--theme-id", help="Theme ID")
    gen.add_argument(
        "--additional-instructions",
        help="Custom directives (1-2000 chars)",
    )
    add_common_args(gen)

    # from-template
    tmpl = subparsers.add_parser("from-template", help="Generate from template")
    tmpl.add_argument("--gamma-id", required=True, help="Gamma template ID (gammaId)")
    tmpl.add_argument("--prompt", help="Customization prompt")
    tmpl.add_argument(
        "--export-as",
        choices=VALID_EXPORT_FORMATS,
        help="Export format",
    )
    tmpl.add_argument("--theme-id", help="Theme ID")
    add_common_args(tmpl)

    # status
    st = subparsers.add_parser("status", help="Check generation status")
    st.add_argument("--id", required=True, help="Generation ID")
    add_common_args(st)

    # themes
    th = subparsers.add_parser("themes", help="List available themes")
    th.add_argument("--query", help="Search by name (case-insensitive)")
    th.add_argument("--limit", type=int, help="Max results (up to 50)")
    add_common_args(th)

    # folders
    fo = subparsers.add_parser("folders", help="List folders")
    fo.add_argument("--query", help="Search by name (case-insensitive)")
    fo.add_argument("--limit", type=int, help="Max results (up to 50)")
    add_common_args(fo)

    args = parser.parse_args()

    try:
        {
            "generate": cmd_generate,
            "from-template": cmd_from_template,
            "status": cmd_status,
            "themes": cmd_themes,
            "folders": cmd_folders,
        }[args.command](args)
    except requests.HTTPError as e:
        error_body = ""
        if e.response is not None:
            try:
                error_body = e.response.json()
            except ValueError:
                error_body = e.response.text
        print(
            json.dumps({"error": str(e), "details": error_body}),
            file=sys.stderr,
        )
        sys.exit(1)
    except requests.ConnectionError as e:
        print(json.dumps({"error": f"Connection failed: {e}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
