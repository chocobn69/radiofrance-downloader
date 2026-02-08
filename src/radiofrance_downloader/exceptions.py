"""Custom exception hierarchy for radiofrance-downloader."""


class RadioFranceError(Exception):
    """Base exception for all radiofrance-downloader errors."""


class APIError(RadioFranceError):
    """Error communicating with the Radio France API."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(APIError):
    """Invalid or missing API key."""

    def __init__(self, message: str = "Invalid or missing API key"):
        super().__init__(message, status_code=401)


class ShowNotFoundError(RadioFranceError):
    """Requested show was not found."""


class EpisodeNotFoundError(RadioFranceError):
    """Requested episode was not found."""


class DownloadError(RadioFranceError):
    """Error downloading an episode file."""


class ScrapingError(RadioFranceError):
    """Error scraping a web page."""


class ConfigError(RadioFranceError):
    """Error reading or writing configuration."""
