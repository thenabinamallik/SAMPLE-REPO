"""
AutoCommit — Automated GitHub README Updater

A Streamlit dashboard that launches a background thread to periodically
update a GitHub repository's README.md. The UI is informational only;
the entire process runs without user interaction.
"""

import logging
import threading
import time
from datetime import datetime, timezone

import streamlit as st

from config import Config
from updater import GitHubReadmeUpdater

# ---------------------------------------------------------------------------
#  Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AutoCommit — README Updater",
    page_icon="🤖",
    layout="centered",
)

# ---------------------------------------------------------------------------
#  Shared State (Thread-Safe Global State)
# ---------------------------------------------------------------------------
class GlobalState:
    _lock = threading.Lock()
    log: list[dict] = []
    connection_status: tuple[bool, str] | None = None
    updater_running = False

    @classmethod
    def add_log(cls, entry: dict):
        with cls._lock:
            cls.log.insert(0, entry)
            cls.log = cls.log[:50]

    @classmethod
    def set_connection_status(cls, ok: bool, msg: str):
        with cls._lock:
            cls.connection_status = (ok, msg)

    @classmethod
    def set_running(cls, running: bool):
        with cls._lock:
            cls.updater_running = running

    @classmethod
    def is_running(cls) -> bool:
        with cls._lock:
            return cls.updater_running

    @classmethod
    def get_connection_status(cls) -> tuple[bool, str] | None:
        with cls._lock:
            return cls.connection_status

    @classmethod
    def get_log(cls) -> list[dict]:
        with cls._lock:
            return list(cls.log)


# ---------------------------------------------------------------------------
#  Background updater thread
# ---------------------------------------------------------------------------
def _updater_loop(config: Config):
    """Runs in a daemon thread — performs periodic README updates."""
    try:
        try:
            updater = GitHubReadmeUpdater(config)
            ok, msg = updater.test_connection()
            GlobalState.set_connection_status(ok, msg)
        except Exception as exc:
            GlobalState.set_connection_status(False, f"Initialization failed: {exc}")
            logger.exception("Failed to initialize updater or test connection")
            return

        if not ok:
            logger.error("Connection test failed, aborting updater loop.")
            return

        logger.info(
            "Updater loop started. Interval: %d s", config.update_interval
        )

        while True:
            result = updater.run_update()
            GlobalState.add_log(result)

            time.sleep(config.update_interval)

    except Exception:
        logger.exception("Updater loop crashed")


def _ensure_updater_started(config: Config):
    """Start the background thread exactly once."""
    if GlobalState.is_running():
        return
    GlobalState.set_running(True)
    thread = threading.Thread(target=_updater_loop, args=(config,), daemon=True)
    thread.start()
    logger.info("Background updater thread launched.")


# ---------------------------------------------------------------------------
#  UI
# ---------------------------------------------------------------------------
def main():
    # ---- Header ----
    st.markdown(
        """
        <div style="text-align:center; padding: 1rem 0 0.5rem;">
            <h1 style="margin:0;">🤖 AutoCommit</h1>
            <p style="color:grey;">Automated GitHub README Updater</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Load & validate config ----
    config = Config()
    errors = config.validate()

    if errors:
        st.error("⚠️ Configuration errors — fix these before the updater can run:")
        for err in errors:
            st.warning(err)
        st.info(
            "Set the required environment variables as **Hugging Face Secrets** "
            "(Settings → Secrets) or in your local shell, then restart the app."
        )
        st.stop()

    # ---- Start background updater ----
    _ensure_updater_started(config)

    # ---- Dashboard ----
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📡 Connection")
        status = GlobalState.get_connection_status()
        if status is None:
            st.info("Connecting…")
        elif status[0]:
            st.success(status[1])
        else:
            st.error(status[1])

    with col2:
        st.subheader("⚙️ Configuration")
        st.markdown(
            f"""
| Setting | Value |
|---|---|
| **Repository** | `{config.github_repo}` |
| **Branch** | `{config.target_branch}` |
| **Interval** | `{config.update_interval}` s |
| **Token** | `{config.masked_token}` |
"""
        )

    st.divider()

    # ---- Activity log ----
    st.subheader("📋 Activity Log")

    logs = GlobalState.get_log()
    if not logs:
        st.info("No updates yet — the first run is in progress…")
    else:
        for entry in logs:
            icon = "✅" if entry["success"] else "❌"
            sha_info = ""
            if entry.get("commit_sha"):
                sha_info = f"  •  `{entry['commit_sha'][:7]}`"
            st.markdown(f"{icon} {entry['message']}{sha_info}")

    # ---- Auto-refresh every 30 s so the UI stays current ----
    time.sleep(30)
    st.rerun()


if __name__ == "__main__":
    main()
