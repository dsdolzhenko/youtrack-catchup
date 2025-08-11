"""Main entry point for YouTrack Catchup CLI."""

import logging
import sys
from pprint import pprint

from .api_client import YouTrackClient, YouTrackAPIError
from .config import Config


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main function to demonstrate YouTrack API client usage."""
    try:
        # Initialize configuration and client
        config = Config()
        client = YouTrackClient(config)

        print(f"Connected to YouTrack at: {config.base_url}\n")

        # Example 1: Search for unresolved issues assigned to current user
        print("=" * 60)
        print("Example 1: Fetching first 5 unresolved issues for current user")
        print("=" * 60)

        result = client.search_issues(
            query="for: me #Unresolved",
            fields=[
                "idReadable",
                "summary",
                "created",
                "updated",
                "customFields(name,value(name))",
            ],
            top=5,
        )

        print(
            f"\nFound {len(result['issues'])} issues (has_more: {result['has_more']})\n"
        )

        for issue in result["issues"]:
            print(f"Issue: {issue.get('idReadable', issue.get('id'))}")
            print(f"  Summary: {issue.get('summary', 'N/A')}")
            print(f"  Created: {issue.get('created', 'N/A')}")

            if "custom_fields" in issue:
                cf = issue["custom_fields"]
                print(f"  State: {cf.get('State', 'N/A')}")
                print(f"  Priority: {cf.get('Priority', 'N/A')}")
                print(f"  Type: {cf.get('Type', 'N/A')}")
            print()

        # Example 2: Using the generator to fetch all issues with a limit
        print("=" * 60)
        print("Example 2: Using generator to fetch issues")
        print("=" * 60)

        print("\nFetching up to 10 issues using generator:")
        count = 0
        for issue in client.search_all_issues(
            query="for: me",
            fields=["idReadable", "summary"],
            page_size=3,  # Small page size to demonstrate pagination
            max_results=10,
        ):
            count += 1
            print(
                f"  {count}. {issue.get('idReadable', issue.get('id'))}: {issue.get('summary', 'N/A')[:50]}..."
            )

        print(f"\nTotal issues fetched: {count}")

        # Example 3: Get a specific issue (if you know an issue ID)
        print("\n" + "=" * 60)
        print("Example 3: Fetching a specific issue (if available)")
        print("=" * 60)

        # Try to get the first issue from our search results
        if result["issues"]:
            first_issue_id = result["issues"][0].get("idReadable") or result["issues"][
                0
            ].get("id")
            print(f"\nFetching details for issue: {first_issue_id}")

            issue = client.get_issue(
                issue_id=first_issue_id,
                fields=[
                    "idReadable",
                    "summary",
                    "description",
                    "customFields(name,value(name))",
                ],
            )

            print("\nIssue details:")
            print(f"  ID: {issue.get('idReadable', issue.get('id'))}")
            print(f"  Summary: {issue.get('summary', 'N/A')}")
            print(
                f"  Description: {(issue.get('description', 'N/A') or 'N/A')[:100]}..."
            )

            if "custom_fields" in issue:
                print("\n  Custom fields:")
                for field_name, field_value in issue["custom_fields"].items():
                    print(f"    {field_name}: {field_value}")

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\nConfiguration error: {e}")
        print("Please ensure your .env file contains YOUTRACK_URL and YOUTRACK_TOKEN")
        sys.exit(1)

    except YouTrackAPIError as e:
        logger.error(f"API error: {e}")
        print(f"\nAPI error: {e}")
        print("Please check your YouTrack URL and authentication token")
        sys.exit(1)

    except Exception as e:
        logger.exception("Unexpected error occurred")
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
