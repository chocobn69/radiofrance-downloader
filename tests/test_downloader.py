"""Tests for the download engine."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
import responses as rsps

from radiofrance_downloader.downloader import EpisodeDownloader, sanitize_filename
from radiofrance_downloader.exceptions import DownloadError
from radiofrance_downloader.models import Episode


class TestSanitizeFilename:
    def test_simple(self):
        assert sanitize_filename("hello world") == "hello-world"

    def test_special_chars(self):
        assert sanitize_filename("épisode: 1/2\\3") == "episode-1-2-3"

    def test_multiple_hyphens(self):
        assert sanitize_filename("a - - b") == "a-b"

    def test_empty(self):
        assert sanitize_filename("") == "episode"

    def test_long_name(self):
        result = sanitize_filename("x" * 300)
        assert len(result) <= 200


class TestEpisodeDownloader:
    @pytest.fixture
    def episode(self):
        return Episode(
            id="ep-001",
            title="Test Episode",
            show_id="1234",
            show_title="My Show",
            published_at=datetime(2025, 1, 15, tzinfo=UTC),
            audio_url="https://example.com/test.mp3",
        )

    @pytest.fixture
    def downloader(self, tmp_path):
        return EpisodeDownloader(output_dir=tmp_path)

    def test_download_episode(self, downloader, episode, tmp_path):
        content = b"fake mp3 content" * 100
        rsps.get(
            "https://example.com/test.mp3",
            body=content,
            status=200,
            headers={"Content-Length": str(len(content))},
        )

        result = downloader.download_episode(episode)
        assert result.success
        assert result.file_path is not None
        assert result.file_path.exists()
        assert result.file_path.suffix == ".mp3"
        assert result.file_size == len(content)
        assert "My-Show" in str(result.file_path)
        assert "2025-01-15" in result.file_path.name

    def test_skip_existing(self, downloader, episode, tmp_path):
        # Create the file first
        show_dir = tmp_path / "My-Show"
        show_dir.mkdir()
        existing = show_dir / "2025-01-15_Test-Episode.mp3"
        existing.write_bytes(b"existing data")

        result = downloader.download_episode(episode)
        assert result.success
        assert result.already_existed

    def test_no_audio_url(self, downloader):
        ep = Episode(id="1", title="No Audio")
        result = downloader.download_episode(ep)
        assert not result.success
        assert "No audio URL" in result.error

    def test_progress_callback(self, downloader, episode):
        content = b"x" * 1000
        rsps.get(
            "https://example.com/test.mp3",
            body=content,
            status=200,
            headers={"Content-Length": str(len(content))},
        )

        callback = MagicMock()
        result = downloader.download_episode(episode, progress_callback=callback)
        assert result.success
        assert callback.called

    def test_download_http_error(self, downloader, episode):
        rsps.get(
            "https://example.com/test.mp3",
            body="Not found",
            status=404,
        )

        with pytest.raises(DownloadError):
            downloader.download_episode(episode)
