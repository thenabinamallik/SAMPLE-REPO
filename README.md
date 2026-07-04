# 🤖 AutoCommit - Automated GitHub README Updater

A Python Streamlit application that **automatically modifies and commits** changes to a GitHub repository's `README.md` - deployed on **Hugging Face Spaces** with zero user interaction required.

---

## Features

- 🔄 **Fully automated** — runs a background loop that updates your README on a schedule
- 📊 **Live dashboard** — Streamlit UI shows connection status, config, and activity log
- 🔐 **Secure** — credentials managed via environment variables / Hugging Face Secrets
- ⚙️ **Configurable** — repo, branch, interval, and commit message are all customizable

---

## Quick Start

### 1. Clone this repository

```bash
git clone https://github.com/<your-username>/AutoCommit.git
cd AutoCommit
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set environment variables

```bash
export GITHUB_TOKEN="ghp_your_personal_access_token"
export GITHUB_REPO="owner/repo-name"
# Optional:
export TARGET_BRANCH="main"
export UPDATE_INTERVAL_SECONDS="4320" # 72 minutes (achieves exactly 20 commits/day)
export COMMIT_MESSAGE_PREFIX="docs: auto-update README.md"
```

### 4. Run locally

```bash
streamlit run app.py
```

---

## Deploy on Hugging Face Spaces

1. Create a new **Space** on [huggingface.co/spaces](https://huggingface.co/spaces) with **Streamlit** SDK.
2. Push this repo to the Space.
3. Go to **Settings → Secrets** and add:
   - `GITHUB_TOKEN` — your GitHub Personal Access Token
   - `GITHUB_REPO` — target repo in `owner/repo` format
   - (optional) `TARGET_BRANCH`, `UPDATE_INTERVAL_SECONDS`, `COMMIT_MESSAGE_PREFIX`
4. The app starts automatically and begins updating the target README.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GITHUB_TOKEN` | ✅ | — | GitHub Personal Access Token with `repo` scope |
| `GITHUB_REPO` | ✅ | — | Target repository (`owner/repo-name`) |
| `TARGET_BRANCH` | ❌ | `main` | Branch to commit to |
| `UPDATE_INTERVAL_SECONDS` | ❌ | `4320` | Seconds between auto-updates (Default 4320s / 72 mins for exactly 20 commits/day) |
| `COMMIT_MESSAGE_PREFIX` | ❌ | `docs: auto-update README.md` | Prefix for commit messages |

---

## Security

- **Never hardcode tokens** — use environment variables or HF Secrets.
- The GitHub PAT only needs `repo` scope (or `public_repo` for public repos).
- The dashboard masks the token; only the first/last 4 characters are shown.

---

## How It Works

1. On startup, the Streamlit app validates configuration and connects to GitHub.
2. A **daemon thread** is launched that runs a loop:
   - Fetches the current `README.md` from the target branch.
   - Appends a timestamped entry to an "Auto-Update Log" section.
   - Commits the change back via the GitHub API.
   - Sleeps for the configured interval.
3. The Streamlit UI auto-refreshes every 30 seconds to show the latest activity.

---

## License

MIT

---

## Auto-Update Log

- ✅ Auto-updated on `2026-07-04 00:06:12 UTC`
- ✅ Auto-updated on `2026-07-04 00:05:41 UTC`
- ✅ Auto-updated on `2026-07-04 00:05:11 UTC`
- ✅ Auto-updated on `2026-07-04 00:04:44 UTC`
- ✅ Auto-updated on `2026-07-03 00:15:30 UTC`
- ✅ Auto-updated on `2026-07-03 00:12:26 UTC`
- ✅ Auto-updated on `2026-07-03 00:11:56 UTC`
- ✅ Auto-updated on `2026-07-03 00:11:26 UTC`
- ✅ Auto-updated on `2026-07-03 00:10:58 UTC`
- ✅ Auto-updated on `2026-07-02 16:28:41 UTC`
- ✅ Auto-updated on `2026-07-02 16:25:37 UTC`
- ✅ Auto-updated on `2026-07-02 16:25:07 UTC`
- ✅ Auto-updated on `2026-07-02 16:24:37 UTC`
- ✅ Auto-updated on `2026-07-02 16:24:07 UTC`
- ✅ Auto-updated on `2026-06-28 00:26:32 UTC`
- ✅ Auto-updated on `2026-06-28 00:17:30 UTC`
- ✅ Auto-updated on `2026-06-28 00:10:21 UTC`
- ✅ Auto-updated on `2026-06-28 00:09:51 UTC`
- ✅ Auto-updated on `2026-06-28 00:00:48 UTC`
- ✅ Auto-updated on `2026-06-27 00:06:41 UTC`
