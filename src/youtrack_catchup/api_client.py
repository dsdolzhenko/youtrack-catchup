"""YouTrack API client for fetching and searching issues."""

import logging
from typing import Optional, List, Dict, Any, Generator
from urllib.parse import urlencode, urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from .config import Config


logger = logging.getLogger(__name__)


class YouTrackAPIError(Exception):
    """Exception raised for YouTrack API errors."""

    pass


class YouTrackClient:
    """Client for interacting with YouTrack REST API."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize YouTrack API client.

        Args:
            config: Optional configuration object. If not provided,
                   will create a new Config instance.
        """
        self.config = config or Config()
        self.session = self._setup_session()

    def _setup_session(self) -> requests.Session:
        """Setup requests session with retry logic and default headers.

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update(self.config.headers)

        return session

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to YouTrack API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body data

        Returns:
            JSON response data

        Raises:
            YouTrackAPIError: If API request fails
        """
        # Ensure endpoint doesn't start with / for proper urljoin behavior
        endpoint = endpoint.lstrip("/")
        url = urljoin(self.config.api_base_url + "/", endpoint)

        logger.debug(f"Making {method} request to: {url}")
        if params:
            logger.debug(f"Query params: {params}")

        try:
            response = self.session.request(
                method=method, url=url, params=params, json=json_data, timeout=30
            )
            response.raise_for_status()

            # Handle empty responses
            if response.status_code == 204 or not response.content:
                return {}

            # Try to parse JSON response
            try:
                return response.json()
            except ValueError as json_error:
                # Log the actual response for debugging
                logger.error(f"Failed to parse JSON response from {url}")
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response headers: {response.headers}")
                logger.error(
                    f"Response content (first 500 chars): {response.text[:500]}"
                )
                raise YouTrackAPIError(
                    f"Invalid JSON response from API. Status: {response.status_code}. "
                    f"This might indicate an authentication issue or incorrect URL."
                ) from json_error

        except requests.exceptions.HTTPError as e:
            error_msg = f"YouTrack API error: {e}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = f"YouTrack API error: {error_data.get('error_description', error_data)}"
                except:
                    error_msg = f"YouTrack API error: {e.response.text}"
            logger.error(error_msg)
            raise YouTrackAPIError(error_msg) from e

        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {e}"
            logger.error(error_msg)
            raise YouTrackAPIError(error_msg) from e

    def _build_fields_param(self, fields: Optional[List[str]] = None) -> Optional[str]:
        """Build fields parameter for API request.

        Args:
            fields: List of fields to include

        Returns:
            Formatted fields parameter string or None
        """
        if fields:
            return ",".join(fields)
        return None

    def _normalize_custom_fields(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize custom fields in issue data for easier access.

        Args:
            issue: Raw issue data from API

        Returns:
            Issue with normalized custom fields
        """
        if "customFields" not in issue:
            return issue

        # Create a copy to avoid modifying the original
        normalized = issue.copy()

        # Extract custom fields into a simpler structure
        custom_fields_map = {}

        for custom_field in issue.get("customFields", []):
            field_name = custom_field.get("name", "")
            field_value = custom_field.get("value")

            if field_value is None:
                custom_fields_map[field_name] = None
            elif isinstance(field_value, dict):
                # Handle different value types
                if "name" in field_value:
                    custom_fields_map[field_name] = field_value["name"]
                elif "login" in field_value:
                    custom_fields_map[field_name] = field_value["login"]
                elif "text" in field_value:
                    custom_fields_map[field_name] = field_value["text"]
                else:
                    # Keep the full object for complex fields
                    custom_fields_map[field_name] = field_value
            elif isinstance(field_value, list):
                # Handle multi-value fields
                values = []
                for item in field_value:
                    if isinstance(item, dict):
                        if "name" in item:
                            values.append(item["name"])
                        elif "login" in item:
                            values.append(item["login"])
                        else:
                            values.append(item)
                    else:
                        values.append(item)
                custom_fields_map[field_name] = values
            else:
                custom_fields_map[field_name] = field_value

        # Add flattened custom fields to the issue
        normalized["custom_fields"] = custom_fields_map

        # Also keep original customFields for reference if needed
        normalized["_raw_custom_fields"] = issue.get("customFields", [])

        return normalized

    def search_issues(
        self,
        query: str = "",
        fields: Optional[List[str]] = None,
        skip: int = 0,
        top: Optional[int] = None,
        normalize_custom_fields: bool = True,
    ) -> Dict[str, Any]:
        """Search for issues in YouTrack.

        Args:
            query: YouTrack query string (e.g., "for: me #Unresolved")
            fields: List of fields to return. If None, YouTrack returns default fields.
            skip: Number of issues to skip (for pagination)
            top: Maximum number of issues to return. If None, uses default page size.
            normalize_custom_fields: Whether to normalize custom fields for easier access

        Returns:
            Dictionary containing:
                - issues: List of issue dictionaries
                - total: Total number of matching issues (if available)
                - has_more: Whether there are more results

        Example:
            >>> client = YouTrackClient()
            >>> result = client.search_issues(
            ...     query="for: me #Unresolved",
            ...     fields=["id", "summary", "customFields(name,value(name))"],
            ...     top=10
            ... )
            >>> for issue in result["issues"]:
            ...     print(f"{issue['id']}: {issue['summary']}")
        """
        if top is None:
            top = self.config.default_page_size
        elif top > self.config.max_page_size:
            logger.warning(
                f"Requested page size {top} exceeds maximum {self.config.max_page_size}. "
                f"Using maximum instead."
            )
            top = self.config.max_page_size

        # Build query parameters
        params = {"$skip": skip, "$top": top}

        if query:
            params["query"] = query

        # Build fields parameter
        fields_param = self._build_fields_param(fields)
        if fields_param:
            params["fields"] = fields_param

        # Make API request
        logger.debug(f"Searching issues with params: {params}")
        response = self._make_request("GET", "issues", params=params)

        # Process the response
        issues = response if isinstance(response, list) else response.get("issues", [])

        # Normalize custom fields if requested
        if normalize_custom_fields:
            issues = [self._normalize_custom_fields(issue) for issue in issues]

        # Determine if there are more results
        has_more = len(issues) == top

        return {
            "issues": issues,
            "total": len(issues),  # API doesn't return total count directly
            "has_more": has_more,
            "skip": skip,
            "top": top,
        }

    def search_all_issues(
        self,
        query: str = "",
        fields: Optional[List[str]] = None,
        page_size: Optional[int] = None,
        normalize_custom_fields: bool = True,
        max_results: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Search for all issues matching the query, with automatic pagination.

        This method returns a generator that automatically fetches additional
        pages as needed.

        Args:
            query: YouTrack query string (e.g., "for: me #Unresolved")
            fields: List of fields to return. If None, YouTrack returns default fields.
            page_size: Number of issues per page. If None, uses default.
            normalize_custom_fields: Whether to normalize custom fields for easier access
            max_results: Maximum total number of results to return (None for unlimited)

        Yields:
            Individual issue dictionaries

        Example:
            >>> client = YouTrackClient()
            >>> for issue in client.search_all_issues("for: me #Unresolved"):
            ...     print(f"{issue['id']}: {issue['summary']}")
        """
        if page_size is None:
            page_size = self.config.default_page_size

        skip = 0
        total_yielded = 0

        while True:
            # Calculate how many items to fetch in this batch
            if max_results is not None:
                remaining = max_results - total_yielded
                if remaining <= 0:
                    break
                batch_size = min(page_size, remaining)
            else:
                batch_size = page_size

            # Fetch next batch
            result = self.search_issues(
                query=query,
                fields=fields,
                skip=skip,
                top=batch_size,
                normalize_custom_fields=normalize_custom_fields,
            )

            issues = result["issues"]

            # Yield each issue
            for issue in issues:
                yield issue
                total_yielded += 1

                if max_results is not None and total_yielded >= max_results:
                    return

            # Check if we've retrieved all issues
            if not result["has_more"] or len(issues) < batch_size:
                break

            skip += len(issues)

            logger.debug(f"Fetched {total_yielded} issues so far, continuing...")

    def get_issue(
        self,
        issue_id: str,
        fields: Optional[List[str]] = None,
        normalize_custom_fields: bool = True,
    ) -> Dict[str, Any]:
        """Get a single issue by ID.

        Args:
            issue_id: Issue ID (e.g., "PROJECT-123")
            fields: List of fields to return. If None, YouTrack returns default fields.
            normalize_custom_fields: Whether to normalize custom fields for easier access

        Returns:
            Issue dictionary

        Raises:
            YouTrackAPIError: If issue not found or API error occurs
        """
        # Build fields parameter
        fields_param = self._build_fields_param(fields)

        params = {}
        if fields_param:
            params["fields"] = fields_param

        # Make API request
        logger.debug(f"Fetching issue {issue_id}")
        issue = self._make_request("GET", f"issues/{issue_id}", params=params)

        # Normalize custom fields if requested
        if normalize_custom_fields:
            issue = self._normalize_custom_fields(issue)

        return issue

    def get_current_user(
        self,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get the current authenticated user's information.

        Args:
            fields: List of fields to return. If None, YouTrack returns default fields.
                   Common fields include: id, login, fullName, email, avatarUrl, banned,
                   online, guest, jabberAccountName, ringId, tags(id,name), profiles(general(locale,dateFieldFormat))

        Returns:
            Dictionary containing user information

        Raises:
            YouTrackAPIError: If API error occurs

        Example:
            >>> client = YouTrackClient()
            >>> user = client.get_current_user(fields=["id", "login", "fullName", "email"])
            >>> print(f"Logged in as: {user['fullName']} ({user['login']})")
        """
        # Build fields parameter
        fields_param = self._build_fields_param(fields)

        params = {}
        if fields_param:
            params["fields"] = fields_param

        # Make API request
        logger.debug("Fetching current user information")
        user = self._make_request("GET", "users/me", params=params)

        return user
