"""NotebookLM automation — constants, selectors, and paths."""

from pathlib import Path

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------

BASE_URL = "https://notebooklm.google.com"
NOTEBOOKS_URL = f"{BASE_URL}/notebooks"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

OPENCLAW_DIR = Path.home() / ".openclaw"
STATE_FILE = OPENCLAW_DIR / "notebooklm-state.json"
CHROME_PROFILE_DIR = OPENCLAW_DIR / "notebooklm-chrome-profile"

# ---------------------------------------------------------------------------
# Multi-account support
# ---------------------------------------------------------------------------

ACCOUNTS: dict[str, dict[str, Path]] = {
    "default": {
        "profile_dir": CHROME_PROFILE_DIR,
        "state_file": STATE_FILE,
    },
}


def get_account_config(account: str | None = None) -> dict[str, Path]:
    """Return profile_dir and state_file for a named account.

    Falls back to 'default' when *account* is None or not found.
    """
    if account is None:
        account = "default"
    return ACCOUNTS.get(account, ACCOUNTS["default"])


# ---------------------------------------------------------------------------
# Browser settings
# ---------------------------------------------------------------------------

VIEWPORT = {"width": 1280, "height": 900}
TYPING_DELAY_MIN_MS = 30
TYPING_DELAY_MAX_MS = 80
DEFAULT_TIMEOUT_MS = 30_000
AUDIO_GENERATION_TIMEOUT_MS = 600_000  # 10 minutes
QUERY_STABILITY_CHECKS = 3
QUERY_STABILITY_INTERVAL_MS = 1_000
STUDIO_GENERATION_TIMEOUT_MS = 600_000  # 10 minutes

# ---------------------------------------------------------------------------
# Studio output types
# ---------------------------------------------------------------------------

STUDIO_TYPES: dict[str, dict] = {
    "audio": {"label": "Audio Overview", "ext": ".mp3", "downloadable": True},
    "video": {"label": "Video Overview", "ext": ".mp4", "downloadable": True},
    "mind_map": {"label": "Mind Map", "ext": None, "downloadable": False},
    "report": {"label": "Reports", "ext": ".pdf", "downloadable": True},
    "flashcards": {"label": "Flashcards", "ext": None, "downloadable": False},
    "quiz": {"label": "Quiz", "ext": None, "downloadable": False},
    "infographic": {"label": "Infographic", "ext": ".png", "downloadable": True},
    "slide_deck": {"label": "Slide Deck", "ext": ".pptx", "downloadable": True},
    "data_table": {"label": "Data Table", "ext": ".csv", "downloadable": True},
}

# ---------------------------------------------------------------------------
# CSS Selectors — fallback lists per element
#
# NotebookLM is Angular Material; selectors will break.
# Each key maps to a list tried in order by click_with_fallback / etc.
# ---------------------------------------------------------------------------

