"""
Core logic for retrieving, modifying, and committing README.md updates
to a GitHub repository via the GitHub REST API (PyGithub).
"""

import logging
from datetime import datetime, timezone

from github import Github, GithubException
from github.ContentFile import ContentFile
from github.Repository import Repository

from config import Config

logger = logging.getLogger(__name__)


class GitHubReadmeUpdater:
    """Handles the full lifecycle of a README.md auto-update."""

    def __init__(self, config: Config):
        self.config = config
        self._github = Github(config.github_token, lazy=True)
        self._repo: Repository = self._github.get_repo(config.github_repo)
        logger.info("Connected to repository: %s", config.github_repo)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run_update(self) -> dict:
        """
        Execute a single update cycle: get → modify → commit.

        Returns:
            A dict with keys:
            success (bool),
            message (str),
            commit_sha (str | None),
            timestamp (str)
        """
        timestamp = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )

        try:
            # ---------------------------------------------------------- #
            # Limit to 10 commits per day
            # ---------------------------------------------------------- #
            try:
                now = datetime.now(timezone.utc)
                since = now.replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

                commits = self._repo.get_commits(
                    path="README.md",
                    sha=self.config.target_branch,
                    since=since
                )

                recent_commits = commits.totalCount

                if recent_commits >= 10:
                    msg = (
                        f"[{timestamp}] Skipped: Daily limit reached "
                        f"({recent_commits}/10 commits today)."
                    )
                    logger.info(msg)
                    return self._result(
                        True,
                        msg,
                        None,
                        timestamp
                    )

            except GithubException as exc:
                is_empty = (
                    exc.status == 404
                    or "empty" in exc.data.get(
                        "message", ""
                    ).lower()
                )

                if not is_empty:
                    raise

            # ---------------------------------------------------------- #
            # Get current README
            # ---------------------------------------------------------- #
            try:
                content_file = self._get_readme()
                current_content = (
                    content_file.decoded_content.decode("utf-8")
                )
                current_sha = content_file.sha

            except GithubException as exc:
                is_empty_or_missing = (
                    exc.status == 404
                    or "empty" in exc.data.get(
                        "message", ""
                    ).lower()
                )

                if is_empty_or_missing:
                    current_content = ""
                    current_sha = None
                else:
                    raise

            # ---------------------------------------------------------- #
            # Modify README
            # ---------------------------------------------------------- #
            new_content = self._modify_readme(
                current_content,
                timestamp
            )

            # Avoid unnecessary commits
            if (
                current_sha is not None
                and new_content == current_content
            ):
                msg = (
                    f"[{timestamp}] No changes needed — "
                    "README is already up to date."
                )
                logger.info(msg)

                return self._result(
                    True,
                    msg,
                    None,
                    timestamp
                )

            # ---------------------------------------------------------- #
            # Commit changes
            # ---------------------------------------------------------- #
            commit = self._commit_readme(
                new_content,
                current_sha,
                timestamp
            )

            msg = (
                f"[{timestamp}] README updated successfully. "
                f"Commit: {commit.sha[:7]}"
            )

            logger.info(msg)

            return self._result(
                True,
                msg,
                commit.sha,
                timestamp
            )

        except GithubException as exc:
            msg = (
                f"[{timestamp}] GitHub API error: "
                f"{exc.data.get('message', str(exc))}"
            )
            logger.error(msg)

            return self._result(
                False,
                msg,
                None,
                timestamp
            )

        except Exception as exc:
            msg = f"[{timestamp}] Unexpected error: {exc}"
            logger.exception(msg)

            return self._result(
                False,
                msg,
                None,
                timestamp
            )

    def test_connection(self) -> tuple[bool, str]:
        """
        Verify that the token and repo are valid.
        """
        try:
            _ = self._repo.id
            user = self._github.get_user().login
            repo_name = self._repo.full_name

            return (
                True,
                f"Authenticated as '{user}', "
                f"repo '{repo_name}' is accessible."
            )

        except GithubException as exc:
            return (
                False,
                f"Connection failed: "
                f"{exc.data.get('message', str(exc))}"
            )

        except Exception as exc:
            return False, f"Connection failed: {exc}"

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _get_readme(self) -> ContentFile:
        """Fetch README.md from target branch."""
        return self._repo.get_contents(
            "README.md",
            ref=self.config.target_branch
        )

    def _modify_readme(
        self,
        content: str,
        timestamp: str
    ) -> str:
        """
        Modify README content.

        - Create README if missing.
        - Add Auto-Update Log section.
        - Keep only last 20 entries.
        """

        if not content.strip():
            content = (
                "# AutoCommit Repository\n\n"
                "This repository's README.md is automatically "
                "updated by the AutoCommit application."
            )

        section_header = "## Auto-Update Log"
        divider = "---"
        new_entry = f"- ✅ Auto-updated on `{timestamp}`"

        if section_header in content:
            before, after = content.split(section_header, 1)

            lines = after.strip().splitlines()

            entries = [
                line for line in lines
                if line.startswith("- ")
            ]

            entries.insert(0, new_entry)
            entries = entries[:20]

            rebuilt_section = (
                f"{section_header}\n\n"
                + "\n".join(entries)
                + "\n"
            )

            return (
                before.rstrip()
                + "\n\n"
                + rebuilt_section
            )

        return (
            content.rstrip()
            + f"\n\n{divider}\n\n"
            + f"{section_header}\n\n"
            + f"{new_entry}\n"
        )

    def _commit_readme(
        self,
        new_content: str,
        sha: str | None,
        timestamp: str
    ):
        """Commit README changes."""

        commit_message = (
            f"{self.config.commit_message_prefix}"
            f" [{timestamp}]"
        )

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
    def _result(
        success: bool,
        message: str,
        commit_sha: str | None,
        timestamp: str,
    ) -> dict:
        return {
            "success": success,
            "message": message,
            "commit_sha": commit_sha,
            "timestamp": timestamp,
        }
