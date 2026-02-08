"""Configuration management for radiofrance-downloader."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from radiofrance_downloader.exceptions import ConfigError

CONFIG_DIR = Path.home() / ".config" / "radiofrance-downloader"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Config:
    """Application configuration."""

    api_key: str = ""
    output_dir: str = str(Path.home() / "Podcasts" / "RadioFrance")
    default_station: str = ""

    @classmethod
    def load(cls) -> Config:
        """Load configuration from disk, returning defaults if not found."""
        if not CONFIG_FILE.exists():
            return cls()
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return cls(
                api_key=data.get("api_key", ""),
                output_dir=data.get("output_dir", str(Path.home() / "Podcasts" / "RadioFrance")),
                default_station=data.get("default_station", ""),
            )
        except (json.JSONDecodeError, OSError) as e:
            raise ConfigError(f"Failed to read config: {e}") from e

    def save(self) -> None:
        """Save configuration to disk."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(
                json.dumps(asdict(self), indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as e:
            raise ConfigError(f"Failed to write config: {e}") from e
