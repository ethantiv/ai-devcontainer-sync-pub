"""Telegram bot handlers and callbacks."""

import logging
from enum import IntEnum, auto

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

from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from .projects import create_worktree, get_project, list_projects
from .tasks import brainstorm_manager, task_manager

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
                await message.reply_text("Unauthorized")
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
            await update.callback_query.answer("Unauthorized")
            return ConversationHandler.END
        return await func(update, context)

    return wrapper


def get_user_data(chat_id: int) -> dict:
    """Get or create user data dict."""
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {}
    return user_data_store[chat_id]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start and /projects commands."""
    assert update.effective_chat is not None
    assert update.message is not None
    chat_id = update.effective_chat.id
    if chat_id != TELEGRAM_CHAT_ID:
        await update.message.reply_text("Unauthorized")
        return ConversationHandler.END

    return await show_projects(update, context)


async def show_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:  # noqa: ARG001
    """Show list of projects as buttons."""
    projects = list_projects()

    if not projects:
        text = "No projects found. Check PROJECTS_ROOT configuration."
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            assert update.message is not None
            await update.message.reply_text(text)
        return ConversationHandler.END

    buttons = []
    for project in projects:
        label = project.name
        if project.is_main:
            label = f"📂 {label}"
        elif task_manager.check_running(project.path):
            label = f"🔄 {label}"
        else:
            label = f"📁 {label}"
        buttons.append(
            InlineKeyboardButton(label, callback_data=f"project:{project.name}")
        )

    # Arrange buttons in rows of 2
    keyboard = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "📂 *Dostępne projekty:*"
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )
    else:
        assert update.message is not None
        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

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
        await query.edit_message_text("Project not found")
        return ConversationHandler.END

    user_data = get_user_data(update.effective_chat.id)
    user_data["project"] = project

    return await show_project_menu(update, context, project)


async def show_project_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, project) -> int:  # noqa: ARG001
    """Show menu for a specific project."""
    task = task_manager.get_task(project.path)
    queue = task_manager.get_queue(project.path)
    queue_count = len(queue)

    if project.is_main:
        # Main repo - can create new worktrees
        text = f"📁 *{project.name}* (main)\n"
        text += f"Branch: `{project.branch}`"

        buttons = [
            [
                InlineKeyboardButton("➕ Nowy projekt", callback_data="action:new"),
                InlineKeyboardButton("📊 Status", callback_data="action:status"),
            ],
            [InlineKeyboardButton("⬅️ Powrót", callback_data="action:back")],
        ]
    else:
        # Worktree - can run plan/build
        status = "🔄 Zadanie w toku" if task else "🟢 Wolny"
        text = f"📁 *{project.name}*\n"
        text += f"Branch: `{project.branch}`\n"
        text += f"Status: {status}"
        if queue_count > 0:
            text += f" ({queue_count} w kolejce)"

        if task:
            duration = task_manager.get_task_duration(task)
            current = task_manager.get_current_iteration(task) or "?"
            text += f"\n\n🔨 {task.mode.title()} • Iteracja: {current}/{task.iterations} • {duration}"
            row1 = [
                InlineKeyboardButton("📺 Podłącz", callback_data="action:attach"),
                InlineKeyboardButton("📊 Status", callback_data="action:status"),
            ]
            if queue_count > 0:
                row1.append(
                    InlineKeyboardButton(f"📋 Kolejka ({queue_count})", callback_data="action:queue")
                )
            buttons = [
                row1,
                [
                    InlineKeyboardButton("🧐 Plan", callback_data="action:plan"),
                    InlineKeyboardButton("💪 Build", callback_data="action:build"),
                ],
                [
                    InlineKeyboardButton("💡 Brainstorm", callback_data="action:brainstorm"),
                ],
                [InlineKeyboardButton("⬅️ Powrót", callback_data="action:back")],
            ]
        else:
            if project.has_loop:
                buttons = [
                    [
                        InlineKeyboardButton("🧐 Plan", callback_data="action:plan"),
                        InlineKeyboardButton("💪 Build", callback_data="action:build"),
                    ],
                    [
                        InlineKeyboardButton("💡 Brainstorm", callback_data="action:brainstorm"),
                    ],
                    [
                        InlineKeyboardButton("📊 Status", callback_data="action:status"),
                        InlineKeyboardButton("⬅️ Powrót", callback_data="action:back"),
                    ],
                ]
            else:
                text += "\n\n⚠️ Loop not available (loop/loop.sh not found)"
                buttons = [
                    [InlineKeyboardButton("⬅️ Powrót", callback_data="action:back")],
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

    if action == "new":
        await query.edit_message_text(
            "📝 *Podaj nazwę projektu:*\n\n"
            f"Utworzę: `{{name}}`\n"
            "Branch: `{name}`\n\n"
            "Wyślij /cancel aby anulować.",
            parse_mode="Markdown",
        )
        return State.ENTER_NAME

    if action == "plan":
        user_data["mode"] = "plan"
        await query.edit_message_text(
            "📝 *Plan: Opisz ideę*\n\n"
            "Wpisz opis funkcjonalności lub wyślij /skip aby pominąć.\n"
            "Wyślij /cancel aby anulować.",
            parse_mode="Markdown",
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
                f"📺 *Podłącz do sesji:*\n\n`tmux attach -t {session}`",
                parse_mode="Markdown",
            )
        return ConversationHandler.END

    if action == "queue":
        return await show_queue(update, context)

    if action == "brainstorm":
        await query.edit_message_text(
            "🧠 *Brainstorming*\n\n"
            f"Projekt: `{project.name}`\n\n"
            "Opisz temat/pomysł do dyskusji:\n\n"
            "Wyślij /cancel aby anulować.",
            parse_mode="Markdown",
        )
        return State.ENTER_BRAINSTORM_PROMPT

    return State.PROJECT_MENU


async def show_queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:  # noqa: ARG001
    """Show queue for current project."""
    query = update.callback_query
    assert query is not None
    assert update.effective_chat is not None
    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")

    if not project:
        await query.edit_message_text("Brak wybranego projektu")
        return ConversationHandler.END

    queue = task_manager.get_queue(project.path)

    if not queue:
        text = f"📋 *Kolejka dla {project.name}*\n\nKolejka jest pusta."
        buttons = [[InlineKeyboardButton("⬅️ Powrót", callback_data="action:back_to_project")]]
    else:
        text = f"📋 *Kolejka dla {project.name}*\n\n"
        buttons = []
        for i, task in enumerate(queue, 1):
            mode_icon = "📋" if task.mode == "plan" else "🔨"
            text += f"{i}. {mode_icon} {task.mode.title()} • {task.iterations} iter"
            if task.idea:
                text += f"\n   _{task.idea[:50]}{'...' if len(task.idea) > 50 else ''}_"
            text += "\n\n"
            buttons.append([
                InlineKeyboardButton(
                    f"❌ Anuluj #{i}", callback_data=f"cancel_queue:{task.id}"
                )
            ])
        buttons.append([InlineKeyboardButton("⬅️ Powrót", callback_data="action:back_to_project")])

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
        await query.answer("Usunięto z kolejki", show_alert=True)
    else:
        await query.answer("Nie znaleziono zadania", show_alert=True)

    return await show_queue(update, context)


@authorized
async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle new project name input."""
    assert update.message is not None
    assert update.message.text is not None
    name = update.message.text.strip().lower()

    # Validate name
    if not name or not name.replace("-", "").replace("_", "").isalnum():
        await update.message.reply_text(
            "Invalid name. Use only letters, numbers, dashes and underscores."
        )
        return State.ENTER_NAME

    success, message = create_worktree(name)

    if success:
        await update.message.reply_text(f"✅ {message}")
        # Refresh project list
        return await start(update, context)
    else:
        await update.message.reply_text(f"❌ {message}")
        return State.ENTER_NAME


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
        await update.message.reply_text("❌ Podaj temat brainstorming.")
        return State.ENTER_BRAINSTORM_PROMPT

    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")

    if not project:
        await update.message.reply_text("❌ Brak wybranego projektu.")
        return ConversationHandler.END

    # Send "thinking" message that we'll update with progress
    thinking_msg = await update.message.reply_text(
        f"🧠 *Brainstorming*\n\nProjekt: `{project.name}`\n_Uruchamiam Claude..._",
        parse_mode="Markdown",
    )

    last_status = "Uruchamiam Claude..."  # Track last status to avoid redundant edits

    async for status, is_final in brainstorm_manager.start(
        chat_id=update.effective_chat.id,
        project=project.name,
        project_path=project.path,
        prompt=prompt,
    ):
        if is_final:
            if status.startswith("Sesja brainstorming już") or "Nie udało" in status or "Timeout" in status or "error" in status.lower():
                await thinking_msg.edit_text(f"❌ {status}", parse_mode="Markdown")
                return ConversationHandler.END

            # Success - delete thinking message and send response
            await thinking_msg.delete()
            await update.message.reply_text(
                f"🤖 *Claude:*\n\n{status}\n\n"
                "_Odpowiedz aby kontynuować. Użyj /done aby zapisać, /cancel aby anulować._",
                parse_mode="Markdown",
            )
            return State.BRAINSTORMING
        else:
            # Update progress only if status changed (avoids "Message is not modified" error)
            if status != last_status:
                last_status = status
                await thinking_msg.edit_text(
                    f"🧠 *Brainstorming*\n\nProjekt: `{project.name}`\n_{status}_",
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
        [InlineKeyboardButton("Inna ilość...", callback_data="iter:custom")],
        [InlineKeyboardButton("❌ Anuluj", callback_data="iter:cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    user_data = get_user_data(update.effective_chat.id)
    mode = user_data.get("mode", "build")
    project = user_data.get("project")

    project_name = project.name if project else "unknown"
    text = f"🔢 *Wybierz liczbę iteracji:*\n\nProjekt: `{project_name}`\nTryb: {mode}"

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )
    else:
        assert update.message is not None
        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

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
            "🔢 *Wpisz liczbę iteracji:*\n\n"
            "Wyślij /cancel aby anulować.",
            parse_mode="Markdown",
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

    mode_icon = "📋" if mode == "plan" else "🔨"
    is_queued = "Dodano do kolejki" in message

    if success:
        if is_queued:
            text = f"📋 *{message}*\n\n"
            text += f"Projekt: `{project.name}`\n"
            text += f"Tryb: {mode}\n"
            text += f"Iteracje: {iterations}\n"
            if idea:
                text += f"Idea: {idea[:100]}{'...' if len(idea) > 100 else ''}"
        else:
            text = f"{mode_icon} *Task uruchomiony*\n\n"
            text += f"Projekt: `{project.name}`\n"
            text += f"Tryb: {mode}\n"
            text += f"Iteracje: {iterations}\n"
            if idea:
                text += f"Idea: {idea[:100]}{'...' if len(idea) > 100 else ''}\n"
            text += f"\nSesja: `loop-{project.name}`"
    else:
        text = f"❌ *Błąd*\n\n{message}"

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown")
    else:
        assert update.message is not None
        await update.message.reply_text(text, parse_mode="Markdown")

    return ConversationHandler.END


async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show status of all active tasks."""
    tasks = task_manager.list_active()

    if not tasks:
        text = "📊 *Status*\n\nBrak aktywnych zadań."
    else:
        text = "📊 *Aktywne zadania:*\n\n"
        for task in tasks:
            mode_icon = "📋" if task.mode == "plan" else "🔨"
            duration = task_manager.get_task_duration(task)
            text += f"{mode_icon} *{task.project}*\n"
            current = task_manager.get_current_iteration(task) or "?"
            text += f"   {task.mode.title()} • Iteracja: {current}/{task.iterations} • {duration}\n\n"

    buttons = [[InlineKeyboardButton("⬅️ Powrót", callback_data="action:back")]]
    reply_markup = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )
    else:
        assert update.message is not None
        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    return State.PROJECT_MENU


@authorized
async def start_brainstorming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /brainstorming <prompt> command to start a brainstorming session."""
    assert update.message is not None
    assert update.effective_chat is not None

    user_data = get_user_data(update.effective_chat.id)
    project = user_data.get("project")

    if not project:
        await update.message.reply_text(
            "❌ Najpierw wybierz projekt za pomocą /projects"
        )
        return ConversationHandler.END

    # Extract prompt from command
    text = update.message.text or ""
    prompt = text.replace("/brainstorming", "").strip()

    if not prompt:
        await update.message.reply_text(
            "❌ Podaj temat brainstorming:\n`/brainstorming <opis pomysłu>`",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    # Send "thinking" message that we'll update with progress
    thinking_msg = await update.message.reply_text(
        f"🧠 *Brainstorming*\n\nProjekt: `{project.name}`\n_Uruchamiam Claude..._",
        parse_mode="Markdown",
    )

    last_status = "Uruchamiam Claude..."  # Track last status to avoid redundant edits

    # Start brainstorming session with async generator
    async for status, is_final in brainstorm_manager.start(
        chat_id=update.effective_chat.id,
        project=project.name,
        project_path=project.path,
        prompt=prompt,
    ):
        if is_final:
            if status.startswith("Sesja brainstorming już") or "Nie udało" in status or "Timeout" in status or "error" in status.lower():
                await thinking_msg.edit_text(f"❌ {status}", parse_mode="Markdown")
                return ConversationHandler.END

            # Success - delete thinking message and send response
            await thinking_msg.delete()
            await update.message.reply_text(
                f"🤖 *Claude:*\n\n{status}\n\n"
                "_Odpowiedz, aby kontynuować. Użyj /done lub /save aby zapisać do IDEA.md, "
                "lub /cancel aby anulować._",
                parse_mode="Markdown",
            )
            return State.BRAINSTORMING
        else:
            # Update progress only if status changed (avoids "Message is not modified" error)
            if status != last_status:
                last_status = status
                await thinking_msg.edit_text(
                    f"🧠 *Brainstorming*\n\nProjekt: `{project.name}`\n_{status}_",
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

    # Send "thinking" message that we'll update with progress
    thinking_msg = await update.message.reply_text("🤔 _Claude myśli..._", parse_mode="Markdown")

    last_status = "Claude myśli..."  # Track last status to avoid redundant edits

    # Send message to Claude with async generator
    async for status, is_final in brainstorm_manager.respond(
        chat_id=update.effective_chat.id,
        message=message,
    ):
        if is_final:
            if "Brak aktywnej" in status or "nie jest gotowa" in status or "Nie udało" in status or "Timeout" in status or "error" in status.lower():
                await thinking_msg.edit_text(f"❌ {status}", parse_mode="Markdown")
                return State.BRAINSTORMING

            # Success - delete thinking message and send response
            await thinking_msg.delete()
            await update.message.reply_text(
                f"🤖 *Claude:*\n\n{status}",
                parse_mode="Markdown",
            )
            return State.BRAINSTORMING
        else:
            # Update progress only if status changed (avoids "Message is not modified" error)
            if status != last_status:
                last_status = status
                await thinking_msg.edit_text(f"🤔 _{status}_", parse_mode="Markdown")

    return State.BRAINSTORMING


@authorized
async def finish_brainstorming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /done and /save commands to finish brainstorming and save to IDEA.md."""
    assert update.message is not None
    assert update.effective_chat is not None

    thinking_msg = await update.message.reply_text("📝 _Zapisuję IDEA..._", parse_mode="Markdown")

    success, message, idea_content = await brainstorm_manager.finish(
        chat_id=update.effective_chat.id
    )

    if not success:
        await thinking_msg.edit_text(f"❌ {message}", parse_mode="Markdown")
        return State.BRAINSTORMING

    # Show buttons for next action
    buttons = [
        [
            InlineKeyboardButton("🧐 Uruchom Plan", callback_data="brainstorm:plan"),
            InlineKeyboardButton("🔚 Zakończ", callback_data="brainstorm:end"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await thinking_msg.edit_text(
        f"✅ *{message}*\n\nCo chcesz zrobić dalej?",
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
            await query.edit_message_text("❌ Brak wybranego projektu")
            return ConversationHandler.END

        # Start plan mode with saved IDEA
        user_data["mode"] = "plan"
        user_data["idea"] = None  # IDEA already saved to file, loop.sh will read it

        await query.edit_message_text(
            f"▶️ *Uruchamiam Plan dla {project.name}...*",
            parse_mode="Markdown",
        )

        return await show_iterations_menu(update, context)

    # action == "end"
    await query.edit_message_text("✅ Sesja brainstorming zakończona.")
    return ConversationHandler.END


@authorized
async def cancel_brainstorming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel brainstorming session without saving."""
    assert update.message is not None
    assert update.effective_chat is not None

    cancelled = brainstorm_manager.cancel(update.effective_chat.id)

    if cancelled:
        await update.message.reply_text("❌ Brainstorming anulowany.")
    else:
        await update.message.reply_text("Brak aktywnej sesji brainstorming.")

    return ConversationHandler.END


@authorized
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel current operation."""
    assert update.message is not None
    await update.message.reply_text("Anulowano.")
    return ConversationHandler.END


@authorized
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot usage instructions and available commands."""
    assert update.message is not None

    text = (
        "Jak dziala bot?\n"
        "\n"
        "1. Wybierz projekt z listy (/start)\n"
        "2. Wybierz akcje: Plan, Build lub przejrzyj kolejke\n"
        "3. Podaj opis zadania (opcjonalny w trybie Plan)\n"
        "4. Wybierz liczbe iteracji\n"
        "5. Bot uruchomi Claude w tle — sledz postep przez /status\n"
        "\n"
        "Mozesz tez rozpoczac sesje brainstormingu komenda /brainstorming.\n"
        "\n"
        "Komendy:\n"
        "\n"
        "/start — Pokaz liste projektow i wybierz projekt\n"
        "/status — Pokaz aktywne taski i ich postep\n"
        "/brainstorming <temat> — Rozpocznij sesje burzy mozgow z Claude\n"
        "/cancel — Anuluj biezaca operacje\n"
        "/skip — Pomin opis zadania (tryb Plan)\n"
        "/done — Zakoncz brainstorming i zapisz wynik\n"
        "/save — Alias dla /done"
    )

    await update.message.reply_text(text)
    return None


async def check_task_completion(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job that checks for completed tasks and starts queued ones."""
    logger.debug("check_task_completion running")
    results = task_manager.process_completed_tasks()
    logger.debug(f"Processed {len(results)} task completions")

    for _, next_task in results:
        text = ""

        if next_task:
            next_icon = "📋" if next_task.mode == "plan" else "🔨"
            if text:
                text += f"\n\n"
            text += f"▶️ *Uruchomiono z kolejki:*\n"
            text += f"{next_icon} {next_task.project} - {next_task.mode.title()} • {next_task.iterations} iteracji"

        if text:
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=text,
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
            ],
            State.PROJECT_MENU: [
                CallbackQueryHandler(handle_action, pattern=r"^action:"),
                CallbackQueryHandler(handle_cancel_queue, pattern=r"^cancel_queue:"),
                CallbackQueryHandler(project_selected, pattern=r"^project:"),
            ],
            State.ENTER_NAME: [
                CommandHandler("cancel", cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name),
            ],
            State.ENTER_IDEA: [
                CommandHandler("cancel", cancel),
                CommandHandler("skip", skip_idea),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_idea),
            ],
            State.ENTER_BRAINSTORM_PROMPT: [
                CommandHandler("cancel", cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_brainstorm_prompt),
            ],
            State.SELECT_ITERATIONS: [
                CallbackQueryHandler(handle_iterations, pattern=r"^iter:"),
                CommandHandler("cancel", cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_iterations),
            ],
            State.BRAINSTORMING: [
                CommandHandler("done", finish_brainstorming),
                CommandHandler("save", finish_brainstorming),
                CommandHandler("cancel", cancel_brainstorming),
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

    # Job to check for completed tasks every 30 seconds
    if app.job_queue:
        app.job_queue.run_repeating(check_task_completion, interval=30, first=10)
        logger.info("JobQueue registered: check_task_completion every 30s")
    else:
        logger.warning(
            "JobQueue is None! Queue processing disabled. "
            "Install APScheduler: pip install 'python-telegram-bot[job-queue]'"
        )

    return app
