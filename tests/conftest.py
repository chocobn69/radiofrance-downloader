"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import responses as rsps

from radiofrance_downloader.models import Episode, Show, Station, StationId

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _block_http():
    """Block all unmocked HTTP requests in every test."""
    rsps.start()
    yield
    rsps.stop()
    rsps.reset()


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def sample_station() -> Station:
    return Station(
        id=StationId.FRANCE_INTER,
        name="France Inter",
        url="https://www.radiofrance.fr/franceinter",
    )


@pytest.fixture
def sample_show(sample_station: Station) -> Show:
    return Show(
        id="1234",
        title="Le Billet de Guillaume Meurice",
        description="Le billet d'humeur de Guillaume Meurice",
        url="https://www.radiofrance.fr/franceinter/podcasts/le-billet-de-guillaume-meurice",
        station=sample_station,
        image_url="https://example.com/image.jpg",
    )


@pytest.fixture
def sample_episode() -> Episode:
    from datetime import datetime

    return Episode(
        id="ep-001",
        title="Épisode du 15 janvier 2025",
        description="Un épisode formidable",
        show_id="1234",
        show_title="Le Billet de Guillaume Meurice",
        published_at=datetime(2025, 1, 15, 8, 0),
        duration=180,
        audio_url="https://media.radiofrance-podcast.net/podcast09/test.mp3",
        page_url="https://www.radiofrance.fr/franceinter/podcasts/test/episode-1",
        image_url="https://example.com/ep-image.jpg",
    )


@pytest.fixture
def api_search_response(fixtures_dir: Path) -> dict:
    return json.loads((fixtures_dir / "api_search_response.json").read_text())


@pytest.fixture
def api_diffusions_response(fixtures_dir: Path) -> dict:
    return json.loads((fixtures_dir / "api_diffusions_response.json").read_text())
