"""Telegram bot handlers and callbacks."""

import logging
import os
import subprocess
import time
from enum import IntEnum, auto
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .config import (
    GIT_DIFF_RANGE,
    LOG_MAX_SIZE_MB,
    LOG_RETENTION_DAYS,
    PROJECTS_ROOT,
    QUEUE_TTL,
    STALE_THRESHOLD,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from .log_rotation import cleanup_brainstorm_files, rotate_logs
from .git_utils import get_diff_stats, get_plan_progress, get_recent_commits
from .messages import (
    BRAINSTORM_ERROR_CODES,
    MSG_ACTIVE_BRAINSTORM,
    MSG_ACTIVE_TASKS_TITLE,
    MSG_ATTACH_BTN,
    MSG_ATTACH_SESSION,
    MSG_AVAILABLE_PROJECTS,
    MSG_BACK_BTN,
    MSG_BRAINSTORM_BTN,
    MSG_BRAINSTORM_CANCELLED,
    MSG_BRAINSTORM_CMD_PROMPT_REQUIRED,
    MSG_BRAINSTORM_CMD_USAGE,
    MSG_BRAINSTORM_CLAUDE_THINKING,
    MSG_BRAINSTORM_DONE_BTN,
    MSG_BRAINSTORM_END_BTN,
    MSG_BRAINSTORM_ENTER_TOPIC,
    MSG_BRAINSTORM_HEADER,
    MSG_BRAINSTORM_NO_ACTIVE,
    MSG_BRAINSTORM_NO_SESSION,
    MSG_BRAINSTORM_REPLY_HINT,
    MSG_BRAINSTORM_REPLY_HINT_LONG,
    MSG_BRAINSTORM_RESUME,
    MSG_BRAINSTORM_RUN_PLAN_BTN,
    MSG_BRAINSTORM_SAVE_BTN,
    MSG_BRAINSTORM_SAVING,
    MSG_BRAINSTORM_SESSION_ENDED,
    MSG_BRAINSTORM_STARTING,
    MSG_BRAINSTORM_STARTING_PLAN,
    MSG_BRAINSTORM_THINKING,
    MSG_BRAINSTORM_WHAT_NEXT,
    MSG_BUILD_BTN,
    MSG_CANCEL_BTN,
    MSG_CANCEL_QUEUE_ITEM,
    MSG_CANCELLED,
    MSG_CLONE_REPO_BTN,
    MSG_CLONING_REPO,
    MSG_CREATE_PROJECT_BTN,
    MSG_CREATING_PROJECT,
    MSG_COMPLETION_CHANGES,
    MSG_COMPLETION_COMMITS,
    MSG_COMPLETION_ITERATIONS,
    MSG_COMPLETION_QUEUE_NEXT,
    MSG_COMPLETION_PLAN,
    MSG_COMPLETION_TIME,
    MSG_COMPLETION_TITLE,
    MSG_CUSTOM_AMOUNT_BTN,
    MSG_DIFF_SUMMARY_BTN,
    MSG_DIFF_TITLE,
    MSG_ENTER_ITERATIONS,
    MSG_ENTER_PROJECT_NAME,
    MSG_ENTER_REPO_URL,
    MSG_ENTER_REPO_URL_EMPTY,
    MSG_ENTER_WORKTREE_NAME,
    MSG_GITHUB_CHOICE_PROMPT,
    MSG_GITHUB_CREATING,
    MSG_GITHUB_CREATED,
    MSG_GITHUB_FAILED,
    MSG_GITHUB_PRIVATE_BTN,
    MSG_GITHUB_PUBLIC_BTN,
    MSG_GITHUB_SKIP_BTN,
    MSG_HELP,
    MSG_IDEA_LABEL,
    MSG_IN_QUEUE,
    MSG_INVALID_NAME,
    MSG_ITERATION_LABEL,
    MSG_ITERATIONS_LABEL,
    MSG_LOOP_INIT_BTN,
    MSG_LOOP_INIT_FAIL,
    MSG_LOOP_INIT_OK,
    MSG_LOOP_NOT_INITIALIZED,
    MSG_MODE_LABEL,
    MSG_NEW_WORKTREE_BTN,
    MSG_NO_DATA,
    MSG_NO_PROJECT_SELECTED,
    MSG_NO_PROJECTS,
    MSG_PLAN_BTN,
    MSG_PLAN_ENTER_IDEA,
    MSG_PROJECT_BTN,
    MSG_PROJECT_LABEL,
    MSG_PROJECT_NOT_FOUND,
    MSG_PROJECTS_LIST_BTN,
    MSG_QUEUE_BTN,
    MSG_QUEUE_EMPTY,
    MSG_QUEUE_TITLE,
    MSG_REMOVED_FROM_QUEUE,
    MSG_SELECT_ITERATIONS,
    MSG_SESSION_LABEL,
    MSG_STALE_PROGRESS,
    MSG_QUEUE_EXPIRED,
    MSG_STARTED_FROM_QUEUE,
    MSG_STATUS_BTN,
    MSG_STATUS_FREE,
    MSG_STATUS_RUNNING,
    MSG_STATUS_TITLE,
    MSG_RESUME_SESSION_BTN,
    MSG_TASK_ERROR,
    MSG_TASK_NOT_FOUND,
    MSG_TASK_STARTED,
    MSG_TRUNCATED,
    MSG_UNAUTHORIZED,
)
from .projects import (
    clone_repo,
    create_github_repo,
    create_project,
    create_worktree,
    get_project,
    list_projects,
    validate_project_name,
)
from .tasks import Task, brainstorm_manager, task_manager

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class State(IntEnum):
    """Conversation states."""

    SELECT_PROJECT = auto()
    PROJECT_MENU = auto()
    ENTER_NAME = auto()
    ENTER_IDEA = auto()
    SELECT_ITERATIONS = auto()
    BRAINSTORMING = auto()
    ENTER_BRAINSTORM_PROMPT = auto()
    ENTER_URL = auto()
    ENTER_PROJECT_NAME = auto()
    GITHUB_CHOICE = auto()


# Store conversation data
user_data_store: dict[int, dict] = {}


def authorized(func):
    """Decorator to check if user is authorized."""

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.effective_chat is not None
        chat_id = update.effective_chat.id
        if chat_id != TELEGRAM_CHAT_ID:
            message = update.effective_message
            if message:
                await message.reply_text(MSG_UNAUTHORIZED)
            return ConversationHandler.END
        return await func(update, context)

    return wrapper


def authorized_callback(func):
    """Decorator for callback queries."""

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.effective_chat is not None
        assert update.callback_query is not None
        chat_id = update.effective_chat.id
        if chat_id != TELEGRAM_CHAT_ID:
            await update.callback_query.answer(MSG_UNAUTHORIZED)
            return ConversationHandler.END
        return await func(update, context)

    return wrapper


def get_user_data(chat_id: int) -> dict:
    """Get or create user data dict."""
    return user_data_store.setdefault(chat_id, {})


async def reply_text(update: Update, text: str, reply_markup=None, parse_mode="Markdown"):
    """Send text via callback_query edit or message reply, depending on context."""
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode=parse_mode
        )
    else:
        assert update.message is not None
        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode=parse_mode
        )


