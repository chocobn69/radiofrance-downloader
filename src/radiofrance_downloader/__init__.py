"""radiofrance-downloader — Download Radio France podcasts."""

__version__ = "0.1.0"

from radiofrance_downloader.models import (
    DownloadResult,
    Episode,
    Show,
    Station,
    StationId,
)

__all__ = [
    "DownloadResult",
    "Episode",
    "Show",
    "Station",
    "StationId",
    "__version__",
]