SELECTORS: dict[str, list[str]] = {
    # Home page
    "create_notebook": [
        "[aria-label='Create notebook']",
        "button.create-notebook-button",
        'button:has-text("Create notebook")',
    ],
    # Notebook — sources
    "add_source_button": [
        "[aria-label='Add source']",
        "button.add-source-button",
        'button:has-text("Add sources")',
    ],
    "source_type_website": [
        'button:has-text("Websites")',
        'button:has-text("Website")',
        'button.drop-zone-icon-button:has-text("Websites")',
    ],
    "source_type_text": [
        'button:has-text("Copied text")',
        'button.drop-zone-icon-button:has-text("Copied text")',
        'button:has-text("Paste text")',
    ],
    "source_type_youtube": [
        'button:has-text("Websites")',
        'button:has-text("YouTube")',
    ],
    "source_url_input": [
        'input[placeholder*="URL"]',
        'input[placeholder*="url"]',
        'input[placeholder*="Search the web"]',
        "input[type='url']",
    ],
    "source_text_input": [
        'textarea[aria-label="Pasted text"]',
        'textarea[placeholder="Paste text here"]',
        "textarea.copied-text-input-textarea",
    ],
    "source_title_input": [
        "input.title-input",
        'input[placeholder*="Title"]',
        'input[aria-label="Title"]',
    ],
    "source_submit": [
        'button:has-text("Insert")',
        'button:has-text("Add")',
        "button[aria-label='Submit']",
        "button.submit-button",
    ],
    "source_loading_spinner": [
        "mat-spinner",
        ".loading-spinner",
        "[role='progressbar']",
    ],
    "source_close_dialog": [
        "button[aria-label='Close']",
        "button.close-button",
    ],
    "source_upload_button": [
        'button:has-text("Upload a source")',
        "button.upload-button",
        "[aria-label='Opens the upload source dialog']",
        "button.upload-icon-button",
    ],
    # Notebook — chat / query
    "chat_input": [
        'textarea[aria-label="Query box"]',
        "textarea.query-box-input",
        'textarea[placeholder*="source"]',
        'textarea[placeholder*="question"]',
    ],
    "chat_submit": [
        "button.submit-button",
        "button[aria-label='Submit']",
        "button[aria-label='Send']",
    ],
    "chat_response": [
        "chat-message.individual-message mat-card.to-user-message-card-content div.message-text-content",
        "mat-card.to-user-message-card-content div.message-text-content",
        "div.message-text-content",
    ],
    "chat_sources_cited": [
        "div.message-container",
        ".citation",
        ".source-citation",
    ],
    # Notebook — audio / studio panel
    "studio_panel": [
        "[aria-label='Collapse studio panel']",
        "button.toggle-studio-panel-button",
    ],
    "audio_customize": [
        "[aria-label='Customize Audio Overview']",
        'button:has(mat-icon:has-text("audio_magic_eraser"))',
    ],
    "audio_generating_indicator": [
        'button:has-text("Generating Audio Overview")',
        'button:has-text("Generating")',
    ],
    "audio_generate": [
        'button:has-text("Generate")',
        'button:has-text("Create audio")',
        "[aria-label='Generate audio']",
    ],
    "audio_style_deep_dive": [
        'button:has-text("Deep Dive")',
        "[data-style='deep_dive']",
    ],
    "audio_style_summary": [
        'button:has-text("Briefing")',
        'button:has-text("Summary")',
        "[data-style='summary']",
    ],
    "audio_play_button": [
        "button[aria-label='Play']",
        'button:has(mat-icon:has-text("play_arrow"))',
        ".play-button",
    ],
    "audio_loading_spinner": [
        "mat-spinner",
        ".audio-spinner",
        "[role='progressbar']",
    ],
    "audio_more_menu": [
        "button[aria-label='More']:near(button[aria-label='Play'])",
        "button[aria-label='More']",
    ],
    "audio_download": [
        'button:has-text("Download")',
        "[aria-label='Download']",
        'div[role="menuitem"]:has-text("Download")',
        "a[download]",
    ],
    # Auth indicators
    "signed_in_indicator": [
        "button.create-notebook-button",
        "[aria-label='Create notebook']",
        'button:has-text("Create notebook")',
    ],
    "sign_in_page": [
        'button:has-text("Sign in")',
        "#identifierId",
        'input[type="email"]',
    ],
    # Notebook name input (on creation)
    "notebook_name_input": [
        'input[aria-label="Notebook title"]',
        'input[placeholder*="Untitled"]',
        "input.notebook-title",
    ],
    # Home page — notebook cards
    "notebook_card": [
        "a.notebook-item",
        "mat-card.notebook-card",
        "[data-notebook-id]",
        'a[href*="/notebook/"]',
    ],
    "notebook_card_name": [
        ".notebook-title",
        "h3",
        ".notebook-name",
    ],
    # Notebook card — more menu / delete
    "notebook_more_menu": [
        "button[aria-label='More options']",
        "button[aria-label='More']",
        "button.mat-mdc-menu-trigger",
    ],
    "notebook_delete_option": [
        'button:has-text("Move to Trash")',
        'button:has-text("Delete")',
        '[role="menuitem"]:has-text("Delete")',
        '[role="menuitem"]:has-text("Trash")',
    ],
    "notebook_delete_confirm": [
        'button:has-text("Move to Trash")',
        'button:has-text("Delete")',
        'button:has-text("Confirm")',
    ],
    # Source panel — list / manage sources
    "source_item": [
        ".source-item",
        "[data-source-id]",
        "mat-list-item.source-list-item",
    ],
    "source_item_name": [
        ".source-title",
        ".source-name",
        "span.source-title",
    ],
    "source_item_menu": [
        "button[aria-label='Source options']",
        "button[aria-label='More']",
        "button.source-menu-trigger",
    ],
    "source_delete_option": [
        'button:has-text("Remove")',
        'button:has-text("Delete")',
        '[role="menuitem"]:has-text("Remove")',
        '[role="menuitem"]:has-text("Delete")',
    ],
    "source_delete_confirm": [
        'button:has-text("Remove")',
        'button:has-text("Delete")',
        'button:has-text("Confirm")',
    ],
    # Sources dialog — file upload / Google Drive
    "source_type_file": [
        'button:has-text("Upload")',
        'button:has-text("PDF")',
        'button.drop-zone-icon-button:has-text("Upload")',
    ],
    "source_type_drive": [
        'button:has-text("Google Drive")',
        'button:has-text("Drive")',
        'button.drop-zone-icon-button:has-text("Drive")',
    ],
    "source_drive_url_input": [
        'input[placeholder*="Drive"]',
        'input[placeholder*="URL"]',
        'input[placeholder*="paste"]',
    ],
}
