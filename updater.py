"""
Core logic for retrieving, modifying, and committing README.md updates
to a GitHub repository via the GitHub REST API (PyGithub).
"""

import logging
from datetime import datetime, timezone, timedelta

from github import Github, GithubException
from github.ContentFile import ContentFile
from github.Repository import Repository

from config import Config

logger = logging.getLogger(__name__)


class GitHubReadmeUpdater:
    """Handles the full lifecycle of a README auto-update."""

    def __init__(self, config: Config):
        self.config = config
        self._github = Github(config.github_token, lazy=True)
        self._repo: Repository = self._github.get_repo(config.github_repo)
        logger.info("Connected to repository: %s", config.github_repo)

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def run_update(self) -> dict:
        """
        Execute a single update cycle: get → modify → commit.

        Returns:
            A dict with keys: success (bool), message (str),
            commit_sha (str | None), timestamp (str).
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        try:
            # Enforce a maximum limit of 20 commits in the last 24 hours
            try:
                since = datetime.now(timezone.utc) - timedelta(days=1)
                commits = self._repo.get_commits(
                    path="README.md",
                    sha=self.config.target_branch,
                    since=since
                )
                recent_commits = commits.totalCount
                if recent_commits >= 20:
                    msg = f"[{timestamp}] Skipped: Daily limit reached ({recent_commits}/20 commits in last 24h)."
                    logger.info(msg)
                    return self._result(True, msg, None, timestamp)
            except GithubException as exc:
                # If repository is empty or branch doesn't exist, ignore and proceed
                is_empty = exc.status == 404 or "empty" in exc.data.get("message", "").lower()
                if not is_empty:
                    raise

            try:
                content_file = self._get_readme()
                current_content = content_file.decoded_content.decode("utf-8")
                current_sha = content_file.sha
            except GithubException as exc:
                # 404: README.md not found or branch/repo not found
                # "empty" in error message: repository is empty
                is_empty_or_missing = (
                    exc.status == 404 
                    or "empty" in exc.data.get("message", "").lower()
                )
                if is_empty_or_missing:
                    current_content = ""
                    current_sha = None
                else:
                    raise

            new_content = self._modify_readme(current_content, timestamp)

            if current_sha is not None and new_content == current_content:
                msg = f"[{timestamp}] No changes needed — README is already up to date."
                logger.info(msg)
                return self._result(True, msg, None, timestamp)

            commit = self._commit_readme(new_content, current_sha, timestamp)
            msg = f"[{timestamp}] README updated successfully. Commit: {commit.sha[:7]}"
            logger.info(msg)
            return self._result(True, msg, commit.sha, timestamp)

        except GithubException as exc:
            msg = f"[{timestamp}] GitHub API error: {exc.data.get('message', str(exc))}"
            logger.error(msg)
            return self._result(False, msg, None, timestamp)
        except Exception as exc:
            msg = f"[{timestamp}] Unexpected error: {exc}"
            logger.exception(msg)
            return self._result(False, msg, None, timestamp)

    def test_connection(self) -> tuple[bool, str]:
        """
        Verify that the token and repo are valid.

        Returns:
            (success, message) tuple.
        """
        try:
            # Trigger lazy load of repository metadata to verify access
            _ = self._repo.id
            user = self._github.get_user().login
            repo_name = self._repo.full_name
            return True, f"Authenticated as '{user}', repo '{repo_name}' is accessible."
        except GithubException as exc:
            return False, f"Connection failed: {exc.data.get('message', str(exc))}"
        except Exception as exc:
            return False, f"Connection failed: {exc}"

    # ------------------------------------------------------------------ #
    #  Internals
    # ------------------------------------------------------------------ #

    def _get_readme(self) -> ContentFile:
        """Fetch the current README.md from the target branch."""
        return self._repo.get_contents(
            "README.md", ref=self.config.target_branch
        )

    def _modify_readme(self, content: str, timestamp: str) -> str:
        """
        Apply modifications to the README content.

        Current strategy:
        - Ensure an "## Auto-Update Log" section exists at the bottom.
        - Append a timestamped entry to that section.
        - Keep only the last 20 entries to avoid unbounded growth.
        """
        if not content.strip():
            content = (
                f"# AutoCommit Repository\n\n"
                f"This repository's README.md is automatically updated by the AutoCommit application."
            )

        section_header = "## Auto-Update Log"
        divider = "---"
        new_entry = f"- ✅ Auto-updated on `{timestamp}`"

        if section_header in content:
            # Split around the section header
            before, after = content.split(section_header, 1)
            # Parse existing entries (lines starting with "- ")
            lines = after.strip().splitlines()
            entries = [l for l in lines if l.startswith("- ")]
            non_entries = [l for l in lines if not l.startswith("- ") and l.strip()]

            entries.insert(0, new_entry)  # newest first
            entries = entries[:20]  # cap at 20

            rebuilt_section = (
                f"{section_header}\n\n"
                + "\n".join(entries)
                + "\n"
            )
            return before.rstrip() + "\n\n" + rebuilt_section
        else:
            # Append a new section at the end
            return (
                content.rstrip()
                + f"\n\n{divider}\n\n{section_header}\n\n{new_entry}\n"
            )

    def _commit_readme(self, new_content: str, sha: str | None, timestamp: str):
        """Commit the updated README.md back to the repository."""
        commit_message = f"{self.config.commit_message_prefix} [{timestamp}]"
        if sha is None:
            result = self._repo.create_file(
                path="README.md",
                message=commit_message,
                content=new_content,
                branch=self.config.target_branch,
            )
        else:
            result = self._repo.update_file(
                path="README.md",
                message=commit_message,
                content=new_content,
                sha=sha,
                branch=self.config.target_branch,
            )
        return result["commit"]

    @staticmethod
    def _result(success: bool, message: str, commit_sha: str | None, timestamp: str) -> dict:
        return {
            "success": success,
            "message": message,
            "commit_sha": commit_sha,
            "timestamp": timestamp,
        }
