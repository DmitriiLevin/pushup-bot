"""
Персистентність state.json через git commit+push у той самий репозиторій.

Навіщо: більшість безкоштовних 24/7-хостингів (Fly.io, Railway тощо)
не гарантують постійний диск — контейнер може пересоздатись при передеплої,
і локальний state.json загубиться. Замість того щоб вимагати платний volume,
бот при кожній зміні стану комітить data/state.json назад у GitHub-репозиторій
(так само, як раніше робив GitHub Actions workflow) і підтягує його при старті.

Якщо GITHUB_TOKEN/GITHUB_REPO не задані — модуль просто нічого не робить,
і бот працює з локальним диском (ок для VPS з постійним диском).
"""

from __future__ import annotations

import asyncio
import logging
import subprocess

logger = logging.getLogger(__name__)


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=30)


def _remote_url(github_token: str, github_repo: str) -> str:
    """github_repo у форматі 'owner/name'."""
    return f"https://x-access-token:{github_token}@github.com/{github_repo}.git"


def pull_latest(github_token: str, github_repo: str) -> None:
    """Синхронно підтягує найсвіжіший state.json з GitHub перед стартом бота."""
    remote = _remote_url(github_token, github_repo)
    result = _run("git", "fetch", remote, "HEAD")
    if result.returncode != 0:
        logger.warning("Не вдалось зробити git fetch перед стартом: %s", result.stderr.strip())
        return

    result = _run("git", "checkout", "FETCH_HEAD", "--", "data/state.json")
    if result.returncode != 0:
        logger.warning("Не вдалось підтягнути data/state.json з GitHub: %s", result.stderr.strip())
    else:
        logger.info("data/state.json синхронізовано з GitHub перед стартом")


async def commit_and_push(github_token: str, github_repo: str, message: str) -> None:
    """Асинхронно комітить і пушить зміни в data/state.json (не блокує event loop)."""
    await asyncio.to_thread(_commit_and_push_sync, github_token, github_repo, message)


def _commit_and_push_sync(github_token: str, github_repo: str, message: str) -> None:
    _run("git", "config", "user.name", "pushup-bot")
    _run("git", "config", "user.email", "pushup-bot@users.noreply.github.com")
    _run("git", "add", "data/state.json")

    diff = _run("git", "diff", "--staged", "--quiet")
    if diff.returncode == 0:
        return  # немає змін

    commit = _run("git", "commit", "-m", f"chore: {message} [skip ci]")
    if commit.returncode != 0:
        logger.warning("git commit не вдався: %s", commit.stderr.strip())
        return

    remote = _remote_url(github_token, github_repo)
    push = _run("git", "push", remote, "HEAD:main")
    if push.returncode != 0:
        logger.warning("git push не вдався: %s", push.stderr.strip())
    else:
        logger.info("state.json запушено у GitHub (%s)", message)
