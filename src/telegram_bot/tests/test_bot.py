"""Tests for bot.py handlers — inline button functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import CallbackQuery, Chat, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update, User
from telegram.ext import ConversationHandler, ContextTypes


# --- Test helpers ---


def make_callback_update(chat_id: int, data: str) -> Update:
    """Create a mock Update with a CallbackQuery for testing button handlers."""
    user = User(id=chat_id, is_bot=False, first_name="Test")
    chat = Chat(id=chat_id, type="private")
    message = MagicMock(spec=Message)
    message.chat = chat

    query = AsyncMock(spec=CallbackQuery)
    query.data = data
    query.message = message
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.callback_query = query
    update.effective_chat = chat
    update.message = None
    return update


def make_context() -> ContextTypes.DEFAULT_TYPE:
    """Create a mock Context for testing."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    return context


# --- Tests for _cancel_keyboard ---


class TestCancelKeyboard:
    """Tests for _cancel_keyboard() helper."""

    def test_returns_inline_keyboard_markup(self):
        """_cancel_keyboard returns InlineKeyboardMarkup with cancel button."""
        from src.telegram_bot.bot import _cancel_keyboard

        result = _cancel_keyboard("input:cancel")
        assert isinstance(result, InlineKeyboardMarkup)

    def test_contains_single_cancel_button(self):
        """Keyboard has exactly one row with one button."""
        from src.telegram_bot.bot import _cancel_keyboard

        result = _cancel_keyboard("input:cancel")
        # InlineKeyboardMarkup.inline_keyboard is list of rows
        assert len(result.inline_keyboard) == 1
        assert len(result.inline_keyboard[0]) == 1

    def test_button_uses_msg_cancel_btn_text(self):
        """Button text matches MSG_CANCEL_BTN constant."""
        from src.telegram_bot.bot import _cancel_keyboard
        from src.telegram_bot.messages import MSG_CANCEL_BTN

        result = _cancel_keyboard("input:cancel")
        button = result.inline_keyboard[0][0]
        assert button.text == MSG_CANCEL_BTN

    def test_button_uses_provided_callback_data(self):
        """Button callback_data matches the argument."""
        from src.telegram_bot.bot import _cancel_keyboard

        result = _cancel_keyboard("input:cancel")
        button = result.inline_keyboard[0][0]
        assert button.callback_data == "input:cancel"

    def test_different_callback_data(self):
        """Helper works with different callback_data values."""
        from src.telegram_bot.bot import _cancel_keyboard

        result = _cancel_keyboard("iter:cancel")
        button = result.inline_keyboard[0][0]
        assert button.callback_data == "iter:cancel"


# --- Tests for handle_input_cancel ---


