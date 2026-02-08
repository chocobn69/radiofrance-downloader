"""RSS feed parser for Radio France podcasts."""

from __future__ import annotations

from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import requests

from radiofrance_downloader.exceptions import RadioFranceError
from radiofrance_downloader.models import Episode

AERION_URL = "https://radiofrance-podcast.net/podcast09/rss_{show_id}.xml"

# Common namespace for iTunes podcast feeds
ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"


class RSSParser:
    """Parse RSS feeds for Radio France podcasts."""

    def fetch_episodes(self, rss_url: str) -> list[Episode]:
        """Fetch and parse episodes from an RSS feed URL."""
        try:
            resp = requests.get(rss_url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RadioFranceError(f"Failed to fetch RSS feed: {e}") from e

        return self.parse_feed(resp.text)

    def parse_feed(self, xml_text: str) -> list[Episode]:
        """Parse episodes from RSS XML text."""
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as e:
            raise RadioFranceError(f"Invalid RSS XML: {e}") from e

        channel = root.find("channel")
        if channel is None:
            return []

        show_title = ""
        title_el = channel.find("title")
        if title_el is not None and title_el.text:
            show_title = title_el.text

        episodes = []
        for item in channel.findall("item"):
            ep = self._parse_item(item, show_title)
            if ep:
                episodes.append(ep)

        return episodes

    def _parse_item(self, item: ElementTree.Element, show_title: str) -> Episode | None:
        """Parse a single RSS <item> into an Episode."""
        title_el = item.find("title")
        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        if not title:
            return None

        desc_el = item.find("description")
        description = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

        guid_el = item.find("guid")
        ep_id = guid_el.text.strip() if guid_el is not None and guid_el.text else title

        link_el = item.find("link")
        page_url = link_el.text.strip() if link_el is not None and link_el.text else ""

        # Audio URL from enclosure
        audio_url = ""
        enclosure = item.find("enclosure")
        if enclosure is not None:
            audio_url = enclosure.get("url", "")

        # Published date
        published_at = None
        pub_date_el = item.find("pubDate")
        if pub_date_el is not None and pub_date_el.text:
            try:
                published_at = parsedate_to_datetime(pub_date_el.text.strip())
            except (ValueError, TypeError):
                pass

        # Duration from itunes:duration
        duration = 0
        dur_el = item.find(f"{{{ITUNES_NS}}}duration")
        if dur_el is not None and dur_el.text:
            duration = self._parse_duration(dur_el.text.strip())

        # Image
        image_url = ""
        img_el = item.find(f"{{{ITUNES_NS}}}image")
        if img_el is not None:
            image_url = img_el.get("href", "")

        return Episode(
            id=ep_id,
            title=title,
            description=description,
            show_title=show_title,
            published_at=published_at,
            duration=duration,
            audio_url=audio_url,
            page_url=page_url,
            image_url=image_url,
        )

    @staticmethod
    def _parse_duration(text: str) -> int:
        """Parse duration text to seconds. Handles HH:MM:SS, MM:SS, or raw seconds."""
        if ":" in text:
            parts = text.split(":")
            if len(parts) == 3:
                h, m, s = (int(p) for p in parts)
                return h * 3600 + m * 60 + s
            elif len(parts) == 2:
                m, s = (int(p) for p in parts)
                return m * 60 + s
        try:
            return int(text)
        except ValueError:
            return 0

    @staticmethod
    def build_aerion_url(show_id: str) -> str:
        """Build RSS feed URL via the Aerion proxy."""
        return AERION_URL.format(show_id=show_id)
