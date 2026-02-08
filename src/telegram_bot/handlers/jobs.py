"""Background jobs and standalone callback handlers."""

import logging
import os
import subprocess
import time
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ..config import (
    GIT_DIFF_RANGE,
    LOG_MAX_SIZE_MB,
    LOG_RETENTION_DAYS,
    PROJECTS_ROOT,
    QUEUE_TTL,
    STALE_THRESHOLD,
    TELEGRAM_CHAT_ID,
)
from ..git_utils import get_diff_stats, get_plan_progress, get_recent_commits
from ..log_rotation import cleanup_brainstorm_files, rotate_logs
from ..messages import (
    MSG_COMPLETION_CHANGES,
    MSG_COMPLETION_COMMITS,
    MSG_COMPLETION_ITERATIONS,
    MSG_COMPLETION_PLAN,
    MSG_COMPLETION_QUEUE_NEXT,
    MSG_COMPLETION_TIME,
    MSG_COMPLETION_TITLE,
    MSG_DIFF_SUMMARY_BTN,
    MSG_DIFF_TITLE,
    MSG_ITERATION_LABEL,
    MSG_NO_DATA,
    MSG_PROJECT_BTN,
    MSG_PROJECT_NOT_FOUND,
    MSG_QUEUE_EXPIRED,
    MSG_STALE_PROGRESS,
    MSG_STARTED_FROM_QUEUE,
    MSG_TRUNCATED,
    MSG_UNAUTHORIZED,
)
from ..projects import get_project
from ..tasks import Task, task_manager
from .common import _nav_keyboard

logger = logging.getLogger(__name__)


def _format_completion_summary(
    task: Task,
    diff_stats: dict | None,
    commits: list[str],
    plan_progress: tuple[int, int] | None,
    next_task: Task | None = None,
) -> str:
    """Build a Markdown completion summary message.

    When next_task is provided, appends a "queue next" line so the user
    receives one consolidated message instead of two separate ones.
    """
    icon = "\u25c7" if task.mode == "plan" else "\u25a0"
    duration = task_manager.get_task_duration(task)

    text = MSG_COMPLETION_TITLE.format(icon=icon, project=task.project, mode=task.mode.title())
    text += MSG_COMPLETION_ITERATIONS.format(iterations=task.iterations)
    text += MSG_COMPLETION_TIME.format(duration=duration)

    if diff_stats:
        text += MSG_COMPLETION_CHANGES.format(
            files=diff_stats['files_changed'],
            ins=diff_stats['insertions'],
            dels=diff_stats['deletions'],
        )

    if commits:
        text += MSG_COMPLETION_COMMITS
        for commit in commits:
            text += f"  `{commit}`\n"

    if plan_progress:
        done, total = plan_progress
        pct = int(done / total * 100) if total > 0 else 0
        bar_filled = pct // 10
        bar = "\u2588" * bar_filled + "\u2591" * (10 - bar_filled)
        text += MSG_COMPLETION_PLAN.format(done=done, total=total, pct=pct, bar=bar)

    if next_task:
        next_icon = "\u2261" if next_task.mode == "plan" else "\u25a0"
        text += MSG_COMPLETION_QUEUE_NEXT.format(
            icon=next_icon,
            project=next_task.project,
            mode=next_task.mode.title(),
            iterations=next_task.iterations,
        )

    return text


