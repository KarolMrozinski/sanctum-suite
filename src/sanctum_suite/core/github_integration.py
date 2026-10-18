from typing import Any


class GitHubAutomatedPRPublisher:
    """Reports that GitHub branch and pull-request creation is not integrated."""

    def __init__(self, token: str | None = None, repo: str | None = None) -> None:
        self.token = token
        self.repo = repo

    async def create_auto_fix_pr(
        self,
        branch_name: str,
        patch_diff: str,
        title: str,
    ) -> dict[str, Any]:
        return {
            "status": "NOT_IMPLEMENTED",
            "created": False,
            "pr_url": None,
            "branch": None,
            "reason": "GitHub API branch and pull-request operations are not implemented",
        }
