"""Tests for the web scraper fallback."""

from __future__ import annotations

from pathlib import Path

import pytest
import responses as rsps

from radiofrance_downloader.exceptions import ScrapingError
from radiofrance_downloader.scraper import RADIOFRANCE_BASE, RadioFranceScraper


@pytest.fixture
def scraper():
    return RadioFranceScraper()


@pytest.fixture
def show_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "show_page.html").read_text()


@pytest.fixture
def episode_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "episode_page.html").read_text()


class TestRadioFranceScraper:
    def test_get_episodes(self, scraper, show_html):
        rsps.get(
            f"{RADIOFRANCE_BASE}/franceinter/podcasts/le-billet-de-guillaume-meurice",
            body=show_html,
            status=200,
        )

        episodes = scraper.get_episodes("franceinter", "le-billet-de-guillaume-meurice")
        assert len(episodes) == 1
        assert episodes[0].title == "Épisode du 15 janvier 2025"
        assert episodes[0].audio_url.endswith(".mp3")

    def test_get_episode_audio_url(self, scraper, episode_html):
        rsps.get(
            f"{RADIOFRANCE_BASE}/franceinter/podcasts/test/ep-001",
            body=episode_html,
            status=200,
        )

        url = scraper.get_episode_audio_url("/franceinter/podcasts/test/ep-001")
        assert url.endswith(".mp3")
        assert "radiofrance-podcast.net" in url

    def test_get_episodes_http_error(self, scraper):
        rsps.get(
            f"{RADIOFRANCE_BASE}/franceinter/podcasts/nonexistent",
            body="Not Found",
            status=404,
        )

        with pytest.raises(ScrapingError):
            scraper.get_episodes("franceinter", "nonexistent")

    def test_extract_audio_url_regex_fallback(self, scraper):
        html = """
        <html><body>
        <script>var url = "https://media.radiofrance-podcast.net/podcast09/test.mp3";</script>
        </body></html>
        """
        url = scraper._extract_audio_url(html)
        assert url == "https://media.radiofrance-podcast.net/podcast09/test.mp3"

    def test_extract_audio_url_not_found(self, scraper):
        with pytest.raises(ScrapingError, match="Could not find audio URL"):
            scraper._extract_audio_url("<html><body>nothing here</body></html>")
