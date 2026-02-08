"""Shared state, helpers, and generic handlers used across all handler modules."""

import logging
from enum import IntEnum, auto

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from ..config import TELEGRAM_CHAT_ID
from ..messages import (
    BRAINSTORM_ERROR_CODES,
    MSG_BRAINSTORM_DONE_BTN,
    MSG_BRAINSTORM_SAVE_BTN,
    MSG_CANCEL_BTN,
    MSG_CANCELLED,
    MSG_HELP,
    MSG_PROJECT_BTN,
    MSG_PROJECTS_LIST_BTN,
    MSG_UNAUTHORIZED,
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


# --- Generic handlers (shared fallbacks used across all states) ---


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
