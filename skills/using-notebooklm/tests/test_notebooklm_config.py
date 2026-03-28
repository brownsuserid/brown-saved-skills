"""Tests for notebooklm_config.py — constants, selectors, and paths."""

import notebooklm_config


class TestSelectors:
    """SELECTORS dict is well-formed."""

    def test_selectors_is_dict(self):
        assert isinstance(notebooklm_config.SELECTORS, dict)

    def test_every_key_maps_to_nonempty_list(self):
        for key, selectors in notebooklm_config.SELECTORS.items():
            assert isinstance(selectors, list), f"{key} is not a list"
            assert len(selectors) > 0, f"{key} is empty"

    def test_every_selector_is_a_string(self):
        for key, selectors in notebooklm_config.SELECTORS.items():
            for s in selectors:
                assert isinstance(s, str), f"{key} contains non-string: {s!r}"

    def test_required_keys_present(self):
        required = [
            "create_notebook",
            "add_source_button",
            "chat_input",
            "chat_submit",
            "chat_response",
            "audio_generate",
            "audio_play_button",
            "audio_download",
            "signed_in_indicator",
            "sign_in_page",
        ]
        for key in required:
            assert key in notebooklm_config.SELECTORS, f"Missing key: {key}"


class TestUrls:
    """URL constants are valid."""

    def test_base_url(self):
        assert notebooklm_config.BASE_URL == "https://notebooklm.google.com"

    def test_notebooks_url_starts_with_base(self):
        assert notebooklm_config.NOTEBOOKS_URL.startswith(notebooklm_config.BASE_URL)


class TestPaths:
    """Path constants are under ~/.openclaw."""

    def test_state_file_in_openclaw(self):
        assert ".openclaw" in str(notebooklm_config.STATE_FILE)
        assert str(notebooklm_config.STATE_FILE).endswith(".json")

    def test_chrome_profile_in_openclaw(self):
        assert ".openclaw" in str(notebooklm_config.CHROME_PROFILE_DIR)


class TestBrowserSettings:
    """Browser setting constants are sensible."""

    def test_viewport_width_above_minimum(self):
        assert notebooklm_config.VIEWPORT["width"] > 1051

    def test_viewport_has_height(self):
        assert notebooklm_config.VIEWPORT["height"] > 0

    def test_typing_delay_range(self):
        assert (
            notebooklm_config.TYPING_DELAY_MIN_MS
            < notebooklm_config.TYPING_DELAY_MAX_MS
        )

    def test_default_timeout_positive(self):
        assert notebooklm_config.DEFAULT_TIMEOUT_MS > 0

    def test_audio_timeout_at_least_5_minutes(self):
        assert notebooklm_config.AUDIO_GENERATION_TIMEOUT_MS >= 300_000
