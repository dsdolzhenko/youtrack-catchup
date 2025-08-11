"""Main entry point for YouTrack Catchup CLI."""

import argparse
import logging
import re
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any

from .api_client import YouTrackClient, YouTrackAPIError
from .config import Config
from .llm_provider import OpenAIProvider
from .issue_summarizer import IssueSummarizer


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Suppress httpx INFO logs (from OpenAI client)
logging.getLogger("httpx").setLevel(logging.WARNING)


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


def init_ai_summarizer(config: Config, model: str) -> Optional[IssueSummarizer]:
    """Initialize AI summarizer if OpenAI key is available.

    Args:
        config: Configuration object
        model: LLM model to use

    Returns:
        IssueSummarizer instance or None if OpenAI key not available
    """
    try:
        if hasattr(config, "openai_api_key") and config.openai_api_key:
            llm_provider = OpenAIProvider(config.openai_api_key, model=model)
            return IssueSummarizer(llm_provider, base_url=config.base_url)
    except Exception as e:
        logger.warning(f"Could not initialize AI features: {e}")
    return None


def display_ai_summary(
    summarizer: IssueSummarizer, issues: List[Dict[str, Any]], user: Dict[str, Any]
) -> None:
    """Display AI-generated summary of issues.

    Args:
        summarizer: IssueSummarizer instance
        issues: List of issue dictionaries
        user: Current user information
    """
    print("\n" + "=" * 80)
    print("🤖 AI-POWERED SUMMARY")
    print("=" * 80)

    user_context = f"Current user: {user.get('fullName', user.get('login', 'Unknown'))} ({user.get('login', 'Unknown')})"
    summary = summarizer.summarize_issues(issues, user_context=user_context)
    print(f"\n{summary}\n")


def display_action_items(
    summarizer: IssueSummarizer, issues: List[Dict[str, Any]], user: Dict[str, Any]
) -> None:
    """Display AI-generated action items.

    Args:
        summarizer: IssueSummarizer instance
        issues: List of issue dictionaries
        user: Current user information
    """
    print("\n" + "=" * 80)
    print("📝 PRIORITIZED ACTION ITEMS")
    print("=" * 80)

    user_context = f"{user.get('fullName', user.get('login', 'Unknown'))} ({user.get('login', 'Unknown')})"
    action_items = summarizer.generate_action_items(
        issues, max_items=10, user_context=user_context
    )

    if action_items:
        for i, item in enumerate(action_items, 1):
            print(f"\n  {i}. [ ] {item}")
        print()
    else:
        print("\nNo action items generated.\n")


def analyze_specific_issue(
    summarizer: IssueSummarizer, issues: List[Dict[str, Any]], issue_id: str
) -> None:
    """Analyze a specific issue in detail.

    Args:
        summarizer: IssueSummarizer instance
        issues: List of issue dictionaries
        issue_id: Issue ID to analyze
    """
    # Find the issue
    issue = None
    for i in issues:
        if i.get("idReadable", "").lower() == issue_id.lower():
            issue = i
            break

    if not issue:
        print(f"\n❌ Issue '{issue_id}' not found in the fetched issues.")
        return

    print("\n" + "=" * 80)
    print(f"🔍 DETAILED ANALYSIS: {issue_id}")
    print("=" * 80)

    analysis = summarizer.analyze_issue(issue, analysis_type="general")
    print(f"\n{analysis}\n")


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
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Generate an AI-powered summary of all issues",
    )
    parser.add_argument(
        "--actions",
        action="store_true",
        help="Generate a list of prioritized action items",
    )
    parser.add_argument(
        "--analyze",
        type=str,
        metavar="ISSUE_ID",
        help="Analyze a specific issue in detail (e.g., 'PROJECT-123')",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="LLM model to use for AI features (default: gpt-4o-mini)",
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

        # Initialize AI summarizer if needed
        summarizer = None
        if args.summarize or args.actions or args.analyze:
            summarizer = init_ai_summarizer(config, args.model)
            if not summarizer:
                print(
                    "\n⚠️  AI features unavailable. Please set OPEN_AI_TOKEN in your .env file."
                )

        # Display AI-powered features if requested and available
        if summarizer:
            if args.summarize:
                display_ai_summary(summarizer, issues, user)

            if args.actions:
                display_action_items(summarizer, issues, user)

            if args.analyze:
                analyze_specific_issue(summarizer, issues, args.analyze)

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