def _is_brainstorm_error(error_code: str | None) -> bool:
    """Check if a brainstorm result indicates an error via error code."""
    return error_code is not None and error_code in BRAINSTORM_ERROR_CODES


def _cancel_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    """Return a single-button cancel keyboard for text-input states."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(MSG_CANCEL_BTN, callback_data=callback_data)]]
    )


def _brainstorm_hint_keyboard() -> InlineKeyboardMarkup:
    """Return Done + Cancel keyboard for brainstorm multi-turn replies."""
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(MSG_BRAINSTORM_DONE_BTN, callback_data="bs:done"),
            InlineKeyboardButton(MSG_CANCEL_BTN, callback_data="bs:cancel"),
        ]]
    )


def _brainstorm_hint_long_keyboard() -> InlineKeyboardMarkup:
    """Return Done + Save + Cancel keyboard for first brainstorm response via /brainstorming."""
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(MSG_BRAINSTORM_DONE_BTN, callback_data="bs:done"),
            InlineKeyboardButton(MSG_BRAINSTORM_SAVE_BTN, callback_data="bs:save"),
            InlineKeyboardButton(MSG_CANCEL_BTN, callback_data="bs:cancel"),
        ]]
    )


def _nav_keyboard(project_name: str | None = None) -> InlineKeyboardMarkup:
    """Return navigation buttons for conversation dead-ends.

    When project_name is given, includes a 'View Project' button.
    Always includes a 'Projects' button to go to the project list.
    """
    buttons = []
    if project_name:
        buttons.append(
            InlineKeyboardButton(MSG_PROJECT_BTN, callback_data=f"project:{project_name}")
        )
    buttons.append(
        InlineKeyboardButton(MSG_PROJECTS_LIST_BTN, callback_data="action:back")
    )
    return InlineKeyboardMarkup([buttons])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start and /projects commands."""
    assert update.effective_chat is not None
    assert update.message is not None
    chat_id = update.effective_chat.id
    if chat_id != TELEGRAM_CHAT_ID:
        await update.message.reply_text(MSG_UNAUTHORIZED)
        return ConversationHandler.END

    return await show_projects(update, context)


