"""Data models for radiofrance-downloader."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class StationId(StrEnum):
    """Radio France station/brand identifiers (GraphQL API)."""

    FRANCE_INTER = "FRANCEINTER"
    FRANCE_INFO = "FRANCEINFO"
    FRANCE_CULTURE = "FRANCECULTURE"
    FRANCE_MUSIQUE = "FRANCEMUSIQUE"
    FIP = "FIP"
    MOUV = "MOUV"
    FRANCE_BLEU = "FRANCEBLEU"


@dataclass(frozen=True)
class Station:
    """A Radio France station."""

    id: StationId
    name: str
    url: str


@dataclass(frozen=True)
class Show:
    """A podcast show."""

    id: str
    title: str
    description: str = ""
    url: str = ""
    station: Station | None = None
    image_url: str = ""


@dataclass(frozen=True)
class Episode:
    """A single podcast episode."""

    id: str
    title: str
    description: str = ""
    show_id: str = ""
    show_title: str = ""
    published_at: datetime | None = None
    duration: int = 0
    audio_url: str = ""
    page_url: str = ""
    image_url: str = ""


@dataclass
class DownloadResult:
    """Outcome of a download attempt."""

    episode: Episode
    file_path: Path | None = None
    file_size: int = 0
    already_existed: bool = False
    success: bool = False
    error: str = ""
