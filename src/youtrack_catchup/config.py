"""Configuration management for YouTrack Catchup."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class Config:
    """Configuration for YouTrack API client."""

    def __init__(self, env_file: Optional[Path] = None):
        """Initialize configuration from environment variables.

        Args:
            env_file: Optional path to .env file. If not provided,
                     will look for .env in the current directory.
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        self.base_url = self._get_required_env("YOUTRACK_URL")
        self.token = self._get_required_env("YOUTRACK_TOKEN")

        # API defaults
        self.default_page_size = 50
        self.max_page_size = 100

    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error.

        Args:
            key: Environment variable name

        Returns:
            Environment variable value

        Raises:
            ValueError: If environment variable is not set
        """
        value = os.getenv(key)
        if not value:
            raise ValueError(
                f"Required environment variable {key} is not set. "
                f"Please check your .env file or environment configuration."
            )
        return value.rstrip("/")  # Remove trailing slash if present for URLs

    @property
    def api_base_url(self) -> str:
        """Get the base URL for API requests."""
        return f"{self.base_url}/api"

    @property
    def headers(self) -> dict:
        """Get default headers for API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        }
