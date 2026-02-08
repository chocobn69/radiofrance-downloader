"""Tests for the CLI interface."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import responses as rsps
from click.testing import CliRunner

from radiofrance_downloader.api import BASE_URL
from radiofrance_downloader.cli import main
from radiofrance_downloader.config import Config
from radiofrance_downloader.models import DownloadResult


class _NoOpProgress:
    """Dummy Progress replacement that does nothing (no threads)."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def add_task(self, *args, **kwargs):
        return 0

    def update(self, *args, **kwargs):
        pass


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_config():
    """Mock config that returns a config with a test API key."""
    config = Config(api_key="test-key-123", output_dir="/tmp/test-podcasts")
    with patch("radiofrance_downloader.cli.Config.load", return_value=config):
        yield config


@pytest.fixture
def mock_config_no_key():
    """Mock config with no API key."""
    config = Config(api_key="", output_dir="/tmp/test-podcasts")
    with patch("radiofrance_downloader.cli.Config.load", return_value=config):
        yield config


class TestCLI:
    def test_version(self, runner, mock_config):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self, runner, mock_config):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Download Radio France podcasts" in result.output

    def test_list_stations(self, runner, mock_config):
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "France Inter" in result.output
        assert "France Culture" in result.output
        assert "FIP" in result.output

    def test_search(self, runner, mock_config, api_search_response):
        rsps.get(
            f"{BASE_URL}/stations/search",
            json=api_search_response,
            status=200,
        )

        result = runner.invoke(main, ["search", "meurice"])
        assert result.exit_code == 0
        assert "Guillaume Meurice" in result.output

    def test_search_no_results(self, runner, mock_config):
        rsps.get(
            f"{BASE_URL}/stations/search",
            json={"data": [], "included": [], "meta": {"total": 0}},
            status=200,
        )

        result = runner.invoke(main, ["search", "zzzznonexistent"])
        assert result.exit_code == 0
        assert "No shows found" in result.output

    def test_search_no_api_key(self, runner, mock_config_no_key):
        result = runner.invoke(main, ["search", "test"])
        assert result.exit_code != 0
        assert "API key" in result.output

    def test_episodes(self, runner, mock_config, api_diffusions_response):
        rsps.get(
            f"{BASE_URL}/shows/1234/diffusions",
            json=api_diffusions_response,
            status=200,
        )

        result = runner.invoke(main, ["episodes", "1234"])
        assert result.exit_code == 0
        assert "15 janvier" in result.output

    def test_download_latest(self, runner, mock_config, api_diffusions_response, tmp_path):
        rsps.get(
            f"{BASE_URL}/shows/1234/diffusions",
            json=api_diffusions_response,
            status=200,
        )

        fake_file = tmp_path / "test.mp3"
        fake_file.write_bytes(b"fake mp3")

        def mock_download(episode, progress_callback=None):
            return DownloadResult(
                episode=episode,
                file_path=fake_file,
                file_size=8,
                success=True,
            )

        with (
            patch(
                "radiofrance_downloader.cli.EpisodeDownloader.download_episode",
                side_effect=mock_download,
            ),
            patch("radiofrance_downloader.cli.Progress", _NoOpProgress),
        ):
            result = runner.invoke(
                main,
                ["download", "1234", "--latest", "1", "-o", str(tmp_path)],
            )
        assert result.exit_code == 0


class TestConfigCommands:
    def test_config_show(self, runner, mock_config):
        result = runner.invoke(main, ["config", "show"])
        assert result.exit_code == 0
        assert "test-key" in result.output

    def test_config_set_api_key(self, runner):
        with patch("radiofrance_downloader.cli.Config.load", return_value=Config()):
            with patch.object(Config, "save"):
                result = runner.invoke(main, ["config", "set-api-key", "new-key"])
                assert result.exit_code == 0
                assert "saved" in result.output