async def show_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:  # noqa: ARG001
    """Show list of projects as buttons."""
    projects = list_projects()

    if not projects:
        keyboard = [
            [
                InlineKeyboardButton(MSG_CREATE_PROJECT_BTN, callback_data="action:create_project"),
                InlineKeyboardButton(MSG_CLONE_REPO_BTN, callback_data="action:clone"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await reply_text(update, MSG_NO_PROJECTS, reply_markup=reply_markup, parse_mode=None)
        return State.SELECT_PROJECT

    buttons = []
    for project in projects:
        label = project.name
        if task_manager.check_running(project.path):
            label = f"◉ {label}"
        elif project.is_worktree:
            label = f"↳ {label}"
        else:
            label = f"▸ {label}"
        buttons.append(
            InlineKeyboardButton(label, callback_data=f"project:{project.name}")
        )

    # Arrange buttons in rows of 2
    keyboard = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    keyboard.append([
        InlineKeyboardButton(MSG_CREATE_PROJECT_BTN, callback_data="action:create_project"),
        InlineKeyboardButton(MSG_CLONE_REPO_BTN, callback_data="action:clone"),
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await reply_text(update, MSG_AVAILABLE_PROJECTS, reply_markup=reply_markup)
    return State.SELECT_PROJECT


@authorized_callback
async def project_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle project selection."""
    query = update.callback_query
    assert query is not None
    assert query.data is not None
    await query.answer()

    project_name = query.data.replace("project:", "")
    project = get_project(project_name)

    if not project:
        await query.edit_message_text(MSG_PROJECT_NOT_FOUND)
        return ConversationHandler.END

    user_data = get_user_data(update.effective_chat.id)
    user_data["project"] = project

    return await show_project_menu(update, context, project)


async def show_project_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, project) -> int:  # noqa: ARG001
    """Show menu for a specific project."""
    task = task_manager.get_task(project.path)
    queue = task_manager.get_queue(project.path)
    queue_count = len(queue)

    # Check for active brainstorm session on this project
    has_brainstorm = any(
        s.project == project.name and s.status == "ready"
        for s in brainstorm_manager.sessions.values()
    )

    icon = "↳" if project.is_worktree else "▸"
    status = MSG_STATUS_RUNNING if task else MSG_STATUS_FREE
    text = f"{icon} *{project.name}*\n"
    text += f"Branch: `{project.branch}`\n"
    text += f"Status: {status}"
    if project.is_worktree and project.parent_repo:
        text += f"\nParent: `{project.parent_repo}`"
    if queue_count > 0:
        text += f" ({MSG_IN_QUEUE.format(count=queue_count)})"
    if has_brainstorm:
        text += MSG_ACTIVE_BRAINSTORM

    brainstorm_row = [InlineKeyboardButton(MSG_BRAINSTORM_BTN, callback_data="action:brainstorm")]
    if has_brainstorm:
        brainstorm_row.append(InlineKeyboardButton(MSG_RESUME_SESSION_BTN, callback_data="action:resume_brainstorm"))

    if task:
        duration = task_manager.get_task_duration(task)
        current = task_manager.get_current_iteration(task) or "?"
        text += f"\n\n■ {task.mode.title()} • {MSG_ITERATION_LABEL}: {current}/{task.iterations} • {duration}"
        row1 = [
            InlineKeyboardButton(MSG_ATTACH_BTN, callback_data="action:attach"),
            InlineKeyboardButton(MSG_STATUS_BTN, callback_data="action:status"),
        ]
        if queue_count > 0:
            row1.append(
                InlineKeyboardButton(MSG_QUEUE_BTN.format(count=queue_count), callback_data="action:queue")
            )
        buttons = [
            row1,
            [
                InlineKeyboardButton(MSG_PLAN_BTN, callback_data="action:plan"),
                InlineKeyboardButton(MSG_BUILD_BTN, callback_data="action:build"),
            ],
            brainstorm_row,
            [InlineKeyboardButton(MSG_BACK_BTN, callback_data="action:back")],
        ]
    elif project.has_loop:
        buttons = [
            [
                InlineKeyboardButton(MSG_PLAN_BTN, callback_data="action:plan"),
                InlineKeyboardButton(MSG_BUILD_BTN, callback_data="action:build"),
            ],
            brainstorm_row,
            [
                InlineKeyboardButton(MSG_NEW_WORKTREE_BTN, callback_data="action:worktree"),
                InlineKeyboardButton(MSG_STATUS_BTN, callback_data="action:status"),
            ],
            [InlineKeyboardButton(MSG_BACK_BTN, callback_data="action:back")],
        ]
    else:
        text += MSG_LOOP_NOT_INITIALIZED
        buttons = [
            [
                InlineKeyboardButton(MSG_LOOP_INIT_BTN, callback_data="action:loop_init"),
                InlineKeyboardButton(MSG_NEW_WORKTREE_BTN, callback_data="action:worktree"),
            ],
            [InlineKeyboardButton(MSG_BACK_BTN, callback_data="action:back")],
        ]

    reply_markup = InlineKeyboardMarkup(buttons)

    query = update.callback_query
    assert query is not None
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return State.PROJECT_MENU


@authorized_callback
async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle menu action buttons."""
    query = update.callback_query
    assert query is not None
    assert query.data is not None
    assert update.effective_chat is not None
    await query.answer()

    action = query.data.replace("action:", "")
    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")

    if action == "back":
        return await show_projects(update, context)

    if action == "back_to_project":
        if project:
            return await show_project_menu(update, context, project)
        return await show_projects(update, context)

    if action == "status":
        return await show_status(update, context)

    if action == "create_project":
        await query.edit_message_text(
            MSG_ENTER_PROJECT_NAME,
            parse_mode="Markdown",
            reply_markup=_cancel_keyboard("input:cancel"),
        )
        return State.ENTER_PROJECT_NAME

    if action == "clone":
        await query.edit_message_text(
            MSG_ENTER_REPO_URL,
            parse_mode="Markdown",
            reply_markup=_cancel_keyboard("input:cancel"),
        )
        return State.ENTER_URL

    if action == "worktree":
        if project:
            await query.edit_message_text(
                MSG_ENTER_WORKTREE_NAME.format(project=project.name),
                parse_mode="Markdown",
                reply_markup=_cancel_keyboard("input:cancel"),
            )
            return State.ENTER_NAME
        return await show_projects(update, context)

    if action == "loop_init":
        if project:
            from .projects import _run_loop_init

            success = _run_loop_init(project.path)
            if success:
                await query.edit_message_text(MSG_LOOP_INIT_OK.format(name=project.name))
            else:
                await query.edit_message_text(MSG_LOOP_INIT_FAIL.format(name=project.name))
            # Refresh project data
            refreshed = get_project(project.name)
            if refreshed:
                user_data["project"] = refreshed
                return await show_project_menu(update, context, refreshed)
        return await show_projects(update, context)

    if action == "plan":
        user_data["mode"] = "plan"
        idea_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(MSG_GITHUB_SKIP_BTN, callback_data="idea:skip"),
                    InlineKeyboardButton(MSG_CANCEL_BTN, callback_data="idea:cancel"),
                ]
            ]
        )
        await query.edit_message_text(
            MSG_PLAN_ENTER_IDEA,
            parse_mode="Markdown",
            reply_markup=idea_keyboard,
        )
        return State.ENTER_IDEA

    if action == "build":
        user_data["mode"] = "build"
        user_data["idea"] = None
        return await show_iterations_menu(update, context)

    if action == "attach":
        if project is not None:
            session = f"loop-{project.name}"
            await query.edit_message_text(
                MSG_ATTACH_SESSION.format(session=session),
                parse_mode="Markdown",
            )
        return ConversationHandler.END

    if action == "queue":
        return await show_queue(update, context)

    if action == "brainstorm":
        await query.edit_message_text(
            MSG_BRAINSTORM_HEADER.format(project=project.name),
            parse_mode="Markdown",
            reply_markup=_cancel_keyboard("input:cancel"),
        )
        return State.ENTER_BRAINSTORM_PROMPT

    if action == "resume_brainstorm":
        if not project:
            await query.edit_message_text(MSG_NO_PROJECT_SELECTED)
            return ConversationHandler.END
        # Find the session for this project
        session = next(
            (s for s in brainstorm_manager.sessions.values() if s.project == project.name),
            None,
        )
        if not session:
            await query.edit_message_text(MSG_BRAINSTORM_NO_SESSION)
            return ConversationHandler.END
        await query.edit_message_text(
            MSG_BRAINSTORM_RESUME.format(
                project=project.name,
                time=session.started_at.strftime('%H:%M %d.%m'),
            ),
            parse_mode="Markdown",
            reply_markup=_brainstorm_hint_keyboard(),
        )
        return State.BRAINSTORMING

    return State.PROJECT_MENU


async def show_queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:  # noqa: ARG001
    """Show queue for current project."""
    query = update.callback_query
    assert query is not None
    assert update.effective_chat is not None
    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")

    if not project:
        await query.edit_message_text(MSG_NO_PROJECT_SELECTED)
        return ConversationHandler.END

    queue = task_manager.get_queue(project.path)

    if not queue:
        text = MSG_QUEUE_TITLE.format(project=project.name) + MSG_QUEUE_EMPTY
        buttons = [[InlineKeyboardButton(MSG_BACK_BTN, callback_data="action:back_to_project")]]
    else:
        text = MSG_QUEUE_TITLE.format(project=project.name)
        buttons = []
        for i, task in enumerate(queue, 1):
            mode_icon = "◇" if task.mode == "plan" else "■"
            text += f"{i}. {mode_icon} {task.mode.title()} • {task.iterations} iter"
            if task.idea:
                text += f"\n   _{task.idea[:50]}{'...' if len(task.idea) > 50 else ''}_"
            text += "\n\n"
            buttons.append([
                InlineKeyboardButton(
                    MSG_CANCEL_QUEUE_ITEM.format(num=i), callback_data=f"cancel_queue:{task.id}"
                )
            ])
        buttons.append([InlineKeyboardButton(MSG_BACK_BTN, callback_data="action:back_to_project")])

    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return State.PROJECT_MENU


@authorized_callback
async def handle_cancel_queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancellation of queued task."""
    query = update.callback_query
    assert query is not None
    assert query.data is not None
    assert update.effective_chat is not None
    await query.answer()

    task_id = query.data.replace("cancel_queue:", "")
    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")

    if project and task_manager.cancel_queued_task(project.path, task_id):
        await query.answer(MSG_REMOVED_FROM_QUEUE, show_alert=True)
    else:
        await query.answer(MSG_TASK_NOT_FOUND, show_alert=True)

    return await show_queue(update, context)


@authorized
async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle worktree name input."""
    assert update.message is not None
    assert update.message.text is not None
    assert update.effective_chat is not None
    name = update.message.text.strip().lower()

    # Validate name
    if not name or not name.replace("-", "").replace("_", "").isalnum():
        await update.message.reply_text(MSG_INVALID_NAME)
        return State.ENTER_NAME

    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")

    if not project:
        await update.message.reply_text(MSG_NO_PROJECT_SELECTED)
        return ConversationHandler.END

    success, message = create_worktree(project.path, name)

    if success:
        await update.message.reply_text(f"✓ {message}")
        return await start(update, context)
    else:
        await update.message.reply_text(f"✗ {message}")
        return State.ENTER_NAME


@authorized
async def handle_clone_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle git clone URL input."""
    assert update.message is not None
    assert update.message.text is not None
    url = update.message.text.strip()

    if not url:
        await update.message.reply_text(MSG_ENTER_REPO_URL_EMPTY)
        return State.ENTER_URL

    await update.message.reply_text(MSG_CLONING_REPO)

    success, message = clone_repo(url)

    if success:
        await update.message.reply_text(f"✓ {message}")
        return await start(update, context)
    else:
        await update.message.reply_text(f"✗ {message}")
        return State.ENTER_URL


@authorized
async def handle_project_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle project name input for project creation flow."""
    assert update.message is not None
    assert update.message.text is not None
    assert update.effective_chat is not None
    name = update.message.text.strip().lower()

    valid, result = validate_project_name(name)
    if not valid:
        await update.message.reply_text(result, parse_mode="Markdown")
        return State.ENTER_PROJECT_NAME

    await update.message.reply_text(MSG_CREATING_PROJECT)

    success, message = create_project(name)

    if not success:
        await update.message.reply_text(f"\u2717 {message}")
        return State.ENTER_PROJECT_NAME

    # Store created project name for GitHub choice step
    user_data = get_user_data(update.effective_chat.id)
    user_data["created_project_name"] = name

    buttons = [
        [
            InlineKeyboardButton(MSG_GITHUB_PRIVATE_BTN, callback_data="github:private"),
            InlineKeyboardButton(MSG_GITHUB_PUBLIC_BTN, callback_data="github:public"),
        ],
        [InlineKeyboardButton(MSG_GITHUB_SKIP_BTN, callback_data="github:skip")],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        MSG_GITHUB_CHOICE_PROMPT,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return State.GITHUB_CHOICE


@authorized_callback
async def handle_github_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle GitHub repo visibility choice after project creation."""
    query = update.callback_query
    assert query is not None
    assert query.data is not None
    assert update.effective_chat is not None
    await query.answer()

    choice = query.data.replace("github:", "")
    user_data = get_user_data(update.effective_chat.id)
    project_name = user_data.get("created_project_name")

    if not project_name:
        await query.edit_message_text(MSG_NO_PROJECT_SELECTED)
        return ConversationHandler.END

    if choice == "skip":
        project = get_project(project_name)
        if project:
            user_data["project"] = project
            return await show_project_menu(update, context, project)
        return await show_projects(update, context)

    # private or public
    private = choice == "private"
    await query.edit_message_text(MSG_GITHUB_CREATING)

    project_path = Path(PROJECTS_ROOT) / project_name
    success, message = create_github_repo(project_path, project_name, private)

    # Show GitHub result, then navigate to project menu
    project = get_project(project_name)
    if project:
        user_data["project"] = project
        # Send result as a separate message, then show project menu via edit
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode="Markdown",
        )
        return await show_project_menu(update, context, project)

    return await show_projects(update, context)


@authorized
async def handle_idea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle idea input for plan mode."""
    assert update.effective_chat is not None
    assert update.message is not None
    assert update.message.text is not None
    user_data = get_user_data(update.effective_chat.id)
    user_data["idea"] = update.message.text.strip()

    return await show_iterations_menu(update, context)


@authorized
async def handle_brainstorm_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle brainstorm prompt input from button flow."""
    assert update.message is not None
    assert update.effective_chat is not None

    prompt = (update.message.text or "").strip()
    if not prompt:
        await update.message.reply_text(MSG_BRAINSTORM_ENTER_TOPIC)
        return State.ENTER_BRAINSTORM_PROMPT

    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")

    if not project:
        await update.message.reply_text(MSG_NO_PROJECT_SELECTED)
        return ConversationHandler.END

    # Send "thinking" message that we'll update with progress
    thinking_msg = await update.message.reply_text(
        MSG_BRAINSTORM_THINKING.format(project=project.name, status=MSG_BRAINSTORM_STARTING),
        parse_mode="Markdown",
    )

    last_status = MSG_BRAINSTORM_STARTING

    async for error_code, status, is_final in brainstorm_manager.start(
        chat_id=update.effective_chat.id,
        project=project.name,
        project_path=project.path,
        prompt=prompt,
    ):
        if is_final:
            if _is_brainstorm_error(error_code):
                await thinking_msg.edit_text(f"\u2717 {status}", parse_mode="Markdown")
                return ConversationHandler.END

            await thinking_msg.delete()
            await update.message.reply_text(
                f"\u203a *Claude:*\n\n{status}\n\n"
                + MSG_BRAINSTORM_REPLY_HINT,
                parse_mode="Markdown",
                reply_markup=_brainstorm_hint_keyboard(),
            )
            return State.BRAINSTORMING

        if status != last_status:
            last_status = status
            await thinking_msg.edit_text(
                MSG_BRAINSTORM_THINKING.format(project=project.name, status=status),
                parse_mode="Markdown",
            )

    return ConversationHandler.END


@authorized
async def skip_idea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip idea input."""
    assert update.effective_chat is not None
    user_data = get_user_data(update.effective_chat.id)
    user_data["idea"] = None

    return await show_iterations_menu(update, context)


async def show_iterations_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show iteration count selection."""
    assert update.effective_chat is not None
    buttons = [
        [
            InlineKeyboardButton("3", callback_data="iter:3"),
            InlineKeyboardButton("5", callback_data="iter:5"),
            InlineKeyboardButton("10", callback_data="iter:10"),
        ],
        [InlineKeyboardButton(MSG_CUSTOM_AMOUNT_BTN, callback_data="iter:custom")],
        [InlineKeyboardButton(MSG_CANCEL_BTN, callback_data="iter:cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    user_data = get_user_data(update.effective_chat.id)
    mode = user_data.get("mode", "build")
    project = user_data.get("project")

    project_name = project.name if project else "unknown"
    text = MSG_SELECT_ITERATIONS.format(project=project_name, mode=mode)

    await reply_text(update, text, reply_markup=reply_markup)
    return State.SELECT_ITERATIONS


@authorized_callback
async def handle_iterations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle iteration count selection."""
    query = update.callback_query
    assert query is not None
    assert query.data is not None
    await query.answer()

    value = query.data.replace("iter:", "")

    if value == "cancel":
        return await show_projects(update, context)

    if value == "custom":
        await query.edit_message_text(
            MSG_ENTER_ITERATIONS,
            parse_mode="Markdown",
            reply_markup=_cancel_keyboard("iter:cancel"),
        )
        return State.SELECT_ITERATIONS

    user_data = get_user_data(update.effective_chat.id)
    user_data["iterations"] = int(value)

    return await start_task(update, context)


@authorized
async def handle_custom_iterations(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle custom iteration count input."""
    assert update.message is not None
    assert update.message.text is not None
    assert update.effective_chat is not None
    try:
        iterations = int(update.message.text.strip())
        if iterations < 1 or iterations > 100:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("Please enter a number between 1 and 100.")
        return State.SELECT_ITERATIONS

    user_data = get_user_data(update.effective_chat.id)
    user_data["iterations"] = iterations

    return await start_task(update, context)


async def start_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the loop task or add to queue."""
    assert update.effective_chat is not None
    user_data = get_user_data(update.effective_chat.id)
    project = user_data["project"]
    mode = user_data["mode"]
    iterations = user_data["iterations"]
    idea = user_data.get("idea")

    success, message = task_manager.start_task(
        project=project.name,
        project_path=project.path,
        mode=mode,
        iterations=iterations,
        idea=idea,
    )

    mode_icon = "◇" if mode == "plan" else "■"
    is_queued = message.startswith("Queued")

    if success:
        if is_queued:
            text = f"\u2261 *{message}*\n\n"
            text += MSG_PROJECT_LABEL.format(project=project.name)
            text += MSG_MODE_LABEL.format(mode=mode)
            text += MSG_ITERATIONS_LABEL.format(iterations=iterations)
            if idea:
                text += MSG_IDEA_LABEL.format(idea=f"{idea[:100]}{'...' if len(idea) > 100 else ''}")
        else:
            text = MSG_TASK_STARTED.format(icon=mode_icon)
            text += MSG_PROJECT_LABEL.format(project=project.name)
            text += MSG_MODE_LABEL.format(mode=mode)
            text += MSG_ITERATIONS_LABEL.format(iterations=iterations)
            if idea:
                text += MSG_IDEA_LABEL.format(idea=f"{idea[:100]}{'...' if len(idea) > 100 else ''}")
            text += MSG_SESSION_LABEL.format(project=project.name)
    else:
        text = MSG_TASK_ERROR.format(message=message)

    # Context-aware follow-up buttons
    if success and is_queued:
        buttons = [
            InlineKeyboardButton(MSG_QUEUE_BTN.format(count=""), callback_data="action:queue"),
            InlineKeyboardButton(MSG_PROJECT_BTN, callback_data=f"project:{project.name}"),
            InlineKeyboardButton(MSG_PROJECTS_LIST_BTN, callback_data="action:back"),
        ]
    else:
        buttons = [
            InlineKeyboardButton(MSG_PROJECT_BTN, callback_data=f"project:{project.name}"),
            InlineKeyboardButton(MSG_PROJECTS_LIST_BTN, callback_data="action:back"),
        ]
    reply_markup = InlineKeyboardMarkup([buttons])

    await reply_text(update, text, reply_markup=reply_markup)
    return State.SELECT_PROJECT


async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show status of all active tasks."""
    tasks = task_manager.list_active()

    if not tasks:
        text = MSG_STATUS_TITLE
    else:
        text = MSG_ACTIVE_TASKS_TITLE
        for task in tasks:
            mode_icon = "◇" if task.mode == "plan" else "■"
            duration = task_manager.get_task_duration(task)
            text += f"{mode_icon} *{task.project}*\n"
            current = task_manager.get_current_iteration(task) or "?"
            text += f"   {task.mode.title()} • {MSG_ITERATION_LABEL}: {current}/{task.iterations} • {duration}\n\n"

    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(MSG_BACK_BTN, callback_data="action:back")]]
    )
    await reply_text(update, text, reply_markup=reply_markup)
    return State.PROJECT_MENU


@authorized
async def start_brainstorming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /brainstorming <prompt> command to start a brainstorming session."""
    assert update.message is not None
    assert update.effective_chat is not None

    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")

    if not project:
        await update.message.reply_text(MSG_BRAINSTORM_CMD_USAGE)
        return ConversationHandler.END

    # Extract prompt from command
    text = update.message.text or ""
    prompt = text.replace("/brainstorming", "").strip()

    if not prompt:
        await update.message.reply_text(
            MSG_BRAINSTORM_CMD_PROMPT_REQUIRED,
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    # Send "thinking" message that we'll update with progress
    thinking_msg = await update.message.reply_text(
        MSG_BRAINSTORM_THINKING.format(project=project.name, status=MSG_BRAINSTORM_STARTING),
        parse_mode="Markdown",
    )

    last_status = MSG_BRAINSTORM_STARTING

    async for error_code, status, is_final in brainstorm_manager.start(
        chat_id=update.effective_chat.id,
        project=project.name,
        project_path=project.path,
        prompt=prompt,
    ):
        if is_final:
            if _is_brainstorm_error(error_code):
                await thinking_msg.edit_text(f"\u2717 {status}", parse_mode="Markdown")
                return ConversationHandler.END

            await thinking_msg.delete()
            await update.message.reply_text(
                f"\u203a *Claude:*\n\n{status}\n\n"
                + MSG_BRAINSTORM_REPLY_HINT_LONG,
                parse_mode="Markdown",
                reply_markup=_brainstorm_hint_long_keyboard(),
            )
            return State.BRAINSTORMING

        if status != last_status:
            last_status = status
            await thinking_msg.edit_text(
                MSG_BRAINSTORM_THINKING.format(project=project.name, status=status),
                parse_mode="Markdown",
            )

    return ConversationHandler.END


@authorized
async def handle_brainstorm_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user messages during brainstorming session."""
    assert update.message is not None
    assert update.effective_chat is not None

    message = update.message.text or ""
    if not message:
        return State.BRAINSTORMING

    thinking_msg = await update.message.reply_text(
        f"\u2026 _{MSG_BRAINSTORM_CLAUDE_THINKING}_", parse_mode="Markdown"
    )
    last_status = MSG_BRAINSTORM_CLAUDE_THINKING

    async for error_code, status, is_final in brainstorm_manager.respond(
        chat_id=update.effective_chat.id,
        message=message,
    ):
        if is_final:
            if _is_brainstorm_error(error_code):
                await thinking_msg.edit_text(f"\u2717 {status}", parse_mode="Markdown")
                return State.BRAINSTORMING

            await thinking_msg.delete()
            await update.message.reply_text(
                f"\u203a *Claude:*\n\n{status}\n\n"
                + MSG_BRAINSTORM_REPLY_HINT,
                parse_mode="Markdown",
                reply_markup=_brainstorm_hint_keyboard(),
            )
            return State.BRAINSTORMING

        if status != last_status:
            last_status = status
            await thinking_msg.edit_text(f"\u2026 _{status}_", parse_mode="Markdown")

    return State.BRAINSTORMING


@authorized
async def finish_brainstorming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /done and /save commands to finish brainstorming and save to ROADMAP.md."""
    assert update.message is not None
    assert update.effective_chat is not None

    thinking_msg = await update.message.reply_text(MSG_BRAINSTORM_SAVING, parse_mode="Markdown")

    success, message, idea_content = await brainstorm_manager.finish(
        chat_id=update.effective_chat.id
    )

    if not success:
        await thinking_msg.edit_text(f"\u2717 {message}", parse_mode="Markdown")
        return State.BRAINSTORMING

    # Show buttons for next action
    buttons = [
        [
            InlineKeyboardButton(MSG_BRAINSTORM_RUN_PLAN_BTN, callback_data="brainstorm:plan"),
            InlineKeyboardButton(MSG_BRAINSTORM_END_BTN, callback_data="brainstorm:end"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await thinking_msg.edit_text(
        MSG_BRAINSTORM_WHAT_NEXT.format(message=message),
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

    return State.BRAINSTORMING


@authorized_callback
async def handle_brainstorm_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle post-brainstorming action buttons (Run Plan / End)."""
    query = update.callback_query
    assert query is not None
    assert query.data is not None
    assert update.effective_chat is not None
    await query.answer()

    action = query.data.replace("brainstorm:", "")
    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")

    if action == "plan":
        if not project:
            await query.edit_message_text(
                MSG_NO_PROJECT_SELECTED,
                reply_markup=_nav_keyboard(),
            )
            return State.SELECT_PROJECT

        # Start plan mode with saved IDEA
        user_data["mode"] = "plan"
        user_data["idea"] = None  # IDEA already saved to file, loop.sh will read it

        await query.edit_message_text(
            MSG_BRAINSTORM_STARTING_PLAN.format(project=project.name),
            parse_mode="Markdown",
        )

        return await show_iterations_menu(update, context)

    # action == "end"
    project_name = project.name if project else None
    await query.edit_message_text(
        MSG_BRAINSTORM_SESSION_ENDED,
        reply_markup=_nav_keyboard(project_name),
    )
    return State.SELECT_PROJECT


@authorized
async def cancel_brainstorming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel brainstorming session without saving."""
    assert update.message is not None
    assert update.effective_chat is not None

    cancelled = brainstorm_manager.cancel(update.effective_chat.id)
    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")
    project_name = project.name if project else None
    reply_markup = _nav_keyboard(project_name)

    if cancelled:
        await update.message.reply_text(MSG_BRAINSTORM_CANCELLED, reply_markup=reply_markup)
    else:
        await update.message.reply_text(MSG_BRAINSTORM_NO_ACTIVE, reply_markup=reply_markup)

    return State.SELECT_PROJECT


@authorized_callback
async def handle_input_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancel button press in text-input states."""
    query = update.callback_query
    assert query is not None
    await query.answer()
    await query.edit_message_text(
        MSG_CANCELLED,
        reply_markup=_nav_keyboard(),
    )
    return State.SELECT_PROJECT


@authorized_callback
async def handle_idea_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Skip/Cancel button press in ENTER_IDEA state."""
    query = update.callback_query
    assert query is not None
    await query.answer()

    if query.data == "idea:skip":
        assert update.effective_chat is not None
        user_data = get_user_data(update.effective_chat.id)
        user_data["idea"] = None
        return await show_iterations_menu(update, context)

    # idea:cancel — project is available since we're in ENTER_IDEA state
    assert update.effective_chat is not None
    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")
    project_name = project.name if project else None
    await query.edit_message_text(
        MSG_CANCELLED,
        reply_markup=_nav_keyboard(project_name),
    )
    return State.SELECT_PROJECT


@authorized_callback
async def handle_brainstorm_hint_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Done/Save/Cancel button press in BRAINSTORMING state."""
    query = update.callback_query
    assert query is not None
    assert query.data is not None
    assert update.effective_chat is not None
    await query.answer()

    if query.data == "bs:cancel":
        brainstorm_manager.cancel(update.effective_chat.id)
        user_data = get_user_data(update.effective_chat.id)
        project = user_data.get("project")
        project_name = project.name if project else None
        await query.edit_message_text(
            MSG_BRAINSTORM_CANCELLED,
            reply_markup=_nav_keyboard(project_name),
        )
        return State.SELECT_PROJECT

    # bs:done or bs:save — both trigger finish
    success, message, idea_content = await brainstorm_manager.finish(
        chat_id=update.effective_chat.id
    )

    if not success:
        await query.edit_message_text(f"\u2717 {message}", parse_mode="Markdown")
        return State.BRAINSTORMING

    # Show buttons for next action (same as finish_brainstorming)
    buttons = [
        [
            InlineKeyboardButton(MSG_BRAINSTORM_RUN_PLAN_BTN, callback_data="brainstorm:plan"),
            InlineKeyboardButton(MSG_BRAINSTORM_END_BTN, callback_data="brainstorm:end"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(
        MSG_BRAINSTORM_WHAT_NEXT.format(message=message),
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

    return State.BRAINSTORMING


@authorized
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel current operation."""
    assert update.message is not None
    await update.message.reply_text(
        MSG_CANCELLED,
        reply_markup=_nav_keyboard(),
    )
    return State.SELECT_PROJECT


@authorized
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot usage instructions and available commands."""
    assert update.message is not None

    text = MSG_HELP

    await update.message.reply_text(text, reply_markup=_nav_keyboard())
    return None


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
    icon = "◇" if task.mode == "plan" else "■"
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
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        text += MSG_COMPLETION_PLAN.format(done=done, total=total, pct=pct, bar=bar)

    if next_task:
        next_icon = "≡" if next_task.mode == "plan" else "■"
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

        # Standalone queue start — only when no completed task (e.g. bot restarted)
        elif next_task:
            icon = "≡" if next_task.mode == "plan" else "■"
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
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=MSG_STALE_PROGRESS.format(project=task.project),
                parse_mode="Markdown",
            )

        # Only update on iteration change
        if current == task.last_reported_iteration:
            continue

        task.last_reported_iteration = current
        task.stale_warned = False  # Reset stale warning on progress

        icon = "◇" if task.mode == "plan" else "■"
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


def create_application() -> Application:
    """Create and configure the bot application."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("projects", start),
            CommandHandler("status", show_status),
            CommandHandler("brainstorming", start_brainstorming),
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
