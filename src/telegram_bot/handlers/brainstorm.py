"""Brainstorm-related handlers: start, message, finish, cancel, history, actions."""

from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from ..messages import (
    MSG_BRAINSTORM_CANCELLED,
    MSG_BRAINSTORM_CLAUDE_THINKING,
    MSG_BRAINSTORM_CMD_PROMPT_REQUIRED,
    MSG_BRAINSTORM_CMD_USAGE,
    MSG_BRAINSTORM_CONTINUE_BTN,
    MSG_BRAINSTORM_CONTINUE_NO_SESSION,
    MSG_BRAINSTORM_CONTINUE_RESUMING,
    MSG_BRAINSTORM_END_BTN,
    MSG_BRAINSTORM_EXPORT_BTN,
    MSG_BRAINSTORM_EXPORT_FAIL,
    MSG_BRAINSTORM_EXPORT_SUCCESS,
    MSG_BRAINSTORM_HISTORY_EMPTY,
    MSG_BRAINSTORM_HISTORY_TITLE,
    MSG_BRAINSTORM_NO_ACTIVE,
    MSG_BRAINSTORM_NO_SESSION,
    MSG_BRAINSTORM_REPLY_HINT,
    MSG_BRAINSTORM_REPLY_HINT_LONG,
    MSG_BRAINSTORM_RESUME,
    MSG_BRAINSTORM_RUN_PLAN_BTN,
    MSG_BRAINSTORM_SAVING,
    MSG_BRAINSTORM_SESSION_ENDED,
    MSG_BRAINSTORM_SESSION_ENTRY,
    MSG_BRAINSTORM_STARTING,
    MSG_BRAINSTORM_STARTING_PLAN,
    MSG_BRAINSTORM_THINKING,
    MSG_BRAINSTORM_WHAT_NEXT,
    MSG_BRAINSTORM_ENTER_TOPIC,
    MSG_BRAINSTORM_HEADER,
    MSG_NO_PROJECT_SELECTED,
)
from ..tasks import brainstorm_manager
from .common import (
    State,
    _brainstorm_hint_keyboard,
    _brainstorm_hint_long_keyboard,
    _is_brainstorm_error,
    _nav_keyboard,
    authorized,
    authorized_callback,
    get_user_data,
)


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
async def show_brainstorm_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /history command to show brainstorm session history."""
    assert update.message is not None

    # Check if a project filter was given
    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")
    project_name = project.name if project else None

    history = brainstorm_manager.list_brainstorm_history(project=project_name)

    if not history:
        reply_markup = _nav_keyboard(project_name)
        await update.message.reply_text(
            MSG_BRAINSTORM_HISTORY_EMPTY, reply_markup=reply_markup
        )
        return State.SELECT_PROJECT

    # Show up to 10 most recent entries
    PAGE_SIZE = 10
    text = MSG_BRAINSTORM_HISTORY_TITLE
    export_buttons = []
    for i, entry in enumerate(history[:PAGE_SIZE], 1):
        finished_at = entry.get("finished_at", "")
        try:
            dt = datetime.fromisoformat(finished_at)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            date_str = "unknown"

        text += MSG_BRAINSTORM_SESSION_ENTRY.format(
            num=i,
            project=entry.get("project", "?"),
            topic=entry.get("topic", "?"),
            date=date_str,
            turns=entry.get("turns", 0),
        )
        text += "\n"

        # Add export button only for entries with conversation data
        if entry.get("conversation"):
            export_buttons.append(
                InlineKeyboardButton(
                    MSG_BRAINSTORM_EXPORT_BTN.format(num=i),
                    callback_data=f"bs:export:{i - 1}",
                )
            )

    if len(history) > PAGE_SIZE:
        text += f"_...and {len(history) - PAGE_SIZE} more_\n"

    # Build keyboard: export buttons in rows of 3, plus nav buttons
    buttons = []
    for j in range(0, len(export_buttons), 3):
        buttons.append(export_buttons[j:j + 3])

    nav = _nav_keyboard(project_name)
    buttons.extend(nav.inline_keyboard)

    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return State.SELECT_PROJECT


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

        # Import here to avoid circular dependency
        from .tasks import show_iterations_menu

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

    # bs:done or bs:save -- both trigger finish
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


@authorized_callback
async def handle_brainstorm_continue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Continue last' button to resume an archived brainstorm session."""
    query = update.callback_query
    assert query is not None
    assert update.effective_chat is not None
    await query.answer()

    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")

    if not project:
        await query.edit_message_text(MSG_NO_PROJECT_SELECTED)
        return ConversationHandler.END

    resumable = brainstorm_manager.get_resumable_session(project.name)
    if not resumable:
        await query.edit_message_text(
            MSG_BRAINSTORM_CONTINUE_NO_SESSION,
            reply_markup=_nav_keyboard(project.name),
        )
        return State.SELECT_PROJECT

    topic = resumable.get("topic", "")[:60]
    await query.edit_message_text(
        MSG_BRAINSTORM_CONTINUE_RESUMING.format(project=project.name, topic=topic),
        parse_mode="Markdown",
    )

    last_status = MSG_BRAINSTORM_STARTING

    async for error_code, status, is_final in brainstorm_manager.resume_archived_session(
        chat_id=update.effective_chat.id,
        project=project.name,
        project_path=project.path,
        history_entry=resumable,
    ):
        if is_final:
            if _is_brainstorm_error(error_code):
                await query.edit_message_text(f"\u2717 {status}", parse_mode="Markdown")
                return ConversationHandler.END

            await query.edit_message_text(
                f"\u203a *Claude:*\n\n{status}\n\n"
                + MSG_BRAINSTORM_REPLY_HINT,
                parse_mode="Markdown",
                reply_markup=_brainstorm_hint_keyboard(),
            )
            return State.BRAINSTORMING

        if status != last_status:
            last_status = status
            await query.edit_message_text(
                MSG_BRAINSTORM_THINKING.format(project=project.name, status=status),
                parse_mode="Markdown",
            )

    return ConversationHandler.END