async def check_task_completion(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job that checks for completed tasks, expired queued tasks, and starts queued ones."""
    results, expired_tasks = task_manager.process_completed_tasks()

    # Notify about expired queued tasks
    for expired in expired_tasks:
        minutes = QUEUE_TTL // 60
        text = MSG_QUEUE_EXPIRED.format(
            project=expired.project,
            mode=expired.mode.title(),
            iterations=expired.iterations,
            minutes=minutes,
        )
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="Markdown",
        )

    for completed_task, next_task in results:
        # Send completion summary for finished task
        if completed_task:
            diff_stats = None
            commits: list[str] = []
            plan_progress = None

            if completed_task.start_commit:
                diff_stats = get_diff_stats(
                    completed_task.project_path, completed_task.start_commit
                )
                commits = get_recent_commits(
                    completed_task.project_path, completed_task.start_commit
                )

            plan_progress = get_plan_progress(completed_task.project_path)

            summary = _format_completion_summary(
                completed_task, diff_stats, commits, plan_progress,
                next_task=next_task,
            )

            buttons = []
            if diff_stats:
                buttons.append(
                    InlineKeyboardButton(
                        MSG_DIFF_SUMMARY_BTN,
                        callback_data=f"completion:diff:{completed_task.project}",
                    )
                )
            buttons.append(
                InlineKeyboardButton(
                    MSG_PROJECT_BTN,
                    callback_data=f"project:{completed_task.project}",
                )
            )
            reply_markup = InlineKeyboardMarkup([buttons])

            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=summary,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )

        # Standalone queue start -- only when no completed task (e.g. bot restarted)
        elif next_task:
            icon = "\u2261" if next_task.mode == "plan" else "\u25a0"
            text = MSG_STARTED_FROM_QUEUE.format(
                icon=icon,
                project=next_task.project,
                mode=next_task.mode.title(),
                iterations=next_task.iterations,
            )
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=text,
                parse_mode="Markdown",
                reply_markup=_nav_keyboard(next_task.project),
            )


async def check_task_progress(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job that sends/edits Telegram messages with iteration progress for active tasks."""
    for task in list(task_manager.active_tasks.values()):
        current = task_manager.get_current_iteration(task)
        if current is None:
            continue

        # Stale detection: .progress file unchanged for >5 minutes while tmux alive
        progress_file = task.project_path / "loop" / "logs" / ".progress"
        try:
            mtime = os.path.getmtime(progress_file)
            stale_seconds = time.time() - mtime
        except OSError:
            stale_seconds = 0

        if (
            stale_seconds > STALE_THRESHOLD
            and not task.stale_warned
            and task_manager._is_session_running(task.session_name)
        ):
            task.stale_warned = True
            minutes = STALE_THRESHOLD // 60
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=MSG_STALE_PROGRESS.format(project=task.project, minutes=minutes),
                parse_mode="Markdown",
            )

        # Only update on iteration change
        if current == task.last_reported_iteration:
            continue

        task.last_reported_iteration = current
        task.stale_warned = False  # Reset stale warning on progress

        icon = "\u25c7" if task.mode == "plan" else "\u25a0"
        elapsed = task_manager.get_task_duration(task)
        text = f"{icon} *{task.project}* \u2014 {MSG_ITERATION_LABEL} {current}/{task.iterations} ({elapsed})"

        if task.progress_message_id is None:
            msg = await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=text,
                parse_mode="Markdown",
            )
            task.progress_message_id = msg.message_id
        else:
            try:
                await context.bot.edit_message_text(
                    chat_id=TELEGRAM_CHAT_ID,
                    message_id=task.progress_message_id,
                    text=text,
                    parse_mode="Markdown",
                )
            except Exception:
                # Message may have been deleted or is unchanged
                logger.debug(f"Could not edit progress message for {task.project}")


async def run_log_rotation(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Daily job that rotates log files and cleans up orphaned brainstorm files."""
    projects_root = Path(PROJECTS_ROOT)
    log_result = rotate_logs(projects_root, retention_days=LOG_RETENTION_DAYS, max_size_mb=LOG_MAX_SIZE_MB)
    bs_result = cleanup_brainstorm_files(projects_root)

    total_deleted = log_result["deleted"] + bs_result["deleted"]
    total_freed = log_result["freed_bytes"] + bs_result["freed_bytes"]

    if total_deleted > 0:
        logger.info(
            "Log rotation: %d files removed, %.1f MB freed",
            total_deleted,
            total_freed / (1024 * 1024),
        )


async def handle_completion_diff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Podsumowanie zmian' button from completion summary."""
    query = update.callback_query
    assert query is not None
    assert query.data is not None
    assert update.effective_chat is not None

    if update.effective_chat.id != TELEGRAM_CHAT_ID:
        await query.answer(MSG_UNAUTHORIZED)
        return

    await query.answer()

    project_name = query.data.replace("completion:diff:", "")
    project = get_project(project_name)

    if not project:
        await query.edit_message_text(f"{MSG_PROJECT_NOT_FOUND}: {project_name}")
        return

    # Get git diff --stat for the project (last commit range)
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", GIT_DIFF_RANGE],
            capture_output=True,
            text=True,
            cwd=project.path,
            timeout=10,
        )
        diff_text = result.stdout.strip() if result.returncode == 0 else MSG_NO_DATA
    except (subprocess.TimeoutExpired, OSError):
        diff_text = MSG_NO_DATA

    # Truncate if too long for Telegram (max ~4096 chars)
    if len(diff_text) > 3500:
        diff_text = diff_text[:3500] + MSG_TRUNCATED

    await query.edit_message_text(
        MSG_DIFF_TITLE.format(project=project_name, diff=diff_text),
        parse_mode="Markdown",
    )
