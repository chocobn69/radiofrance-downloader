"""Radio France REST API client."""

from __future__ import annotations

from datetime import UTC, datetime

import requests

from radiofrance_downloader.exceptions import (
    APIError,
    AuthenticationError,
    ShowNotFoundError,
)
from radiofrance_downloader.models import Episode, Show, Station, StationId

BASE_URL = "https://api.radiofrance.fr/v1"

STATIONS: dict[StationId, Station] = {
    StationId.FRANCE_INTER: Station(
        id=StationId.FRANCE_INTER,
        name="France Inter",
        url="https://www.radiofrance.fr/franceinter",
    ),
    StationId.FRANCE_INFO: Station(
        id=StationId.FRANCE_INFO,
        name="franceinfo",
        url="https://www.radiofrance.fr/franceinfo",
    ),
    StationId.FRANCE_BLEU: Station(
        id=StationId.FRANCE_BLEU,
        name="France Bleu",
        url="https://www.radiofrance.fr/francebleu",
    ),
    StationId.FRANCE_CULTURE: Station(
        id=StationId.FRANCE_CULTURE,
        name="France Culture",
        url="https://www.radiofrance.fr/franceculture",
    ),
    StationId.FRANCE_MUSIQUE: Station(
        id=StationId.FRANCE_MUSIQUE,
        name="France Musique",
        url="https://www.radiofrance.fr/francemusique",
    ),
    StationId.MOUV: Station(
        id=StationId.MOUV,
        name="Mouv'",
        url="https://www.radiofrance.fr/mouv",
    ),
    StationId.FIP: Station(
        id=StationId.FIP,
        name="FIP",
        url="https://www.radiofrance.fr/fip",
    ),
}


class RadioFranceAPI:
    """Client for the Radio France REST API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "x-token": api_key,
                "Accept": "application/x.radiofrance.mobileapi+json",
            }
        )

    def _get(self, path: str, params: dict | None = None) -> dict:
        """Make an authenticated GET request."""
        url = f"{BASE_URL}{path}"
        try:
            resp = self.session.get(url, params=params, timeout=30)
        except requests.RequestException as e:
            raise APIError(f"Request failed: {e}") from e

        if resp.status_code == 401:
            raise AuthenticationError()
        if resp.status_code == 404:
            raise ShowNotFoundError(f"Not found: {path}")
        if resp.status_code >= 400:
            raise APIError(f"API error {resp.status_code}: {resp.text}", resp.status_code)

        return resp.json()

    def search_shows(self, query: str) -> list[Show]:
        """Search for shows by name."""
        data = self._get("/stations/search", params={"value": query, "include": "show"})
        return self._parse_shows(data)

    def get_show_episodes(
        self,
        show_id: str,
        page: int = 0,
        fetch_all: bool = False,
    ) -> tuple[list[Episode], int | None]:
        """Get episodes for a show. Returns (episodes, next_page)."""
        all_episodes: list[Episode] = []
        current_page = page

        while True:
            params: dict = {
                "filter[manifestations][exists]": "true",
                "include": "show,manifestations",
                "page[offset]": str(current_page),
            }
            data = self._get(f"/shows/{show_id}/diffusions", params=params)
            episodes, next_page = self._parse_episodes(data)
            all_episodes.extend(episodes)

            if not fetch_all or next_page is None:
                return all_episodes, next_page

            current_page = next_page

    def get_show_details(self, show_id: str) -> Show:
        """Get details for a single show."""
        data = self._get(f"/shows/{show_id}")
        attrs = data.get("data", {}).get("attributes", {})
        station_data = (
            data.get("data", {}).get("relationships", {}).get("station", {}).get("data", {})
        )
        station = STATIONS.get(StationId(station_data["id"])) if station_data.get("id") else None

        path = attrs.get("path", "")
        url = f"https://www.radiofrance.fr{path}" if path else ""

        return Show(
            id=show_id,
            title=attrs.get("title", ""),
            description=attrs.get("description", ""),
            url=url,
            station=station,
            image_url=attrs.get("visual", {}).get("src", ""),
        )

    def _parse_shows(self, data: dict) -> list[Show]:
        """Parse show list from API response."""
        shows = []
        for item in data.get("data", []):
            if item.get("type") != "shows":
                continue
            attrs = item.get("attributes", {})
            station_ref = (
                item.get("relationships", {}).get("station", {}).get("data", {}).get("id")
            )
            station = None
            if station_ref:
                try:
                    station = STATIONS.get(StationId(station_ref))
                except ValueError:
                    pass

            path = attrs.get("path", "")
            url = f"https://www.radiofrance.fr{path}" if path else ""

            shows.append(
                Show(
                    id=item["id"],
                    title=attrs.get("title", ""),
                    description=attrs.get("description", ""),
                    url=url,
                    station=station,
                    image_url=attrs.get("visual", {}).get("src", ""),
                )
            )
        return shows

    def _parse_episodes(self, data: dict) -> tuple[list[Episode], int | None]:
        """Parse episode list from API response with manifestations."""
        # Build lookup for included resources
        included_by_type: dict[str, dict[str, dict]] = {}
        for item in data.get("included", []):
            included_by_type.setdefault(item["type"], {})[item["id"]] = item

        manifestations = included_by_type.get("manifestations", {})
        shows = included_by_type.get("shows", {})

        episodes = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            rels = item.get("relationships", {})

            # Get show info
            show_ref = rels.get("show", {}).get("data", {})
            show_id = show_ref.get("id", "")
            show_data = shows.get(show_id, {})
            show_title = show_data.get("attributes", {}).get("title", "")

            # Get manifestation (audio file)
            manif_refs = rels.get("manifestations", {}).get("data", [])
            audio_url = ""
            duration = 0
            if manif_refs:
                manif = manifestations.get(manif_refs[0].get("id", ""), {})
                manif_attrs = manif.get("attributes", {})
                audio_url = manif_attrs.get("url", "")
                duration = manif_attrs.get("duration", 0)

            # Parse published date
            published_at = None
            ts = attrs.get("publishedDate")
            if ts:
                published_at = datetime.fromtimestamp(ts, tz=UTC)

            path = attrs.get("path", "")
            page_url = f"https://www.radiofrance.fr{path}" if path else ""

            episodes.append(
                Episode(
                    id=item["id"],
                    title=attrs.get("title", ""),
                    description=attrs.get("standFirst", ""),
                    show_id=show_id,
                    show_title=show_title,
                    published_at=published_at,
                    duration=duration,
                    audio_url=audio_url,
                    page_url=page_url,
                )
            )

        # Determine next page
        next_page = None
        next_link = data.get("links", {}).get("next")
        if next_link:
            # Extract offset from next link
            import re

            match = re.search(r"page\[offset\]=(\d+)", next_link)
            if match:
                next_page = int(match.group(1))

        return episodes, next_page
