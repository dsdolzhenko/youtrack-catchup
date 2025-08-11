"""Main entry point for YouTrack Catchup CLI."""

import argparse
import logging
import re
import sys
from datetime import datetime

from .api_client import YouTrackClient, YouTrackAPIError
from .config import Config


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def validate_period(period: str) -> str:
    """Validate period string format for YouTrack.

    Args:
        period: Period string like '7d', '1w', '1M', '1y 2M 1w'

    Returns:
        Validated and stripped period string

    Raises:
        ValueError: If period format is invalid
    """
    # Basic validation - YouTrack will handle the actual parsing
    # Supports: y (years), M (months), w (weeks), d (days), h (hours), m (minutes)
    pattern = r"^(\d+[yMwdhm]\s*)+$"
    period = period.strip()
    if not re.match(pattern, period):
        raise ValueError(
            f"Invalid period format: '{period}'. "
            f"Use formats like '7d', '1w', '2M', '1y', or '1y 2M 1w'"
        )
    return period


def format_timestamp(timestamp_ms: int) -> str:
    """Format timestamp from milliseconds to readable string.

    Args:
        timestamp_ms: Timestamp in milliseconds

    Returns:
        Formatted date string
    """
    if not timestamp_ms:
        return "N/A"
    dt = datetime.fromtimestamp(timestamp_ms / 1000)
    return dt.strftime("%Y-%m-%d %H:%M")


def fetch_my_issues(
    client: YouTrackClient, fields: list[str], since: str
) -> list[dict]:
    """Fetch issues that the current user is involved with.

    Fetches issues where the user is:
    - Reporter (created the issue)
    - Assignee (assigned to the issue)
    - Mentioned (in description or comments)
    - Subscriber (starred the issue)

    Args:
        client: YouTrack API client instance
        fields: List of fields to fetch for each issue
        since: Time period string (e.g., '7d', '1w', '2M')

    Returns:
        List of issue dictionaries sorted by updated time (most recent first)
    """
    # Validate period format
    period = validate_period(since)

    # Construct query for issues user is involved with, updated recently
    query = f"(reporter: me or Assignee: me or mentions: me or has: star) and updated: {{minus {period}}} .. Today"
    logger.debug(f"Query: {query}")

    # Fetch all matching issues
    issues = []
    for issue in client.search_all_issues(
        query=query, fields=fields, page_size=50, normalize_custom_fields=True
    ):
        issues.append(issue)

    # Sort by updated time (most recent first)
    issues.sort(key=lambda x: x.get("updated", 0), reverse=True)

    return issues


def main():
    """Main function to fetch and display recent YouTrack issues."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Catch up on recent YouTrack issues requiring your attention"
    )
    parser.add_argument(
        "--since",
        type=str,
        default="1w",
        help="Time period to look back (e.g., '7d', '1w', '2M', '1y 2M'). Default: 1w",
    )
    args = parser.parse_args()

    try:
        # Initialize configuration and client
        config = Config()
        client = YouTrackClient(config)

        # Get current user info
        print(f"Connected to YouTrack at: {config.base_url}")
        user = client.get_current_user(fields=["login", "fullName", "email"])
        print(
            f"Logged in as: {user.get('fullName', user.get('login', 'Unknown'))} ({user.get('login', 'Unknown')})"
        )
        print(f"Fetching issues from the last {args.since}...")
        print("=" * 80)

        # Fields to fetch (including comments)
        fields = [
            "idReadable",
            "summary",
            "description",
            "created",
            "updated",
            "resolved",
            "customFields(name,value(name,login))",
            "comments(id,text,created,author(login,fullName))",
        ]

        # Fetch all matching issues
        print("\nFetching issues...\n")
        issues = fetch_my_issues(client, fields, args.since)

        if not issues:
            print("No issues found for the specified period.")
            return

        print(f"Found {len(issues)} issue(s)\n")
        print("=" * 80)

        # Display each issue
        for issue in issues:
            # Basic info
            issue_id = issue.get("idReadable", issue.get("id", "Unknown"))
            summary = issue.get("summary", "No summary")
            created = format_timestamp(issue.get("created"))
            updated = format_timestamp(issue.get("updated"))
            resolved = (
                format_timestamp(issue.get("resolved"))
                if issue.get("resolved")
                else "Unresolved"
            )

            print(f"\n📋 {issue_id}: {summary}")
            print(f"   Created: {created} | Updated: {updated} | Resolved: {resolved}")

            # Custom fields (State, Priority, Type, etc.)
            if "custom_fields" in issue:
                cf = issue["custom_fields"]
                state = cf.get("State", "N/A")
                priority = cf.get("Priority", "N/A")
                issue_type = cf.get("Type", "N/A")
                assignee = cf.get("Assignee", "Unassigned")

                print(f"   State: {state} | Priority: {priority} | Type: {issue_type}")
                print(f"   Assignee: {assignee}")

            # Description preview
            description = issue.get("description", "")
            if description:
                # Show first 200 characters of description
                desc_preview = description[:200].replace("\n", " ")
                if len(description) > 200:
                    desc_preview += "..."
                print(f"   Description: {desc_preview}")

            # Comments
            comments = issue.get("comments", [])
            if comments:
                print(f"   💬 Comments ({len(comments)}):")
                # Show last 3 comments
                for comment in comments[-3:]:
                    author = comment.get("author", {})
                    author_name = author.get("fullName", author.get("login", "Unknown"))
                    comment_date = format_timestamp(comment.get("created"))
                    comment_text = comment.get("text", "")

                    if comment_text:
                        # Show first 150 characters of comment
                        text_preview = comment_text[:150].replace("\n", " ")
                        if len(comment_text) > 150:
                            text_preview += "..."
                        print(f"      • {author_name} ({comment_date}): {text_preview}")

            print("-" * 80)

        print(f"\n✅ Total issues requiring attention: {len(issues)}")

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n❌ Configuration error: {e}")
        print("Please ensure your .env file contains YOUTRACK_URL and YOUTRACK_TOKEN")
        sys.exit(1)

    except YouTrackAPIError as e:
        logger.error(f"API error: {e}")
        print(f"\n❌ API error: {e}")
        print("Please check your YouTrack URL and authentication token")
        sys.exit(1)

    except Exception as e:
        logger.exception("Unexpected error occurred")
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
