"""Radio France GraphQL API client."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import requests

from radiofrance_downloader.exceptions import (
    APIError,
    AuthenticationError,
    ShowNotFoundError,
)
from radiofrance_downloader.models import Episode, Show, Station, StationId

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://openapi.radiofrance.fr/v1/graphql"

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

# Map from URL slug to StationId for reverse lookup
_SLUG_TO_STATION: dict[str, StationId] = {
    "franceinter": StationId.FRANCE_INTER,
    "franceinfo": StationId.FRANCE_INFO,
    "francebleu": StationId.FRANCE_BLEU,
    "franceculture": StationId.FRANCE_CULTURE,
    "francemusique": StationId.FRANCE_MUSIQUE,
    "mouv": StationId.MOUV,
    "fip": StationId.FIP,
}


class RadioFranceAPI:
    """Client for the Radio France GraphQL API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "x-token": api_key,
                "Content-Type": "application/json",
            }
        )

    def _query(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query."""
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables

        logger.debug("GraphQL POST %s", GRAPHQL_URL)
        logger.debug("Query: %s", query.strip()[:200])
        logger.debug("Variables: %s", variables)

        try:
            resp = self.session.post(GRAPHQL_URL, json=payload, timeout=30)
        except requests.RequestException as e:
            raise APIError(f"Request failed: {e}") from e

        logger.debug("Response %s: %s", resp.status_code, resp.text[:500])

        if resp.status_code == 401:
            raise AuthenticationError(
                f"Authentication failed (HTTP {resp.status_code}): "
                f"{resp.text[:200]}"
            )
        if resp.status_code >= 400:
            raise APIError(
                f"API error {resp.status_code}: {resp.text}",
                resp.status_code,
            )

        data = resp.json()

        # GraphQL can return errors even with 200 status
        if "errors" in data:
            errors = data["errors"]
            msg = (
                errors[0].get("message", str(errors))
                if errors else str(errors)
            )
            if "not found" in msg.lower():
                raise ShowNotFoundError(msg)
            raise APIError(f"GraphQL error: {msg}")

        return data.get("data", {})

    def search_shows(
        self, query: str, station: StationId | None = None,
    ) -> list[Show]:
        """Search for shows, optionally filtered by station.

        The GraphQL API has no text search — we list shows per station
        and filter client-side.
        """
        q = query.lower()
        stations = [station] if station else list(STATIONS)

        all_shows: list[Show] = []
        for station_id in stations:
            try:
                shows = self.get_all_station_shows(station_id)
                for show in shows:
                    title = show.title.lower()
                    desc = (show.description or "").lower()
                    if q in title or q in desc:
                        all_shows.append(show)
            except APIError:
                continue
        return all_shows

    def get_all_station_shows(
        self,
        station: StationId,
    ) -> list[Show]:
        """Get all shows for a station, paginating automatically."""
        all_shows: list[Show] = []
        after: str | None = None
        while True:
            shows, last_cursor = self._fetch_station_shows_page(
                station, first=100, after=after,
            )
            all_shows.extend(shows)
            if not last_cursor or len(shows) < 100:
                break
            after = last_cursor
        return all_shows

    def get_station_shows(
        self,
        station: StationId,
        first: int = 100,
        after: str | None = None,
    ) -> list[Show]:
        """Get one page of shows for a station."""
        shows, _ = self._fetch_station_shows_page(
            station, first=first, after=after,
        )
        return shows

    def _fetch_station_shows_page(
        self,
        station: StationId,
        first: int = 100,
        after: str | None = None,
    ) -> tuple[list[Show], str | None]:
        """Fetch a single page of shows. Returns (shows, last_cursor)."""
        gql = """
        query GetShows($station: StationsEnum!, $first: Int!, $after: String) {
            shows(station: $station, first: $first, after: $after) {
                edges {
                    cursor
                    node {
                        id
                        title
                        url
                        standFirst
                    }
                }
            }
        }
        """
        variables: dict = {"station": station.value, "first": first}
        if after:
            variables["after"] = after

        data = self._query(gql, variables)
        shows_data = data.get("shows", {})
        edges = shows_data.get("edges", [])

        shows = []
        last_cursor = None
        for edge in edges:
            node = edge.get("node", {})
            last_cursor = edge.get("cursor")
            station_obj = STATIONS.get(station)

            shows.append(
                Show(
                    id=node.get("id", ""),
                    title=node.get("title", ""),
                    description=node.get("standFirst", ""),
                    url=node.get("url", ""),
                    station=station_obj,
                )
            )
        return shows, last_cursor

    def get_show_episodes(
        self,
        show_url: str,
        first: int = 20,
        after: str | None = None,
        fetch_all: bool = False,
    ) -> tuple[list[Episode], str | None]:
        """Get episodes for a show by its URL.

        Returns (episodes, next_cursor).
        """
        gql = """
        query GetDiffusions($url: String!, $first: Int!, $after: String) {
            diffusionsOfShowByUrl(url: $url, first: $first, after: $after) {
                edges {
                    cursor
                    node {
                        id
                        title
                        standFirst
                        published_date
                        url
                        podcastEpisode {
                            url
                            duration
                        }
                        show {
                            id
                            title
                        }
                    }
                }
            }
        }
        """
        all_episodes: list[Episode] = []
        current_after = after

        while True:
            variables: dict = {"url": show_url, "first": first}
            if current_after:
                variables["after"] = current_after

            data = self._query(gql, variables)
            diffusions = data.get("diffusionsOfShowByUrl", {})
            edges = diffusions.get("edges", [])

            if not edges:
                return all_episodes, None

            next_cursor = None
            for edge in edges:
                node = edge.get("node", {})
                next_cursor = edge.get("cursor")

                show_data = node.get("show") or {}
                podcast = node.get("podcastEpisode") or {}

                # published_date is a String timestamp from the API
                published_at = None
                ts = node.get("published_date")
                if ts:
                    published_at = datetime.fromtimestamp(
                        int(ts), tz=UTC,
                    )

                all_episodes.append(
                    Episode(
                        id=node.get("id", ""),
                        title=node.get("title", ""),
                        description=node.get("standFirst", ""),
                        show_id=show_data.get("id", ""),
                        show_title=show_data.get("title", ""),
                        published_at=published_at,
                        duration=podcast.get("duration", 0) or 0,
                        audio_url=podcast.get("url", ""),
                        page_url=node.get("url", ""),
                    )
                )

            if not fetch_all or not next_cursor:
                return all_episodes, next_cursor

            current_after = next_cursor

    def get_show_details(self, show_url: str) -> Show:
        """Get details for a show by its URL."""
        gql = """
        query GetShow($url: String!) {
            showByUrl(url: $url) {
                id
                title
                standFirst
                url
                podcast {
                    rss
                    itunes
                }
            }
        }
        """
        data = self._query(gql, {"url": show_url})
        show_data = data.get("showByUrl")

        if not show_data:
            raise ShowNotFoundError(f"Show not found: {show_url}")

        show_full_url = show_data.get("url", "")
        station = self._station_from_url(show_full_url)

        return Show(
            id=show_data.get("id", ""),
            title=show_data.get("title", ""),
            description=show_data.get("standFirst", ""),
            url=show_full_url,
            station=station,
        )

    @staticmethod
    def _station_from_url(url: str) -> Station | None:
        """Try to determine the station from a show URL."""
        for slug, station_id in _SLUG_TO_STATION.items():
            if f"/{slug}/" in url or url.endswith(f"/{slug}"):
                return STATIONS.get(station_id)
        return None
