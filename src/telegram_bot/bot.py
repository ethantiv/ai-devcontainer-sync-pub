"""Telegram bot — thin wiring layer.

All handler logic lives in the handlers/ package. This module provides
create_application() which wires ConversationHandler states to handlers
and registers background jobs.
"""

import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .config import TELEGRAM_BOT_TOKEN
from .handlers import (
    State,
    _brainstorm_hint_keyboard,
    _brainstorm_hint_long_keyboard,
    _cancel_keyboard,
    _format_completion_summary,
    _nav_keyboard,
    cancel,
    cancel_brainstorming,
    check_task_completion,
    check_task_progress,
    finish_brainstorming,
    handle_brainstorm_action,
    handle_brainstorm_hint_button,
    handle_brainstorm_message,
    handle_brainstorm_prompt,
    handle_cancel_queue,
    handle_clone_url,
    handle_completion_diff,
    handle_custom_iterations,
    handle_github_choice,
    handle_idea,
    handle_idea_button,
    handle_input_cancel,
    handle_iterations,
    handle_name,
    handle_project_name,
    help_command,
    project_selected,
    run_log_rotation,
    show_brainstorm_history,
    show_project_menu,
    show_projects,
    show_status,
    skip_idea,
    start,
    start_brainstorming,
    start_task,
    user_data_store,
)
from .handlers.brainstorm import _handle_brainstorm_action_dispatch
from .handlers.common import authorized_callback, get_user_data
from .handlers.projects import _handle_project_action
from .handlers.tasks import _handle_task_action, show_iterations_menu

logger = logging.getLogger(__name__)


@authorized_callback
async def handle_action(update, context):
    """Thin router that delegates action: callbacks to domain-specific sub-dispatchers."""
    query = update.callback_query
    assert query is not None
    assert query.data is not None
    assert update.effective_chat is not None
    await query.answer()

    action = query.data.replace("action:", "")
    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")

    # Try each domain sub-dispatcher in order
    result = _handle_project_action(action, query, update, context, user_data, project)
    if result is not None:
        return await result

    result = _handle_task_action(action, query, update, context, user_data, project)
    if result is not None:
        return await result

    result = _handle_brainstorm_action_dispatch(action, query, update, context, user_data, project)
    if result is not None:
        return await result

    return State.PROJECT_MENU


def create_application() -> Application:
    """Create and configure the bot application."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("projects", start),
            CommandHandler("status", show_status),
            CommandHandler("brainstorming", start_brainstorming),
            CommandHandler("history", show_brainstorm_history),
        ],
        states={
            State.SELECT_PROJECT: [
                CallbackQueryHandler(project_selected, pattern=r"^project:"),
                CallbackQueryHandler(handle_action, pattern=r"^action:"),
            ],
            State.PROJECT_MENU: [
                CallbackQueryHandler(handle_action, pattern=r"^action:"),
                CallbackQueryHandler(handle_cancel_queue, pattern=r"^cancel_queue:"),
                CallbackQueryHandler(project_selected, pattern=r"^project:"),
            ],
            State.ENTER_NAME: [
                CallbackQueryHandler(handle_input_cancel, pattern=r"^input:cancel$"),
                CommandHandler("cancel", cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name),
            ],
            State.ENTER_URL: [
                CallbackQueryHandler(handle_input_cancel, pattern=r"^input:cancel$"),
                CommandHandler("cancel", cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_clone_url),
            ],
            State.ENTER_IDEA: [
                CallbackQueryHandler(handle_idea_button, pattern=r"^idea:"),
                CommandHandler("cancel", cancel),
                CommandHandler("skip", skip_idea),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_idea),
            ],
            State.ENTER_BRAINSTORM_PROMPT: [
                CallbackQueryHandler(handle_input_cancel, pattern=r"^input:cancel$"),
                CommandHandler("cancel", cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_brainstorm_prompt),
            ],
            State.SELECT_ITERATIONS: [
                CallbackQueryHandler(handle_iterations, pattern=r"^iter:"),
                CommandHandler("cancel", cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_iterations),
            ],
            State.ENTER_PROJECT_NAME: [
                CallbackQueryHandler(handle_input_cancel, pattern=r"^input:cancel$"),
                CommandHandler("cancel", cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_project_name),
            ],
            State.GITHUB_CHOICE: [
                CallbackQueryHandler(handle_github_choice, pattern=r"^github:"),
            ],
            State.BRAINSTORMING: [
                CommandHandler("done", finish_brainstorming),
                CommandHandler("save", finish_brainstorming),
                CommandHandler("cancel", cancel_brainstorming),
                CallbackQueryHandler(handle_brainstorm_hint_button, pattern=r"^bs:"),
                CallbackQueryHandler(handle_brainstorm_action, pattern=r"^brainstorm:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_brainstorm_message),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
            CommandHandler("help", help_command),
        ],
    )

    app.add_handler(conv_handler)

    # Standalone handler for completion summary buttons (sent outside conversation)
    app.add_handler(CallbackQueryHandler(handle_completion_diff, pattern=r"^completion:diff:"))

    # Job to check for completed tasks every 30 seconds
    if app.job_queue:
        app.job_queue.run_repeating(check_task_completion, interval=30, first=10)
        app.job_queue.run_repeating(check_task_progress, interval=15, first=15)
        app.job_queue.run_repeating(run_log_rotation, interval=86400, first=60)
        logger.info("JobQueue registered: check_task_completion every 30s, check_task_progress every 15s, run_log_rotation daily")
    else:
        logger.warning(
            "JobQueue is None! Queue processing disabled. "
            "Install APScheduler: pip install 'python-telegram-bot[job-queue]'"
        )

    return app
