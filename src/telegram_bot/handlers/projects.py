"""Project-related handlers: listing, selection, creation, cloning, worktrees, sync."""

from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from ..config import PROJECTS_PER_PAGE, PROJECTS_ROOT, TELEGRAM_CHAT_ID
from ..git_utils import check_remote_updates, pull_project
from ..messages import (
    MSG_ACTIVE_BRAINSTORM,
    MSG_ATTACH_BTN,
    MSG_ATTACH_SESSION,
    MSG_AVAILABLE_PROJECTS,
    MSG_BACK_BTN,
    MSG_BRAINSTORM_BTN,
    MSG_BUILD_BTN,
    MSG_CANCEL_BTN,
    MSG_CLONE_REPO_BTN,
    MSG_CLONING_REPO,
    MSG_CREATE_PROJECT_BTN,
    MSG_PAGE_INDICATOR,
    MSG_PAGE_NEXT_BTN,
    MSG_PAGE_PREV_BTN,
    MSG_CREATING_PROJECT,
    MSG_ENTER_PROJECT_NAME,
    MSG_ENTER_REPO_URL,
    MSG_ENTER_REPO_URL_EMPTY,
    MSG_ENTER_WORKTREE_NAME,
    MSG_GITHUB_CHOICE_PROMPT,
    MSG_GITHUB_CREATING,
    MSG_GITHUB_PRIVATE_BTN,
    MSG_GITHUB_PUBLIC_BTN,
    MSG_GITHUB_SKIP_BTN,
    MSG_IN_QUEUE,
    MSG_INVALID_NAME,
    MSG_ITERATION_LABEL,
    MSG_LOOP_INIT_BTN,
    MSG_LOOP_INIT_FAIL,
    MSG_LOOP_INIT_OK,
    MSG_LOOP_NOT_INITIALIZED,
    MSG_NEW_WORKTREE_BTN,
    MSG_NO_PROJECT_SELECTED,
    MSG_NO_PROJECTS,
    MSG_PLAN_BTN,
    MSG_PROJECT_BTN,
    MSG_PROJECT_NOT_FOUND,
    MSG_PROJECTS_LIST_BTN,
    MSG_QUEUE_BTN,
    MSG_RESUME_SESSION_BTN,
    MSG_STATUS_BTN,
    MSG_STATUS_FREE,
    MSG_STATUS_RUNNING,
    MSG_SYNC_BTN,
    MSG_SYNC_BTN_WITH_COUNT,
    MSG_SYNC_FAILED,
    MSG_SYNC_NO_UPDATES,
    MSG_SYNC_PULLING,
    MSG_SYNC_SUCCESS,
    MSG_TASK_HISTORY_BTN,
    MSG_UNAUTHORIZED,
)
from ..projects import (
    clone_repo,
    create_github_repo,
    create_project,
    create_worktree,
    get_project,
    list_projects,
    validate_project_name,
)
from ..tasks import brainstorm_manager, task_manager
from .common import (
    State,
    _cancel_keyboard,
    authorized,
    authorized_callback,
    get_user_data,
    reply_text,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start and /projects commands."""
    assert update.effective_chat is not None
    assert update.message is not None
    chat_id = update.effective_chat.id
    if chat_id != TELEGRAM_CHAT_ID:
        await update.message.reply_text(MSG_UNAUTHORIZED)
        return ConversationHandler.END

    # Reset page to first page on explicit /start or /projects
    user_data = get_user_data(chat_id)
    user_data["projects_page"] = 0

    return await show_projects(update, context)


async def show_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:  # noqa: ARG001
    """Show list of projects as buttons with pagination."""
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

    # Pagination state
    chat_id = update.effective_chat.id if update.effective_chat else 0
    user_data = get_user_data(chat_id)
    total_pages = max(1, -(-len(projects) // PROJECTS_PER_PAGE))  # ceil division
    page = user_data.get("projects_page", 0)
    # Clamp page to valid range
    page = max(0, min(page, total_pages - 1))
    user_data["projects_page"] = page

    # Slice projects for current page
    start_idx = page * PROJECTS_PER_PAGE
    page_projects = projects[start_idx : start_idx + PROJECTS_PER_PAGE]

    buttons = []
    for project in page_projects:
        label = project.name
        if task_manager.check_running(project.path):
            label = f"\u25c9 {label}"
        elif project.is_worktree:
            label = f"\u21b3 {label}"
        else:
            label = f"\u25b8 {label}"
        buttons.append(
            InlineKeyboardButton(label, callback_data=f"project:{project.name}")
        )

    # Arrange buttons in rows of 2
    keyboard = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]

    # Prev/Next navigation row (only when multiple pages)
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(MSG_PAGE_PREV_BTN, callback_data="page:prev"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(MSG_PAGE_NEXT_BTN, callback_data="page:next"))
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton(MSG_CREATE_PROJECT_BTN, callback_data="action:create_project"),
        InlineKeyboardButton(MSG_CLONE_REPO_BTN, callback_data="action:clone"),
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Message text with optional page indicator
    text = MSG_AVAILABLE_PROJECTS
    if total_pages > 1:
        text += f"\n{MSG_PAGE_INDICATOR.format(current=page + 1, total=total_pages)}"

    await reply_text(update, text, reply_markup=reply_markup)
    return State.SELECT_PROJECT


@authorized_callback
async def handle_page_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle page:prev / page:next callbacks for project list pagination."""
    query = update.callback_query
    assert query is not None
    assert query.data is not None
    await query.answer()

    direction = query.data.replace("page:", "")
    user_data = get_user_data(update.effective_chat.id)
    page = user_data.get("projects_page", 0)

    if direction == "next":
        user_data["projects_page"] = page + 1
    elif direction == "prev":
        user_data["projects_page"] = max(0, page - 1)

    # show_projects will clamp the page if out of range
    return await show_projects(update, context)


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

    # Check for remote updates (sync button label)
    remote_count = check_remote_updates(project.path) if (task or project.has_loop) else 0
    if remote_count > 0:
        sync_label = MSG_SYNC_BTN_WITH_COUNT.format(count=remote_count)
    else:
        sync_label = MSG_SYNC_BTN

    icon = "\u21b3" if project.is_worktree else "\u25b8"
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

    sync_btn = InlineKeyboardButton(sync_label, callback_data="action:sync")

    history_btn = InlineKeyboardButton(MSG_TASK_HISTORY_BTN, callback_data="action:task_history")

    if task:
        duration = task_manager.get_task_duration(task)
        current = task_manager.get_current_iteration(task) or "?"
        text += f"\n\n\u25a0 {task.mode.title()} \u2022 {MSG_ITERATION_LABEL}: {current}/{task.iterations} \u2022 {duration}"
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
            [history_btn, sync_btn, InlineKeyboardButton(MSG_BACK_BTN, callback_data="action:back")],
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
                history_btn,
            ],
            [sync_btn, InlineKeyboardButton(MSG_BACK_BTN, callback_data="action:back")],
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
        await update.message.reply_text(f"\u2713 {message}")
        return await start(update, context)
    else:
        await update.message.reply_text(f"\u2717 {message}")
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
        await update.message.reply_text(f"\u2713 {message}")
        return await start(update, context)
    else:
        await update.message.reply_text(f"\u2717 {message}")
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


