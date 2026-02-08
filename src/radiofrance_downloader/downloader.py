"""MP3 download engine with progress callbacks."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from pathlib import Path

import requests

from radiofrance_downloader.exceptions import DownloadError
from radiofrance_downloader.models import DownloadResult, Episode

DEFAULT_CHUNK_SIZE = 8192


def sanitize_filename(name: str) -> str:
    """Convert a string into a safe filename."""
    # Normalize unicode characters
    name = unicodedata.normalize("NFKD", name)
    # Replace common separators with hyphens
    name = re.sub(r"[\s/\\:]+", "-", name)
    # Remove characters not allowed in filenames
    name = re.sub(r"[^\w\-.]", "", name)
    # Collapse multiple hyphens
    name = re.sub(r"-{2,}", "-", name)
    # Strip leading/trailing hyphens and dots
    name = name.strip("-.")
    return name[:200] if name else "episode"


class EpisodeDownloader:
    """Downloads podcast episodes to disk."""

    def __init__(
        self,
        output_dir: str | Path,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ):
        self.output_dir = Path(output_dir)
        self.chunk_size = chunk_size

    def _build_filepath(self, episode: Episode) -> Path:
        """Build the destination file path for an episode."""
        show_dir_name = sanitize_filename(episode.show_title) if episode.show_title else "unknown"
        show_dir = self.output_dir / show_dir_name
        show_dir.mkdir(parents=True, exist_ok=True)

        date_prefix = ""
        if episode.published_at:
            date_prefix = episode.published_at.strftime("%Y-%m-%d") + "_"

        title_part = sanitize_filename(episode.title)
        filename = f"{date_prefix}{title_part}.mp3"

        return show_dir / filename

    def download_episode(
        self,
        episode: Episode,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> DownloadResult:
        """Download a single episode. Skips if file already exists."""
        if not episode.audio_url:
            return DownloadResult(
                episode=episode,
                error="No audio URL available",
            )

        file_path = self._build_filepath(episode)

        # Skip if already downloaded
        if file_path.exists():
            return DownloadResult(
                episode=episode,
                file_path=file_path,
                file_size=file_path.stat().st_size,
                already_existed=True,
                success=True,
            )

        try:
            resp = requests.get(episode.audio_url, stream=True, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise DownloadError(f"Failed to download {episode.audio_url}: {e}") from e

        total_size = int(resp.headers.get("content-length", 0))
        downloaded = 0

        try:
            with open(file_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=self.chunk_size):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)
        except OSError as e:
            # Clean up partial file
            file_path.unlink(missing_ok=True)
            raise DownloadError(f"Failed to write {file_path}: {e}") from e

        return DownloadResult(
            episode=episode,
            file_path=file_path,
            file_size=downloaded,
            success=True,
        )
