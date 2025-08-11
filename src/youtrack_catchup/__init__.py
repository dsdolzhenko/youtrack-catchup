"""YouTrack Catchup - A tool to quickly catch up on YouTrack issues."""

from .api_client import YouTrackClient, YouTrackAPIError
from .config import Config

__version__ = "0.1.0"
__all__ = ["YouTrackClient", "YouTrackAPIError", "Config"]
