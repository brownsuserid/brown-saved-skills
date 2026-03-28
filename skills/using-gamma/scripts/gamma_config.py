"""Gamma API configuration."""

import os
import sys

API_BASE_URL = "https://public-api.gamma.app/v1.0"

POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 300

DEFAULT_FORMAT = "presentation"
DEFAULT_TEXT_MODE = "generate"
DEFAULT_NUM_CARDS = 10
DEFAULT_CARD_SPLIT = "auto"

VALID_FORMATS = ["presentation", "document", "social", "webpage"]
VALID_TEXT_MODES = ["generate", "condense", "preserve"]
VALID_CARD_SPLITS = ["auto", "inputTextBreaks"]
VALID_EXPORT_FORMATS = ["pdf", "pptx"]
VALID_IMAGE_SOURCES = [
    "aiGenerated",
    "pexels",
    "noImages",
    "googleImages",
    "aiAndWeb",
]
VALID_IMAGE_MODELS = [
    "imagen-4-pro",
]
VALID_IMAGE_STYLES = [
    "photorealistic",
]


def get_api_key() -> str:
    """Load API key from GAMMA_API_KEY env var."""
    key = os.environ.get("GAMMA_API_KEY", "")
    if not key:
        print("Error: GAMMA_API_KEY environment variable is not set.", file=sys.stderr)
        print("Get your key at https://gamma.app/settings/developers", file=sys.stderr)
        sys.exit(1)
    return key


def get_headers() -> dict:
    """Return auth headers for Gamma API requests."""
    return {
        "X-API-KEY": get_api_key(),
        "Content-Type": "application/json",
    }
