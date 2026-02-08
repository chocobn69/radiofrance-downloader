"""Tests for the Radio France API client."""

from __future__ import annotations

import pytest
import responses as rsps

from radiofrance_downloader.api import BASE_URL, STATIONS, RadioFranceAPI
from radiofrance_downloader.exceptions import AuthenticationError, ShowNotFoundError
from radiofrance_downloader.models import StationId


@pytest.fixture
def api() -> RadioFranceAPI:
    return RadioFranceAPI(api_key="test-key-123")


class TestRadioFranceAPI:
    def test_search_shows(self, api, api_search_response):
        rsps.get(
            f"{BASE_URL}/stations/search",
            json=api_search_response,
            status=200,
        )

        shows = api.search_shows("meurice")
        assert len(shows) == 2
        assert shows[0].id == "1234"
        assert shows[0].title == "Le Billet de Guillaume Meurice"
        assert shows[0].station is not None
        assert shows[0].station.id == StationId.FRANCE_INTER

    def test_search_shows_empty(self, api):
        rsps.get(
            f"{BASE_URL}/stations/search",
            json={"data": [], "included": [], "meta": {"total": 0}},
            status=200,
        )

        shows = api.search_shows("nonexistent")
        assert shows == []

    def test_get_show_episodes(self, api, api_diffusions_response):
        rsps.get(
            f"{BASE_URL}/shows/1234/diffusions",
            json=api_diffusions_response,
            status=200,
        )

        episodes, next_page = api.get_show_episodes("1234")
        assert len(episodes) == 2
        assert episodes[0].id == "diff-001"
        assert episodes[0].title == "Épisode du 15 janvier 2025"
        assert episodes[0].audio_url.endswith(".mp3")
        assert episodes[0].duration == 180
        assert episodes[0].show_title == "Le Billet de Guillaume Meurice"
        assert next_page == 2

    def test_get_show_episodes_no_next(self, api):
        rsps.get(
            f"{BASE_URL}/shows/1234/diffusions",
            json={"data": [], "included": [], "meta": {"total": 0}},
            status=200,
        )

        episodes, next_page = api.get_show_episodes("1234")
        assert episodes == []
        assert next_page is None

    def test_authentication_error(self, api):
        rsps.get(
            f"{BASE_URL}/stations/search",
            json={"error": "Unauthorized"},
            status=401,
        )

        with pytest.raises(AuthenticationError):
            api.search_shows("test")

    def test_show_not_found(self, api):
        rsps.get(
            f"{BASE_URL}/shows/9999",
            json={"error": "Not found"},
            status=404,
        )

        with pytest.raises(ShowNotFoundError):
            api.get_show_details("9999")

    def test_stations_dict(self):
        assert StationId.FRANCE_INTER in STATIONS
        assert STATIONS[StationId.FRANCE_INTER].name == "France Inter"
        assert len(STATIONS) == 7

    def test_get_show_details(self, api):
        rsps.get(
            f"{BASE_URL}/shows/1234",
            json={
                "data": {
                    "id": "1234",
                    "type": "shows",
                    "attributes": {
                        "title": "Test Show",
                        "description": "A test show",
                        "path": "/franceinter/podcasts/test-show",
                        "visual": {"src": "https://example.com/img.jpg"},
                    },
                    "relationships": {
                        "station": {"data": {"id": "1", "type": "stations"}}
                    },
                }
            },
            status=200,
        )

        show = api.get_show_details("1234")
        assert show.id == "1234"
        assert show.title == "Test Show"
        assert show.station is not None
        assert show.station.id == StationId.FRANCE_INTER
