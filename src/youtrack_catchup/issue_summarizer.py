"""Issue summarization service using LLM providers."""

import logging
from typing import Optional, List, Dict, Any

from .llm_provider import LLMProvider


logger = logging.getLogger(__name__)


class IssueSummarizer:
    """Service for summarizing and analyzing YouTrack issues using LLMs."""

    def __init__(self, llm_provider: LLMProvider, base_url: Optional[str] = None):
        """Initialize issue summarizer with an LLM provider.

        Args:
            llm_provider: LLM provider instance for generating summaries
            base_url: Optional YouTrack base URL for generating issue links
        """
        self.llm = llm_provider
        self.base_url = base_url

    def summarize_issues(
        self,
        issues: List[Dict[str, Any]],
        user_context: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> str:
        """Generate a summary of YouTrack issues.

        Args:
            issues: List of issue dictionaries from YouTrack
            user_context: Optional context about the user's role or preferences
            max_tokens: Maximum tokens for the response

        Returns:
            AI-generated summary of the issues
        """
        if not issues:
            return "No issues to summarize."

        # Prepare issue data for the prompt
        issues_text = self._format_issues_for_prompt(issues)

        # Build the system prompt
        system_prompt = (
            "You are an assistant helping users catch up on their YouTrack issues. "
            "Provide a concise, actionable summary highlighting what needs immediate attention. "
            "Group related issues when possible and emphasize priority items. "
            "When referencing issues, preserve the markdown links in format [ISSUE-ID](url) that are provided."
        )

        if user_context:
            system_prompt += f" User context: {user_context}"

        # Build the user prompt
        user_prompt = (
            f"Please summarize the following {len(issues)} YouTrack issues:\n\n"
            f"{issues_text}\n\n"
            "Provide:\n"
            "1. A brief overview of what needs attention\n"
            "2. High-priority items requiring immediate action\n"
            "3. Items waiting on others or blocked\n"
            "4. Any patterns or trends you notice"
        )

        try:
            return self.llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=0.7,
            )
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"Failed to generate AI summary: {str(e)}"

    def analyze_issue(
        self,
        issue: Dict[str, Any],
        analysis_type: str = "general",
        max_tokens: int = 500,
    ) -> str:
        """Analyze a single issue in detail.

        Args:
            issue: Issue dictionary from YouTrack
            analysis_type: Type of analysis ('general', 'technical', 'priority')
            max_tokens: Maximum tokens for the response

        Returns:
            AI-generated analysis of the issue
        """
        issue_text = self._format_single_issue(issue)

        prompts = {
            "general": (
                "Analyze this issue and provide:\n"
                "1. What action is needed\n"
                "2. Who should take action\n"
                "3. Estimated urgency\n"
                "4. Any blockers or dependencies"
            ),
            "technical": (
                "Provide a technical analysis:\n"
                "1. Technical complexity assessment\n"
                "2. Potential implementation approach\n"
                "3. Risks or challenges\n"
                "4. Suggested next steps"
            ),
            "priority": (
                "Assess the priority of this issue:\n"
                "1. Impact assessment\n"
                "2. Urgency level (1-5)\n"
                "3. Affected stakeholders\n"
                "4. Recommendation for prioritization"
            ),
        }

        prompt = prompts.get(analysis_type, prompts["general"])

        system_prompt = (
            "You are an expert at analyzing software development issues and providing actionable insights. "
            "When referencing the issue, preserve the markdown link in format [ISSUE-ID](url) if provided."
        )
        user_prompt = f"{issue_text}\n\n{prompt}"

        try:
            return self.llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=0.7,
            )
        except Exception as e:
            logger.error(f"Failed to analyze issue: {e}")
            return f"Failed to analyze issue: {str(e)}"

    def generate_action_items(
        self, issues: List[Dict[str, Any]], max_items: int = 10
    ) -> List[str]:
        """Generate actionable items from a list of issues.

        Args:
            issues: List of issue dictionaries from YouTrack
            max_items: Maximum number of action items to generate

        Returns:
            List of action items
        """
        if not issues:
            return []

        issues_text = self._format_issues_for_prompt(issues)

        system_prompt = (
            "You are an expert at creating clear, actionable tasks from issue tracking data. "
            "When referencing specific issues in action items, preserve the markdown links in format [ISSUE-ID](url)."
        )

        user_prompt = (
            f"Based on these {len(issues)} YouTrack issues:\n\n"
            f"{issues_text}\n\n"
            f"Generate up to {max_items} specific, actionable items that the user should do today. "
            "Format each as a clear, concise action starting with a verb. "
            "Include issue references using the markdown links provided. "
            "Prioritize by urgency and impact. "
            "Return only the action items, one per line, without numbering or bullets."
        )

        try:
            content = self.llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=500,
                temperature=0.6,
            )

            # Split by lines and clean up
            action_items = [
                line.strip()
                for line in content.split("\n")
                if line.strip() and not line.strip().startswith(("#", "-", "*", "•"))
            ]

            return action_items[:max_items]

        except Exception as e:
            logger.error(f"Failed to generate action items: {e}")
            return []

    def _format_issues_for_prompt(self, issues: List[Dict[str, Any]]) -> str:
        """Format multiple issues for inclusion in a prompt.

        Args:
            issues: List of issue dictionaries

        Returns:
            Formatted string representation of issues
        """
        formatted_issues = []
        for issue in issues[:20]:  # Limit to prevent token overflow
            formatted_issues.append(self._format_single_issue(issue))

        return "\n---\n".join(formatted_issues)

    def _format_single_issue(self, issue: Dict[str, Any]) -> str:
        """Format a single issue for inclusion in a prompt.

        Args:
            issue: Issue dictionary

        Returns:
            Formatted string representation of the issue
        """
        parts = []

        # Basic info
        issue_id = issue.get("idReadable", "Unknown")
        summary = issue.get("summary", "No summary")

        # Format with markdown link if base_url is available
        if self.base_url:
            issue_link = f"[{issue_id}]({self.base_url}/issue/{issue_id})"
            parts.append(f"Issue {issue_link}: {summary}")
        else:
            parts.append(f"Issue {issue_id}: {summary}")

        # Custom fields
        if "custom_fields" in issue:
            cf = issue["custom_fields"]
            state = cf.get("State", "Unknown")
            priority = cf.get("Priority", "Normal")
            assignee = cf.get("Assignee", "Unassigned")
            parts.append(f"State: {state}, Priority: {priority}, Assignee: {assignee}")

        # Description (truncated)
        description = issue.get("description", "")
        if description:
            desc_preview = description[:300]
            if len(description) > 300:
                desc_preview += "..."
            parts.append(f"Description: {desc_preview}")

        # Recent comments
        comments = issue.get("comments", [])
        if comments:
            recent_comments = comments[-2:]  # Last 2 comments
            comment_texts = []
            for comment in recent_comments:
                author = comment.get("author", {}).get("login", "Unknown")
                text = comment.get("text", "")[:150]
                if text:
                    comment_texts.append(f"{author}: {text}")
            if comment_texts:
                parts.append(f"Recent comments: {'; '.join(comment_texts)}")

        return "\n".join(parts)