@authorized_callback
async def handle_brainstorm_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle export button press from brainstorm history."""
    query = update.callback_query
    assert query is not None
    assert query.data is not None
    await query.answer()

    # Parse index from callback data: bs:export:{index}
    try:
        index = int(query.data.split(":")[-1])
    except (ValueError, IndexError):
        await query.edit_message_text(MSG_BRAINSTORM_EXPORT_FAIL.format(message="Invalid export index."))
        return State.SELECT_PROJECT

    success, message, _ = brainstorm_manager.export_session(index)

    if success:
        await query.edit_message_text(
            MSG_BRAINSTORM_EXPORT_SUCCESS.format(message=message),
            parse_mode="Markdown",
            reply_markup=_nav_keyboard(),
        )
    else:
        await query.edit_message_text(
            MSG_BRAINSTORM_EXPORT_FAIL.format(message=message),
            reply_markup=_nav_keyboard(),
        )

    return State.SELECT_PROJECT


def _handle_brainstorm_action_dispatch(action, query, update, context, user_data, project):
    """Check if action is brainstorm-related and return a coroutine, or None."""
    if action == "brainstorm":
        async def _do_brainstorm():
            # Build keyboard: Cancel + optional Continue last
            buttons = [[InlineKeyboardButton(
                "\u2717 Cancel", callback_data="input:cancel",
            )]]
            resumable = brainstorm_manager.get_resumable_session(project.name)
            if resumable:
                buttons.insert(0, [InlineKeyboardButton(
                    MSG_BRAINSTORM_CONTINUE_BTN,
                    callback_data="bs:continue",
                )])
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.edit_message_text(
                MSG_BRAINSTORM_HEADER.format(project=project.name),
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
            return State.ENTER_BRAINSTORM_PROMPT
        return _do_brainstorm()

    if action == "resume_brainstorm":
        if not project:
            async def _no_project():
                await query.edit_message_text(MSG_NO_PROJECT_SELECTED)
                return ConversationHandler.END
            return _no_project()

        # Find the session for this project
        session = next(
            (s for s in brainstorm_manager.sessions.values() if s.project == project.name),
            None,
        )
        if not session:
            async def _no_session():
                await query.edit_message_text(MSG_BRAINSTORM_NO_SESSION)
                return ConversationHandler.END
            return _no_session()

        async def _do():
            await query.edit_message_text(
                MSG_BRAINSTORM_RESUME.format(
                    project=project.name,
                    time=session.started_at.strftime('%H:%M %d.%m'),
                ),
                parse_mode="Markdown",
                reply_markup=_brainstorm_hint_keyboard(),
            )
            return State.BRAINSTORMING
        return _do()

    return None
