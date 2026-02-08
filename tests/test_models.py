"""Tests for data models."""

from datetime import datetime

from radiofrance_downloader.models import (
    DownloadResult,
    Episode,
    Show,
    StationId,
)


class TestStationId:
    def test_values(self):
        assert StationId.FRANCE_INTER == "1"
        assert StationId.FRANCE_CULTURE == "4"

    def test_str(self):
        assert str(StationId.FRANCE_INTER) == "1"


class TestStation:
    def test_frozen(self, sample_station):
        import pytest

        with pytest.raises(AttributeError):
            sample_station.name = "other"

    def test_fields(self, sample_station):
        assert sample_station.id == StationId.FRANCE_INTER
        assert sample_station.name == "France Inter"


class TestShow:
    def test_creation(self, sample_show):
        assert sample_show.id == "1234"
        assert sample_show.title == "Le Billet de Guillaume Meurice"
        assert sample_show.station is not None
        assert sample_show.station.name == "France Inter"

    def test_defaults(self):
        show = Show(id="1", title="Test")
        assert show.description == ""
        assert show.station is None


class TestEpisode:
    def test_creation(self, sample_episode):
        assert sample_episode.id == "ep-001"
        assert sample_episode.duration == 180
        assert sample_episode.published_at == datetime(2025, 1, 15, 8, 0)

    def test_defaults(self):
        ep = Episode(id="1", title="Test")
        assert ep.audio_url == ""
        assert ep.published_at is None


class TestDownloadResult:
    def test_success(self, sample_episode, tmp_path):
        result = DownloadResult(
            episode=sample_episode,
            file_path=tmp_path / "test.mp3",
            file_size=1024,
            success=True,
        )
        assert result.success
        assert result.file_size == 1024

    def test_failure(self, sample_episode):
        result = DownloadResult(
            episode=sample_episode,
            error="Connection refused",
        )
        assert not result.success
        assert result.error == "Connection refused"