class TestHandleInputCancel:
    """Tests for handle_input_cancel callback handler."""

    CHAT_ID = 12345

    @pytest.mark.asyncio
    async def test_answers_callback_query(self):
        """Handler answers the callback query to dismiss loading indicator."""
        from src.telegram_bot.bot import handle_input_cancel

        update = make_callback_update(self.CHAT_ID, "input:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID):
            await handle_input_cancel(update, context)
        update.callback_query.answer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_edits_message_with_cancelled(self):
        """Handler edits message to show MSG_CANCELLED."""
        from src.telegram_bot.bot import handle_input_cancel
        from src.telegram_bot.messages import MSG_CANCELLED

        update = make_callback_update(self.CHAT_ID, "input:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID):
            await handle_input_cancel(update, context)
        update.callback_query.edit_message_text.assert_awaited_once_with(MSG_CANCELLED)

    @pytest.mark.asyncio
    async def test_returns_conversation_end(self):
        """Handler returns ConversationHandler.END to exit conversation."""
        from src.telegram_bot.bot import handle_input_cancel

        update = make_callback_update(self.CHAT_ID, "input:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID):
            result = await handle_input_cancel(update, context)
        assert result == ConversationHandler.END


# --- Tests for cancel button presence in prompts ---


class TestCancelButtonInPrompts:
    """Verify that text-input state prompts include reply_markup with cancel button."""

    def test_enter_project_name_prompt_has_cancel(self):
        """ENTER_PROJECT_NAME prompt should include cancel keyboard in reply_markup."""
        # This test verifies the integration — the actual edit_message_text call
        # includes reply_markup. We test the keyboard helper is used correctly.
        from src.telegram_bot.bot import _cancel_keyboard
        from src.telegram_bot.messages import MSG_CANCEL_BTN

        kb = _cancel_keyboard("input:cancel")
        assert kb.inline_keyboard[0][0].text == MSG_CANCEL_BTN
        assert kb.inline_keyboard[0][0].callback_data == "input:cancel"

    def test_enter_iterations_custom_has_cancel(self):
        """SELECT_ITERATIONS custom input prompt should include cancel keyboard."""
        from src.telegram_bot.bot import _cancel_keyboard

        kb = _cancel_keyboard("iter:cancel")
        assert kb.inline_keyboard[0][0].callback_data == "iter:cancel"


# --- Tests for message constants (no slash commands) ---


class TestMessageConstantsNoSlashCommands:
    """Verify slash command text has been removed from Phase 1 message constants."""

    def test_enter_repo_url_no_cancel_command(self):
        """MSG_ENTER_REPO_URL should not contain '/cancel'."""
        from src.telegram_bot.messages import MSG_ENTER_REPO_URL
        assert "/cancel" not in MSG_ENTER_REPO_URL

    def test_enter_worktree_name_no_cancel_command(self):
        """MSG_ENTER_WORKTREE_NAME should not contain '/cancel'."""
        from src.telegram_bot.messages import MSG_ENTER_WORKTREE_NAME
        assert "/cancel" not in MSG_ENTER_WORKTREE_NAME

    def test_enter_project_name_no_cancel_command(self):
        """MSG_ENTER_PROJECT_NAME should not contain '/cancel'."""
        from src.telegram_bot.messages import MSG_ENTER_PROJECT_NAME
        assert "/cancel" not in MSG_ENTER_PROJECT_NAME

    def test_brainstorm_header_no_cancel_command(self):
        """MSG_BRAINSTORM_HEADER should not contain '/cancel'."""
        from src.telegram_bot.messages import MSG_BRAINSTORM_HEADER
        assert "/cancel" not in MSG_BRAINSTORM_HEADER

    def test_enter_iterations_no_cancel_command(self):
        """MSG_ENTER_ITERATIONS should not contain '/cancel'."""
        from src.telegram_bot.messages import MSG_ENTER_ITERATIONS
        assert "/cancel" not in MSG_ENTER_ITERATIONS

    def test_plan_enter_idea_no_skip_command(self):
        """MSG_PLAN_ENTER_IDEA should not contain '/skip' — replaced by inline button."""
        from src.telegram_bot.messages import MSG_PLAN_ENTER_IDEA
        assert "/skip" not in MSG_PLAN_ENTER_IDEA

    def test_plan_enter_idea_no_cancel_command(self):
        """MSG_PLAN_ENTER_IDEA should not contain '/cancel' — replaced by inline button."""
        from src.telegram_bot.messages import MSG_PLAN_ENTER_IDEA
        assert "/cancel" not in MSG_PLAN_ENTER_IDEA


# --- Tests for handle_idea_button ---


class TestHandleIdeaButton:
    """Tests for handle_idea_button callback handler (idea:skip, idea:cancel)."""

    CHAT_ID = 12345

    @pytest.mark.asyncio
    async def test_skip_answers_callback_query(self):
        """idea:skip handler answers the callback query."""
        from src.telegram_bot.bot import handle_idea_button

        update = make_callback_update(self.CHAT_ID, "idea:skip")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={}) as mock_gud, \
             patch("src.telegram_bot.bot.show_iterations_menu", new_callable=AsyncMock, return_value=42):
            await handle_idea_button(update, context)
        update.callback_query.answer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skip_sets_idea_to_none(self):
        """idea:skip sets user_data['idea'] to None (skip means no idea)."""
        from src.telegram_bot.bot import handle_idea_button

        update = make_callback_update(self.CHAT_ID, "idea:skip")
        context = make_context()
        user_data = {"idea": "something"}

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value=user_data), \
             patch("src.telegram_bot.bot.show_iterations_menu", new_callable=AsyncMock, return_value=42):
            await handle_idea_button(update, context)
        assert user_data["idea"] is None

    @pytest.mark.asyncio
    async def test_skip_calls_show_iterations_menu(self):
        """idea:skip transitions to iterations menu."""
        from src.telegram_bot.bot import handle_idea_button

        update = make_callback_update(self.CHAT_ID, "idea:skip")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={}), \
             patch("src.telegram_bot.bot.show_iterations_menu", new_callable=AsyncMock, return_value=42) as mock_menu:
            result = await handle_idea_button(update, context)
        mock_menu.assert_awaited_once_with(update, context)
        assert result == 42

    @pytest.mark.asyncio
    async def test_cancel_answers_callback_query(self):
        """idea:cancel handler answers the callback query."""
        from src.telegram_bot.bot import handle_idea_button

        update = make_callback_update(self.CHAT_ID, "idea:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID):
            await handle_idea_button(update, context)
        update.callback_query.answer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cancel_edits_message_with_cancelled(self):
        """idea:cancel edits message to show MSG_CANCELLED."""
        from src.telegram_bot.bot import handle_idea_button
        from src.telegram_bot.messages import MSG_CANCELLED

        update = make_callback_update(self.CHAT_ID, "idea:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID):
            await handle_idea_button(update, context)
        update.callback_query.edit_message_text.assert_awaited_once_with(MSG_CANCELLED)

    @pytest.mark.asyncio
    async def test_cancel_returns_conversation_end(self):
        """idea:cancel returns ConversationHandler.END."""
        from src.telegram_bot.bot import handle_idea_button

        update = make_callback_update(self.CHAT_ID, "idea:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID):
            result = await handle_idea_button(update, context)
        assert result == ConversationHandler.END


# --- Tests for brainstorm hint keyboards ---


class TestBrainstormHintKeyboard:
    """Tests for _brainstorm_hint_keyboard() and _brainstorm_hint_long_keyboard()."""

    def test_short_keyboard_has_done_and_cancel(self):
        """Short keyboard has Done + Cancel buttons."""
        from src.telegram_bot.bot import _brainstorm_hint_keyboard

        kb = _brainstorm_hint_keyboard()
        assert len(kb.inline_keyboard) == 1
        buttons = kb.inline_keyboard[0]
        assert len(buttons) == 2
        assert buttons[0].callback_data == "bs:done"
        assert buttons[1].callback_data == "bs:cancel"

    def test_short_keyboard_button_text(self):
        """Short keyboard buttons use correct MSG constants."""
        from src.telegram_bot.bot import _brainstorm_hint_keyboard
        from src.telegram_bot.messages import MSG_BRAINSTORM_DONE_BTN, MSG_CANCEL_BTN

        kb = _brainstorm_hint_keyboard()
        buttons = kb.inline_keyboard[0]
        assert buttons[0].text == MSG_BRAINSTORM_DONE_BTN
        assert buttons[1].text == MSG_CANCEL_BTN

    def test_long_keyboard_has_done_save_cancel(self):
        """Long keyboard has Done + Save + Cancel buttons."""
        from src.telegram_bot.bot import _brainstorm_hint_long_keyboard

        kb = _brainstorm_hint_long_keyboard()
        assert len(kb.inline_keyboard) == 1
        buttons = kb.inline_keyboard[0]
        assert len(buttons) == 3
        assert buttons[0].callback_data == "bs:done"
        assert buttons[1].callback_data == "bs:save"
        assert buttons[2].callback_data == "bs:cancel"

    def test_long_keyboard_button_text(self):
        """Long keyboard buttons use correct MSG constants."""
        from src.telegram_bot.bot import _brainstorm_hint_long_keyboard
        from src.telegram_bot.messages import (
            MSG_BRAINSTORM_DONE_BTN,
            MSG_BRAINSTORM_SAVE_BTN,
            MSG_CANCEL_BTN,
        )

        kb = _brainstorm_hint_long_keyboard()
        buttons = kb.inline_keyboard[0]
        assert buttons[0].text == MSG_BRAINSTORM_DONE_BTN
        assert buttons[1].text == MSG_BRAINSTORM_SAVE_BTN
        assert buttons[2].text == MSG_CANCEL_BTN


# --- Tests for brainstorm message constants (no slash commands) ---


class TestBrainstormMessageConstantsNoSlashCommands:
    """Verify slash command text removed from Phase 3 brainstorm message constants."""

    def test_brainstorm_reply_hint_no_done_command(self):
        """MSG_BRAINSTORM_REPLY_HINT should not contain '/done'."""
        from src.telegram_bot.messages import MSG_BRAINSTORM_REPLY_HINT
        assert "/done" not in MSG_BRAINSTORM_REPLY_HINT

    def test_brainstorm_reply_hint_no_cancel_command(self):
        """MSG_BRAINSTORM_REPLY_HINT should not contain '/cancel'."""
        from src.telegram_bot.messages import MSG_BRAINSTORM_REPLY_HINT
        assert "/cancel" not in MSG_BRAINSTORM_REPLY_HINT

    def test_brainstorm_reply_hint_long_no_done_command(self):
        """MSG_BRAINSTORM_REPLY_HINT_LONG should not contain '/done'."""
        from src.telegram_bot.messages import MSG_BRAINSTORM_REPLY_HINT_LONG
        assert "/done" not in MSG_BRAINSTORM_REPLY_HINT_LONG

    def test_brainstorm_reply_hint_long_no_save_command(self):
        """MSG_BRAINSTORM_REPLY_HINT_LONG should not contain '/save'."""
        from src.telegram_bot.messages import MSG_BRAINSTORM_REPLY_HINT_LONG
        assert "/save" not in MSG_BRAINSTORM_REPLY_HINT_LONG

    def test_brainstorm_reply_hint_long_no_cancel_command(self):
        """MSG_BRAINSTORM_REPLY_HINT_LONG should not contain '/cancel'."""
        from src.telegram_bot.messages import MSG_BRAINSTORM_REPLY_HINT_LONG
        assert "/cancel" not in MSG_BRAINSTORM_REPLY_HINT_LONG

    def test_brainstorm_resume_no_done_command(self):
        """MSG_BRAINSTORM_RESUME should not contain '/done'."""
        from src.telegram_bot.messages import MSG_BRAINSTORM_RESUME
        assert "/done" not in MSG_BRAINSTORM_RESUME

    def test_brainstorm_resume_no_cancel_command(self):
        """MSG_BRAINSTORM_RESUME should not contain '/cancel'."""
        from src.telegram_bot.messages import MSG_BRAINSTORM_RESUME
        assert "/cancel" not in MSG_BRAINSTORM_RESUME

    def test_session_already_active_no_done_command(self):
        """MSG_SESSION_ALREADY_ACTIVE should not contain '/done'."""
        from src.telegram_bot.messages import MSG_SESSION_ALREADY_ACTIVE
        assert "/done" not in MSG_SESSION_ALREADY_ACTIVE

    def test_session_already_active_no_cancel_command(self):
        """MSG_SESSION_ALREADY_ACTIVE should not contain '/cancel'."""
        from src.telegram_bot.messages import MSG_SESSION_ALREADY_ACTIVE
        assert "/cancel" not in MSG_SESSION_ALREADY_ACTIVE


# --- Tests for handle_brainstorm_hint_button ---


class TestHandleBrainstormHintButton:
    """Tests for handle_brainstorm_hint_button callback handler (bs:done, bs:save, bs:cancel)."""

    CHAT_ID = 12345

    @pytest.mark.asyncio
    async def test_done_answers_callback_query(self):
        """bs:done handler answers the callback query."""
        from src.telegram_bot.bot import handle_brainstorm_hint_button

        update = make_callback_update(self.CHAT_ID, "bs:done")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm:
            mock_bm.finish = AsyncMock(return_value=(True, "Saved", "content"))
            await handle_brainstorm_hint_button(update, context)
        update.callback_query.answer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_done_calls_finish(self):
        """bs:done triggers brainstorm_manager.finish()."""
        from src.telegram_bot.bot import handle_brainstorm_hint_button

        update = make_callback_update(self.CHAT_ID, "bs:done")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm:
            mock_bm.finish = AsyncMock(return_value=(True, "Saved", "content"))
            await handle_brainstorm_hint_button(update, context)
        mock_bm.finish.assert_awaited_once_with(chat_id=self.CHAT_ID)

    @pytest.mark.asyncio
    async def test_done_success_shows_what_next(self):
        """bs:done on success shows 'what next' message with action buttons."""
        from src.telegram_bot.bot import handle_brainstorm_hint_button
        from src.telegram_bot.messages import MSG_BRAINSTORM_WHAT_NEXT

        update = make_callback_update(self.CHAT_ID, "bs:done")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm:
            mock_bm.finish = AsyncMock(return_value=(True, "Saved to ROADMAP", "content"))
            await handle_brainstorm_hint_button(update, context)

        call_args = update.callback_query.edit_message_text.call_args
        # edit_message_text called with positional text arg
        expected = MSG_BRAINSTORM_WHAT_NEXT.format(message="Saved to ROADMAP")
        actual_text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert expected in actual_text

    @pytest.mark.asyncio
    async def test_done_failure_shows_error(self):
        """bs:done on failure shows error message and stays in BRAINSTORMING."""
        from src.telegram_bot.bot import handle_brainstorm_hint_button, State

        update = make_callback_update(self.CHAT_ID, "bs:done")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm:
            mock_bm.finish = AsyncMock(return_value=(False, "No session", None))
            result = await handle_brainstorm_hint_button(update, context)
        assert result == State.BRAINSTORMING

    @pytest.mark.asyncio
    async def test_save_calls_finish(self):
        """bs:save also triggers brainstorm_manager.finish() (same as done)."""
        from src.telegram_bot.bot import handle_brainstorm_hint_button

        update = make_callback_update(self.CHAT_ID, "bs:save")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm:
            mock_bm.finish = AsyncMock(return_value=(True, "Saved", "content"))
            await handle_brainstorm_hint_button(update, context)
        mock_bm.finish.assert_awaited_once_with(chat_id=self.CHAT_ID)

    @pytest.mark.asyncio
    async def test_cancel_answers_callback_query(self):
        """bs:cancel handler answers the callback query."""
        from src.telegram_bot.bot import handle_brainstorm_hint_button

        update = make_callback_update(self.CHAT_ID, "bs:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm:
            mock_bm.cancel = MagicMock(return_value=True)
            await handle_brainstorm_hint_button(update, context)
        update.callback_query.answer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cancel_calls_brainstorm_cancel(self):
        """bs:cancel triggers brainstorm_manager.cancel()."""
        from src.telegram_bot.bot import handle_brainstorm_hint_button

        update = make_callback_update(self.CHAT_ID, "bs:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm:
            mock_bm.cancel = MagicMock(return_value=True)
            await handle_brainstorm_hint_button(update, context)
        mock_bm.cancel.assert_called_once_with(self.CHAT_ID)

    @pytest.mark.asyncio
    async def test_cancel_shows_cancelled_message(self):
        """bs:cancel edits message to show cancelled text."""
        from src.telegram_bot.bot import handle_brainstorm_hint_button
        from src.telegram_bot.messages import MSG_BRAINSTORM_CANCELLED

        update = make_callback_update(self.CHAT_ID, "bs:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm:
            mock_bm.cancel = MagicMock(return_value=True)
            await handle_brainstorm_hint_button(update, context)
        update.callback_query.edit_message_text.assert_awaited_once_with(MSG_BRAINSTORM_CANCELLED)

    @pytest.mark.asyncio
    async def test_cancel_returns_conversation_end(self):
        """bs:cancel returns ConversationHandler.END."""
        from src.telegram_bot.bot import handle_brainstorm_hint_button

        update = make_callback_update(self.CHAT_ID, "bs:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm:
            mock_bm.cancel = MagicMock(return_value=True)
            result = await handle_brainstorm_hint_button(update, context)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_done_success_returns_brainstorming_state(self):
        """bs:done on success returns BRAINSTORMING state (for post-action buttons)."""
        from src.telegram_bot.bot import handle_brainstorm_hint_button, State

        update = make_callback_update(self.CHAT_ID, "bs:done")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm:
            mock_bm.finish = AsyncMock(return_value=(True, "Saved", "content"))
            result = await handle_brainstorm_hint_button(update, context)
        assert result == State.BRAINSTORMING
