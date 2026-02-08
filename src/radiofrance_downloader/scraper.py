"""Web scraping fallback for Radio France shows."""

from __future__ import annotations

import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from radiofrance_downloader.exceptions import ScrapingError
from radiofrance_downloader.models import Episode

RADIOFRANCE_BASE = "https://www.radiofrance.fr"


class RadioFranceScraper:
    """Scrapes Radio France website for episode data."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
                    "Gecko/20100101 Firefox/128.0"
                ),
            }
        )

    def get_episodes(self, station: str, show_slug: str) -> list[Episode]:
        """Get episodes from a show page."""
        url = f"{RADIOFRANCE_BASE}/{station}/podcasts/{show_slug}"
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise ScrapingError(f"Failed to fetch {url}: {e}") from e

        return self._parse_show_page(resp.text, show_slug)

    def get_episode_audio_url(self, episode_url: str) -> str:
        """Extract audio URL from an episode page."""
        if not episode_url.startswith("http"):
            episode_url = f"{RADIOFRANCE_BASE}{episode_url}"

        try:
            resp = self.session.get(episode_url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise ScrapingError(f"Failed to fetch {episode_url}: {e}") from e

        return self._extract_audio_url(resp.text)

    def _parse_show_page(self, html: str, show_slug: str) -> list[Episode]:
        """Parse episode cards from a show page."""
        soup = BeautifulSoup(html, "html.parser")
        episodes = []

        # Try JSON-LD first
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    for item in data:
                        ep = self._parse_jsonld_episode(item)
                        if ep:
                            episodes.append(ep)
                elif isinstance(data, dict):
                    ep = self._parse_jsonld_episode(data)
                    if ep:
                        episodes.append(ep)
            except (json.JSONDecodeError, KeyError):
                continue

        if episodes:
            return episodes

        # Fallback: parse card elements
        cards = soup.select("a.CardEpisode, [class*='CardEpisode'], article.card")
        for card in cards:
            title_el = card.select_one("h2, h3, .title, [class*='title']")
            title = title_el.get_text(strip=True) if title_el else ""
            link = card.get("href", "")
            if link and not link.startswith("http"):
                link = f"{RADIOFRANCE_BASE}{link}"

            if title:
                episodes.append(
                    Episode(
                        id=link.split("/")[-1] if link else title[:50],
                        title=title,
                        page_url=link,
                        show_title=show_slug,
                    )
                )

        return episodes

    def _parse_jsonld_episode(self, data: dict) -> Episode | None:
        """Parse a single episode from JSON-LD data."""
        if data.get("@type") not in ("PodcastEpisode", "RadioEpisode", "AudioObject"):
            return None

        audio_url = ""
        if "contentUrl" in data:
            audio_url = data["contentUrl"]
        elif "associatedMedia" in data:
            media = data["associatedMedia"]
            if isinstance(media, dict):
                audio_url = media.get("contentUrl", "")

        published_at = None
        date_str = data.get("datePublished", "")
        if date_str:
            try:
                published_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        duration = 0
        dur_str = data.get("duration", "")
        if dur_str:
            # Parse ISO 8601 duration (e.g. PT3M30S)
            match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", dur_str)
            if match:
                h, m, s = (int(x or 0) for x in match.groups())
                duration = h * 3600 + m * 60 + s

        return Episode(
            id=data.get("identifier", data.get("@id", "")),
            title=data.get("name", ""),
            description=data.get("description", ""),
            published_at=published_at,
            duration=duration,
            audio_url=audio_url,
            page_url=data.get("url", ""),
        )

    def _extract_audio_url(self, html: str) -> str:
        """Extract MP3 URL from an episode page."""
        soup = BeautifulSoup(html, "html.parser")

        # Try JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    url = data.get("contentUrl", "")
                    if url and url.endswith(".mp3"):
                        return url
                    media = data.get("associatedMedia", {})
                    if isinstance(media, dict):
                        url = media.get("contentUrl", "")
                        if url:
                            return url
            except (json.JSONDecodeError, KeyError):
                continue

        # Regex fallback for mp3 URLs
        match = re.search(
            r'https?://media\.radiofrance-podcast\.net/[^\s"\'<>]+\.mp3',
            html,
        )
        if match:
            return match.group(0)

        raise ScrapingError("Could not find audio URL on page")
