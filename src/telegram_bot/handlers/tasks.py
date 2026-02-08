"""Task-related handlers: idea input, iteration selection, task start, status, queue."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from ..messages import (
    MSG_ACTIVE_TASKS_TITLE,
    MSG_BACK_BTN,
    MSG_CANCEL_BTN,
    MSG_CANCEL_QUEUE_ITEM,
    MSG_CANCELLED,
    MSG_CUSTOM_AMOUNT_BTN,
    MSG_ENTER_ITERATIONS,
    MSG_GITHUB_SKIP_BTN,
    MSG_IDEA_LABEL,
    MSG_IN_QUEUE,
    MSG_ITERATION_LABEL,
    MSG_ITERATIONS_LABEL,
    MSG_MODE_LABEL,
    MSG_NO_PROJECT_SELECTED,
    MSG_PLAN_ENTER_IDEA,
    MSG_PROJECT_BTN,
    MSG_PROJECT_LABEL,
    MSG_PROJECTS_LIST_BTN,
    MSG_QUEUE_BTN,
    MSG_QUEUE_EMPTY,
    MSG_QUEUE_TITLE,
    MSG_REMOVED_FROM_QUEUE,
    MSG_SELECT_ITERATIONS,
    MSG_SESSION_LABEL,
    MSG_STATUS_TITLE,
    MSG_TASK_ERROR,
    MSG_TASK_NOT_FOUND,
    MSG_TASK_STARTED,
)
from ..tasks import task_manager
from .common import (
    State,
    _cancel_keyboard,
    _nav_keyboard,
    authorized,
    authorized_callback,
    get_user_data,
    reply_text,
)


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
async def skip_idea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip idea input."""
    assert update.effective_chat is not None
    user_data = get_user_data(update.effective_chat.id)
    user_data["idea"] = None

    return await show_iterations_menu(update, context)


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

    # idea:cancel -- project is available since we're in ENTER_IDEA state
    assert update.effective_chat is not None
    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")
    project_name = project.name if project else None
    await query.edit_message_text(
        MSG_CANCELLED,
        reply_markup=_nav_keyboard(project_name),
    )
    return State.SELECT_PROJECT


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
        # Import here to avoid circular dependency
        from .projects import show_projects

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

    mode_icon = "\u25c7" if mode == "plan" else "\u25a0"
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
            mode_icon = "\u25c7" if task.mode == "plan" else "\u25a0"
            duration = task_manager.get_task_duration(task)
            text += f"{mode_icon} *{task.project}*\n"
            current = task_manager.get_current_iteration(task) or "?"
            text += f"   {task.mode.title()} \u2022 {MSG_ITERATION_LABEL}: {current}/{task.iterations} \u2022 {duration}\n\n"

    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(MSG_BACK_BTN, callback_data="action:back")]]
    )
    await reply_text(update, text, reply_markup=reply_markup)
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
            mode_icon = "\u25c7" if task.mode == "plan" else "\u25a0"
            text += f"{i}. {mode_icon} {task.mode.title()} \u2022 {task.iterations} iter"
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


def _handle_task_action(action, query, update, context, user_data, project):
    """Check if action is task-related and return a coroutine, or None."""
    if action == "status":
        return show_status(update, context)

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

        async def _do():
            await query.edit_message_text(
                MSG_PLAN_ENTER_IDEA,
                parse_mode="Markdown",
                reply_markup=idea_keyboard,
            )
            return State.ENTER_IDEA
        return _do()

    if action == "build":
        user_data["mode"] = "build"
        user_data["idea"] = None
        return show_iterations_menu(update, context)

    if action == "attach":
        if project is not None:
            async def _do():
                session = f"loop-{project.name}"
                await query.edit_message_text(
                    MSG_ATTACH_SESSION.format(session=session),
                    parse_mode="Markdown",
                )
                return ConversationHandler.END
            return _do()

        async def _end():
            return ConversationHandler.END
        return _end()

    if action == "queue":
        return show_queue(update, context)

    return None