def _handle_project_action(action, query, update, context, user_data, project):
    """Check if action is project-related and return a coroutine, or None."""
    if action == "back":
        return show_projects(update, context)

    if action == "back_to_project":
        if project:
            return show_project_menu(update, context, project)
        return show_projects(update, context)

    if action == "create_project":
        async def _do():
            await query.edit_message_text(
                MSG_ENTER_PROJECT_NAME,
                parse_mode="Markdown",
                reply_markup=_cancel_keyboard("input:cancel"),
            )
            return State.ENTER_PROJECT_NAME
        return _do()

    if action == "clone":
        async def _do():
            await query.edit_message_text(
                MSG_ENTER_REPO_URL,
                parse_mode="Markdown",
                reply_markup=_cancel_keyboard("input:cancel"),
            )
            return State.ENTER_URL
        return _do()

    if action == "worktree":
        if project:
            async def _do():
                await query.edit_message_text(
                    MSG_ENTER_WORKTREE_NAME.format(project=project.name),
                    parse_mode="Markdown",
                    reply_markup=_cancel_keyboard("input:cancel"),
                )
                return State.ENTER_NAME
            return _do()
        return show_projects(update, context)

    if action == "loop_init":
        if project:
            async def _do():
                from ..projects import _run_loop_init

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
            return _do()
        return show_projects(update, context)

    if action == "sync":
        if not project:
            return show_projects(update, context)

        async def _do():
            await query.edit_message_text(MSG_SYNC_PULLING, parse_mode="Markdown")
            success, message = pull_project(project.path)
            if success:
                if "Already up to date" in message:
                    await query.edit_message_text(MSG_SYNC_NO_UPDATES)
                else:
                    await query.edit_message_text(
                        MSG_SYNC_SUCCESS.format(message=message),
                        parse_mode="Markdown",
                    )
            else:
                await query.edit_message_text(
                    MSG_SYNC_FAILED.format(message=message),
                    parse_mode="Markdown",
                )
            # Refresh project data and show menu
            refreshed = get_project(project.name)
            if refreshed:
                user_data["project"] = refreshed
                return await show_project_menu(update, context, refreshed)
            return await show_projects(update, context)
        return _do()

    return None
