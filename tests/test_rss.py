"""Tests for the RSS feed parser."""

from __future__ import annotations

from pathlib import Path

import pytest
import responses as rsps

from radiofrance_downloader.rss import RSSParser


@pytest.fixture
def parser():
    return RSSParser()


@pytest.fixture
def rss_xml(fixtures_dir: Path) -> str:
    return (fixtures_dir / "sample_rss.xml").read_text()


class TestRSSParser:
    def test_parse_feed(self, parser, rss_xml):
        episodes = parser.parse_feed(rss_xml)
        assert len(episodes) == 2

        ep1 = episodes[0]
        assert ep1.title == "Épisode du 15 janvier 2025"
        assert ep1.description == "Un épisode formidable"
        assert ep1.id == "ep-001"
        assert ep1.audio_url.endswith(".mp3")
        assert ep1.duration == 180  # 03:00
        assert ep1.show_title == "Le Billet de Guillaume Meurice"
        assert ep1.published_at is not None
        assert ep1.image_url.endswith(".jpg")

        ep2 = episodes[1]
        assert ep2.duration == 195  # raw seconds

    def test_parse_feed_empty(self, parser):
        xml = '<?xml version="1.0"?><rss><channel><title>Empty</title></channel></rss>'
        episodes = parser.parse_feed(xml)
        assert episodes == []

    def test_parse_feed_invalid_xml(self, parser):
        from radiofrance_downloader.exceptions import RadioFranceError

        with pytest.raises(RadioFranceError, match="Invalid RSS XML"):
            parser.parse_feed("not xml at all <<<")

    def test_fetch_episodes(self, parser, rss_xml):
        rsps.get(
            "https://example.com/feed.xml",
            body=rss_xml,
            status=200,
        )

        episodes = parser.fetch_episodes("https://example.com/feed.xml")
        assert len(episodes) == 2

    def test_fetch_episodes_http_error(self, parser):
        rsps.get(
            "https://example.com/feed.xml",
            body="Server Error",
            status=500,
        )

        from radiofrance_downloader.exceptions import RadioFranceError

        with pytest.raises(RadioFranceError):
            parser.fetch_episodes("https://example.com/feed.xml")

    def test_build_aerion_url(self):
        url = RSSParser.build_aerion_url("12345")
        assert url == "https://radiofrance-podcast.net/podcast09/rss_12345.xml"

    def test_parse_duration_hhmmss(self, parser):
        assert parser._parse_duration("01:30:00") == 5400

    def test_parse_duration_mmss(self, parser):
        assert parser._parse_duration("03:00") == 180

    def test_parse_duration_seconds(self, parser):
        assert parser._parse_duration("195") == 195

    def test_parse_duration_invalid(self, parser):
        assert parser._parse_duration("invalid") == 0
