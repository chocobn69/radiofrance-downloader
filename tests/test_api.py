"""Tests for the Radio France GraphQL API client."""

from __future__ import annotations

import pytest
import responses as rsps

from radiofrance_downloader.api import GRAPHQL_URL, STATIONS, RadioFranceAPI
from radiofrance_downloader.exceptions import APIError, AuthenticationError, ShowNotFoundError
from radiofrance_downloader.models import StationId


@pytest.fixture
def api() -> RadioFranceAPI:
    return RadioFranceAPI(api_key="test-key-123")


def _mock_graphql(json_response: dict, status: int = 200) -> None:
    """Register a mock for the GraphQL endpoint."""
    rsps.post(GRAPHQL_URL, json=json_response, status=status)


class TestRadioFranceAPI:
    def test_get_station_shows(self, api, api_search_response):
        _mock_graphql(api_search_response)

        shows = api.get_station_shows(StationId.FRANCE_INTER)
        assert len(shows) == 2
        assert shows[0].id == "1234"
        assert shows[0].title == "Le Billet de Guillaume Meurice"
        assert shows[0].station is not None
        assert shows[0].station.id == StationId.FRANCE_INTER

    def test_get_station_shows_empty(self, api):
        _mock_graphql({"data": {"shows": {"edges": []}}})

        shows = api.get_station_shows(StationId.FRANCE_INTER)
        assert shows == []

    def test_get_show_episodes(self, api, api_diffusions_response):
        _mock_graphql(api_diffusions_response)

        episodes, next_cursor = api.get_show_episodes(
            "/franceinter/podcasts/le-billet-de-guillaume-meurice"
        )
        assert len(episodes) == 2
        assert episodes[0].id == "diff-001"
        assert episodes[0].title == "Épisode du 15 janvier 2025"
        assert episodes[0].audio_url.endswith(".mp3")
        assert episodes[0].duration == 180
        assert episodes[0].show_title == "Le Billet de Guillaume Meurice"
        assert next_cursor == "cursor-ep2"

    def test_get_show_episodes_empty(self, api):
        _mock_graphql({"data": {"diffusionsOfShowByUrl": {"edges": []}}})

        episodes, next_cursor = api.get_show_episodes("/some/show")
        assert episodes == []
        assert next_cursor is None

    def test_authentication_error(self, api):
        _mock_graphql({"error": "Unauthorized"}, status=401)

        with pytest.raises(AuthenticationError):
            api.get_station_shows(StationId.FRANCE_INTER)

    def test_graphql_error(self, api):
        _mock_graphql({"errors": [{"message": "Something went wrong"}]})

        with pytest.raises(APIError, match="GraphQL error"):
            api.get_station_shows(StationId.FRANCE_INTER)

    def test_show_not_found_via_graphql_error(self, api):
        _mock_graphql({"errors": [{"message": "Show not found"}]})

        with pytest.raises(ShowNotFoundError):
            api.get_show_details("/nonexistent/show")

    def test_show_not_found_empty_response(self, api):
        _mock_graphql({"data": {"showByUrl": None}})

        with pytest.raises(ShowNotFoundError):
            api.get_show_details("/nonexistent/show")

    def test_stations_dict(self):
        assert StationId.FRANCE_INTER in STATIONS
        assert STATIONS[StationId.FRANCE_INTER].name == "France Inter"
        assert len(STATIONS) == 7

    def test_station_ids_are_graphql_brand_ids(self):
        assert StationId.FRANCE_INTER.value == "FRANCEINTER"
        assert StationId.FRANCE_INFO.value == "FRANCEINFO"
        assert StationId.FRANCE_CULTURE.value == "FRANCECULTURE"
        assert StationId.FIP.value == "FIP"

    def test_get_show_details(self, api):
        _mock_graphql({
            "data": {
                "showByUrl": {
                    "id": "1234",
                    "title": "Test Show",
                    "standFirst": "A test show",
                    "url": "https://www.franceinter.fr/franceinter/podcasts/test-show",
                    "podcast": {"rss": "http://example.com/rss.xml", "itunes": None},
                }
            }
        })

        show = api.get_show_details("/franceinter/podcasts/test-show")
        assert show.id == "1234"
        assert show.title == "Test Show"
        assert show.station is not None
        assert show.station.id == StationId.FRANCE_INTER

    def test_get_show_episodes_pagination(self, api, api_diffusions_response):
        """Test that fetch_all follows cursors."""
        # First page returns episodes with cursor
        _mock_graphql(api_diffusions_response)
        # Second page returns empty (end of results)
        _mock_graphql({"data": {"diffusionsOfShowByUrl": {"edges": []}}})

        episodes, next_cursor = api.get_show_episodes(
            "/franceinter/podcasts/test", fetch_all=True
        )
        assert len(episodes) == 2
        assert next_cursor is None
