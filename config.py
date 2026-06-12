"""
Configuration management for the AutoCommit application.

All settings are read from environment variables, making them compatible
with Hugging Face Spaces Secrets (encrypted at rest).
"""

import os


class Config:
    """Loads and validates configuration from environment variables."""

    def __init__(self):
        # Required
        self.github_token: str = os.environ.get("GITHUB_TOKEN", "")
        repo = os.environ.get("GITHUB_REPO", "")
        self.github_repo: str = self._normalize_repo(repo)

        # Optional with defaults
        self.target_branch: str = os.environ.get("TARGET_BRANCH", "main")
        self.update_interval: int = int(
            os.environ.get("UPDATE_INTERVAL_SECONDS", "4320")  # Default to 4320s (72m) for 20 commits/day
        )
        self.commit_message_prefix: str = os.environ.get(
            "COMMIT_MESSAGE_PREFIX", "docs: auto-update README.md"
        )

    @staticmethod
    def _normalize_repo(repo: str) -> str:
        """Extract 'owner/repo-name' from common GitHub URL formats."""
        repo = repo.strip()
        if not repo:
            return ""

        # Remove protocol prefixes
        for prefix in ("https://", "http://"):
            if repo.startswith(prefix):
                repo = repo[len(prefix):]

        # Remove domain
        if repo.startswith("github.com/"):
            repo = repo[len("github.com/"):]

        # Remove trailing .git extension
        if repo.endswith(".git"):
            repo = repo[:-4]

        # Clean any leading/trailing slashes
        return repo.strip("/")

    def validate(self) -> list[str]:
        """
        Validate that all required configuration values are present.

        Returns:
            A list of error messages. Empty list means all checks passed.
        """
        errors: list[str] = []

        if not self.github_token:
            errors.append(
                "GITHUB_TOKEN is not set. "
                "Add it as a Hugging Face Secret or environment variable."
            )

        if not self.github_repo:
            errors.append(
                "GITHUB_REPO is not set. "
                "Expected format: 'owner/repo-name'."
            )
        elif "/" not in self.github_repo:
            errors.append(
                f"GITHUB_REPO '{self.github_repo}' is invalid. "
                "Expected format: 'owner/repo-name'."
            )

        if self.update_interval < 10:
            errors.append(
                f"UPDATE_INTERVAL_SECONDS is {self.update_interval}, "
                "which is too low. Minimum is 10 seconds."
            )

        return errors

    @property
    def masked_token(self) -> str:
        """Return a masked version of the token for display purposes."""
        if not self.github_token:
            return "(not set)"
        if len(self.github_token) <= 8:
            return "****"
        return self.github_token[:4] + "****" + self.github_token[-4:]

    def __repr__(self) -> str:
        return (
            f"Config(repo={self.github_repo!r}, branch={self.target_branch!r}, "
            f"interval={self.update_interval}s, token={self.masked_token})"
        )
