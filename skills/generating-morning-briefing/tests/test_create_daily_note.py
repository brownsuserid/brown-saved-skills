"""Tests for create_daily_note.py — Obsidian daily note creation."""

import sys
import os

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "scripts",
        "generating-morning-briefing",
    ),
)

from create_daily_note import (
    build_obsidian_uri,
    create_note_from_template,
    populate_meetings,
)


class TestCreateNoteFromTemplate:
    """create_note_from_template() creates daily notes from Obsidian templates."""

    def test_creates_new_note(self, tmp_path):
        # Arrange
        template = tmp_path / "template.md"
        template.write_text('# <%tp.file.creation_date("YYYY-MM-DD")%>\n%%meetings%%')
        daily_note = tmp_path / "2026-02-16.md"

        import create_daily_note

        orig_template = create_daily_note.TEMPLATE_PATH
        create_daily_note.TEMPLATE_PATH = str(template)
        try:
            # Act
            created = create_note_from_template("2026-02-16", str(daily_note))

            # Assert
            assert created is True
            content = daily_note.read_text()
            assert "# 2026-02-16" in content
            assert "%%meetings%%" in content
        finally:
            create_daily_note.TEMPLATE_PATH = orig_template

    def test_skips_existing_note(self, tmp_path):
        # Arrange
        daily_note = tmp_path / "2026-02-16.md"
        daily_note.write_text("existing content")

        # Act
        created = create_note_from_template("2026-02-16", str(daily_note))

        # Assert
        assert created is False
        assert daily_note.read_text() == "existing content"

    def test_missing_template(self, tmp_path):
        # Arrange
        daily_note = tmp_path / "2026-02-16.md"

        import create_daily_note

        orig_template = create_daily_note.TEMPLATE_PATH
        create_daily_note.TEMPLATE_PATH = str(tmp_path / "nonexistent.md")
        try:
            # Act
            created = create_note_from_template("2026-02-16", str(daily_note))

            # Assert
            assert created is False
        finally:
            create_daily_note.TEMPLATE_PATH = orig_template


class TestPopulateMeetings:
    """populate_meetings() replaces %%meetings%% placeholder."""

    def test_replaces_placeholder(self, tmp_path):
        # Arrange
        note = tmp_path / "note.md"
        note.write_text("# Today\n%%meetings%%\n## Tasks")

        # Act
        result = populate_meetings(str(note), "- 9:00 AM Standup\n- 10:00 AM Review")

        # Assert
        assert result is True
        content = note.read_text()
        assert "9:00 AM Standup" in content
        assert "%%meetings%%" not in content

    def test_no_placeholder(self, tmp_path):
        # Arrange
        note = tmp_path / "note.md"
        note.write_text("# Today\nNo placeholder here")

        # Act
        result = populate_meetings(str(note), "meetings content")

        # Assert
        assert result is False

    def test_missing_file(self, tmp_path):
        # Act
        result = populate_meetings(str(tmp_path / "missing.md"), "content")

        # Assert
        assert result is False


class TestBuildObsidianUri:
    """build_obsidian_uri() constructs deeplinks."""

    def test_uri_format(self):
        # Act
        uri = build_obsidian_uri("2026-02-16")

        # Assert
        assert uri.startswith("obsidian://open?vault=")
        assert "2026-02-16" in uri
        assert "Daily%20Notes" in uri
