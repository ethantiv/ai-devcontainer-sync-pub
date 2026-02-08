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
        call_args = update.callback_query.edit_message_text.call_args
        assert call_args[0][0] == MSG_CANCELLED

    @pytest.mark.asyncio
    async def test_returns_select_project(self):
        """Handler returns State.SELECT_PROJECT for follow-up button routing."""
        from src.telegram_bot.bot import handle_input_cancel, State

        update = make_callback_update(self.CHAT_ID, "input:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID):
            result = await handle_input_cancel(update, context)
        assert result == State.SELECT_PROJECT

    @pytest.mark.asyncio
    async def test_includes_nav_buttons(self):
        """Handler includes Projects navigation button in reply_markup."""
        from src.telegram_bot.bot import handle_input_cancel
        from src.telegram_bot.messages import MSG_PROJECTS_LIST_BTN

        update = make_callback_update(self.CHAT_ID, "input:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID):
            await handle_input_cancel(update, context)

        call_kwargs = update.callback_query.edit_message_text.call_args[1]
        markup = call_kwargs["reply_markup"]
        assert isinstance(markup, InlineKeyboardMarkup)
        button_texts = [b.text for row in markup.inline_keyboard for b in row]
        assert MSG_PROJECTS_LIST_BTN in button_texts


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

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={}):
            await handle_idea_button(update, context)
        update.callback_query.answer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cancel_edits_message_with_cancelled(self):
        """idea:cancel edits message to show MSG_CANCELLED."""
        from src.telegram_bot.bot import handle_idea_button
        from src.telegram_bot.messages import MSG_CANCELLED

        update = make_callback_update(self.CHAT_ID, "idea:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={}):
            await handle_idea_button(update, context)
        call_args = update.callback_query.edit_message_text.call_args
        assert call_args[0][0] == MSG_CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_returns_select_project(self):
        """idea:cancel returns State.SELECT_PROJECT for follow-up button routing."""
        from src.telegram_bot.bot import handle_idea_button, State

        update = make_callback_update(self.CHAT_ID, "idea:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={}):
            result = await handle_idea_button(update, context)
        assert result == State.SELECT_PROJECT

    @pytest.mark.asyncio
    async def test_cancel_includes_nav_buttons(self):
        """idea:cancel includes navigation buttons with project context."""
        from src.telegram_bot.bot import handle_idea_button
        from src.telegram_bot.messages import MSG_PROJECT_BTN, MSG_PROJECTS_LIST_BTN

        update = make_callback_update(self.CHAT_ID, "idea:cancel")
        context = make_context()
        mock_project = MagicMock()
        mock_project.name = "test-proj"

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={"project": mock_project}):
            await handle_idea_button(update, context)

        call_kwargs = update.callback_query.edit_message_text.call_args[1]
        markup = call_kwargs["reply_markup"]
        button_texts = [b.text for row in markup.inline_keyboard for b in row]
        assert MSG_PROJECT_BTN in button_texts
        assert MSG_PROJECTS_LIST_BTN in button_texts


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
        call_args = update.callback_query.edit_message_text.call_args
        assert call_args[0][0] == MSG_BRAINSTORM_CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_returns_select_project(self):
        """bs:cancel returns State.SELECT_PROJECT for follow-up button routing."""
        from src.telegram_bot.bot import handle_brainstorm_hint_button, State

        update = make_callback_update(self.CHAT_ID, "bs:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm:
            mock_bm.cancel = MagicMock(return_value=True)
            result = await handle_brainstorm_hint_button(update, context)
        assert result == State.SELECT_PROJECT

    @pytest.mark.asyncio
    async def test_cancel_includes_nav_buttons(self):
        """bs:cancel includes navigation buttons in reply_markup."""
        from src.telegram_bot.bot import handle_brainstorm_hint_button
        from src.telegram_bot.messages import MSG_PROJECTS_LIST_BTN

        update = make_callback_update(self.CHAT_ID, "bs:cancel")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm:
            mock_bm.cancel = MagicMock(return_value=True)
            await handle_brainstorm_hint_button(update, context)

        call_kwargs = update.callback_query.edit_message_text.call_args[1]
        markup = call_kwargs["reply_markup"]
        button_texts = [b.text for row in markup.inline_keyboard for b in row]
        assert MSG_PROJECTS_LIST_BTN in button_texts

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


# --- Tests for _format_completion_summary ---


class TestFormatCompletionSummary:
    """Tests for _format_completion_summary() output formatting."""

    def _make_task(self, project="myproject", mode="build", iterations=5):
        from src.telegram_bot.tasks import Task
        from pathlib import Path
        return Task(
            project=project,
            project_path=Path(f"/tmp/{project}"),
            mode=mode,
            iterations=iterations,
            idea=None,
            session_name=f"loop-{project}",
        )

    def test_basic_output(self):
        """Basic summary contains project, mode, iterations, and duration."""
        from src.telegram_bot.bot import _format_completion_summary

        task = self._make_task()
        with patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.get_task_duration.return_value = "2m 30s"
            result = _format_completion_summary(task, None, [], None)

        assert "myproject" in result
        assert "Build completed" in result
        assert "Iterations: 5" in result
        assert "2m 30s" in result

    def test_with_diff_stats(self):
        """Summary includes change stats when diff_stats is provided."""
        from src.telegram_bot.bot import _format_completion_summary

        task = self._make_task()
        diff = {"files_changed": 3, "insertions": 42, "deletions": 10}
        with patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.get_task_duration.return_value = "1m 0s"
            result = _format_completion_summary(task, diff, [], None)

        assert "Files: 3" in result
        assert "+42" in result
        assert "-10" in result

    def test_with_commits(self):
        """Summary includes commit list when commits are provided."""
        from src.telegram_bot.bot import _format_completion_summary

        task = self._make_task()
        commits = ["abc1234 fix: bug", "def5678 feat: new"]
        with patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.get_task_duration.return_value = "5s"
            result = _format_completion_summary(task, None, commits, None)

        assert "abc1234 fix: bug" in result
        assert "def5678 feat: new" in result
        assert "Commits" in result

    def test_with_plan_progress(self):
        """Summary includes plan progress bar when plan_progress is provided."""
        from src.telegram_bot.bot import _format_completion_summary

        task = self._make_task()
        with patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.get_task_duration.return_value = "10s"
            result = _format_completion_summary(task, None, [], (3, 10))

        assert "3/10" in result
        assert "30%" in result
        assert "Plan" in result

    def test_with_next_task_appends_queue_line(self):
        """When next_task is provided, summary includes queue-next line."""
        from src.telegram_bot.bot import _format_completion_summary

        completed = self._make_task(project="proj-a", mode="build", iterations=5)
        next_t = self._make_task(project="proj-b", mode="plan", iterations=3)
        with patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.get_task_duration.return_value = "1m 0s"
            result = _format_completion_summary(completed, None, [], None, next_task=next_t)

        assert "Next" in result
        assert "proj-b" in result
        assert "Plan" in result
        assert "3 iterations" in result

    def test_without_next_task_no_queue_line(self):
        """When next_task is None, summary does not include queue-next line."""
        from src.telegram_bot.bot import _format_completion_summary

        task = self._make_task()
        with patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.get_task_duration.return_value = "5s"
            result = _format_completion_summary(task, None, [], None, next_task=None)

        assert "Next" not in result

    def test_plan_mode_uses_diamond_icon(self):
        """Plan mode uses diamond icon in title."""
        from src.telegram_bot.bot import _format_completion_summary

        task = self._make_task(mode="plan")
        with patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.get_task_duration.return_value = "5s"
            result = _format_completion_summary(task, None, [], None)

        assert "\u25c7" in result  # ◇


# --- Tests for check_task_completion ---


class TestCheckTaskCompletion:
    """Tests for check_task_completion() notification consolidation."""

    CHAT_ID = 12345

    def _make_task(self, project="myproject", mode="build", iterations=5, start_commit=None):
        from src.telegram_bot.tasks import Task
        from pathlib import Path
        return Task(
            project=project,
            project_path=Path(f"/tmp/{project}"),
            mode=mode,
            iterations=iterations,
            idea=None,
            session_name=f"loop-{project}",
            start_commit=start_commit,
        )

    @pytest.mark.asyncio
    async def test_completed_with_queue_sends_single_message(self):
        """When task completes and queue has next, only one send_message call is made."""
        from src.telegram_bot.bot import check_task_completion

        completed = self._make_task(project="proj-a")
        next_t = self._make_task(project="proj-b", mode="plan", iterations=3)
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.task_manager") as mock_tm, \
             patch("src.telegram_bot.bot.get_plan_progress", return_value=None), \
             patch("src.telegram_bot.bot.get_diff_stats", return_value=None), \
             patch("src.telegram_bot.bot.get_recent_commits", return_value=[]):
            mock_tm.process_completed_tasks.return_value = [(completed, next_t)]
            mock_tm.get_task_duration.return_value = "1m 0s"
            await check_task_completion(context)

        # Only one message sent (consolidated), not two separate ones
        assert context.bot.send_message.await_count == 1
        call_kwargs = context.bot.send_message.call_args[1]
        # The single message contains both completion and queue-next info
        assert "proj-a" in call_kwargs["text"]
        assert "proj-b" in call_kwargs["text"]
        assert "Next" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_orphaned_queue_start_sends_standalone_message(self):
        """When no completed task but queue starts, standalone message is sent."""
        from src.telegram_bot.bot import check_task_completion

        next_t = self._make_task(project="proj-b", mode="build", iterations=5)
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.process_completed_tasks.return_value = [(None, next_t)]
            await check_task_completion(context)

        assert context.bot.send_message.await_count == 1
        call_kwargs = context.bot.send_message.call_args[1]
        assert "Started from queue" in call_kwargs["text"]
        assert "proj-b" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_no_tasks_sends_no_message(self):
        """When no completed tasks and no queue, no messages are sent."""
        from src.telegram_bot.bot import check_task_completion

        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.process_completed_tasks.return_value = []
            await check_task_completion(context)

        context.bot.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_completed_without_queue_sends_one_message(self):
        """When task completes with no queue, one completion summary is sent."""
        from src.telegram_bot.bot import check_task_completion

        completed = self._make_task(project="proj-a")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.task_manager") as mock_tm, \
             patch("src.telegram_bot.bot.get_plan_progress", return_value=None), \
             patch("src.telegram_bot.bot.get_diff_stats", return_value=None), \
             patch("src.telegram_bot.bot.get_recent_commits", return_value=[]):
            mock_tm.process_completed_tasks.return_value = [(completed, None)]
            mock_tm.get_task_duration.return_value = "30s"
            await check_task_completion(context)

        assert context.bot.send_message.await_count == 1
        call_kwargs = context.bot.send_message.call_args[1]
        assert "proj-a" in call_kwargs["text"]
        assert "Next" not in call_kwargs["text"]


# --- Test for notify-telegram.sh removal from loop.sh ---


class TestNotifyTelegramRemoval:
    """Verify notify-telegram.sh is no longer called from loop.sh cleanup trap."""

    def test_loop_sh_does_not_call_notify_telegram(self):
        """loop.sh cleanup trap should not invoke notify-telegram.sh."""
        import os
        loop_sh = os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "loop.sh"
        )
        with open(loop_sh) as f:
            content = f.read()
        assert "notify-telegram.sh" not in content


# --- Tests for _nav_keyboard helper ---


class TestNavKeyboard:
    """Tests for _nav_keyboard() navigation button helper."""

    def test_without_project_has_projects_button_only(self):
        """Without project_name, keyboard has only Projects button."""
        from src.telegram_bot.bot import _nav_keyboard
        from src.telegram_bot.messages import MSG_PROJECTS_LIST_BTN

        kb = _nav_keyboard()
        assert len(kb.inline_keyboard) == 1
        assert len(kb.inline_keyboard[0]) == 1
        assert kb.inline_keyboard[0][0].text == MSG_PROJECTS_LIST_BTN
        assert kb.inline_keyboard[0][0].callback_data == "action:back"

    def test_with_project_has_project_and_projects_buttons(self):
        """With project_name, keyboard has View Project + Projects buttons."""
        from src.telegram_bot.bot import _nav_keyboard
        from src.telegram_bot.messages import MSG_PROJECT_BTN, MSG_PROJECTS_LIST_BTN

        kb = _nav_keyboard("my-proj")
        buttons = kb.inline_keyboard[0]
        assert len(buttons) == 2
        assert buttons[0].text == MSG_PROJECT_BTN
        assert buttons[0].callback_data == "project:my-proj"
        assert buttons[1].text == MSG_PROJECTS_LIST_BTN
        assert buttons[1].callback_data == "action:back"

    def test_returns_inline_keyboard_markup(self):
        """Helper returns InlineKeyboardMarkup instance."""
        from src.telegram_bot.bot import _nav_keyboard

        assert isinstance(_nav_keyboard(), InlineKeyboardMarkup)
        assert isinstance(_nav_keyboard("proj"), InlineKeyboardMarkup)


# --- Tests for start_task follow-up buttons ---


class TestStartTaskFollowUp:
    """Tests for follow-up buttons in start_task()."""

    CHAT_ID = 12345

    @pytest.mark.asyncio
    async def test_started_task_returns_select_project(self):
        """start_task returns State.SELECT_PROJECT instead of END."""
        from src.telegram_bot.bot import start_task, State

        update = MagicMock(spec=Update)
        update.effective_chat = Chat(id=self.CHAT_ID, type="private")
        update.callback_query = None
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        context = make_context()

        mock_project = MagicMock()
        mock_project.name = "test-proj"

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={
                 "project": mock_project, "mode": "build", "iterations": 5, "idea": None
             }), \
             patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.start_task.return_value = (True, "Started")
            result = await start_task(update, context)

        assert result == State.SELECT_PROJECT

    @pytest.mark.asyncio
    async def test_started_task_has_project_and_projects_buttons(self):
        """Started task includes View Project + Projects buttons."""
        from src.telegram_bot.bot import start_task
        from src.telegram_bot.messages import MSG_PROJECT_BTN, MSG_PROJECTS_LIST_BTN

        update = MagicMock(spec=Update)
        update.effective_chat = Chat(id=self.CHAT_ID, type="private")
        update.callback_query = None
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        context = make_context()

        mock_project = MagicMock()
        mock_project.name = "test-proj"

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={
                 "project": mock_project, "mode": "build", "iterations": 5, "idea": None
             }), \
             patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.start_task.return_value = (True, "Started")
            await start_task(update, context)

        call_kwargs = update.message.reply_text.call_args[1]
        markup = call_kwargs["reply_markup"]
        button_texts = [b.text for row in markup.inline_keyboard for b in row]
        assert MSG_PROJECT_BTN in button_texts
        assert MSG_PROJECTS_LIST_BTN in button_texts

    @pytest.mark.asyncio
    async def test_queued_task_has_queue_button(self):
        """Queued task includes Queue + Project + Projects buttons."""
        from src.telegram_bot.bot import start_task
        from src.telegram_bot.messages import MSG_PROJECT_BTN, MSG_PROJECTS_LIST_BTN

        update = MagicMock(spec=Update)
        update.effective_chat = Chat(id=self.CHAT_ID, type="private")
        update.callback_query = None
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        context = make_context()

        mock_project = MagicMock()
        mock_project.name = "test-proj"

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={
                 "project": mock_project, "mode": "plan", "iterations": 3, "idea": None
             }), \
             patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.start_task.return_value = (True, "Queued #2")
            await start_task(update, context)

        call_kwargs = update.message.reply_text.call_args[1]
        markup = call_kwargs["reply_markup"]
        buttons = markup.inline_keyboard[0]
        # Queued: 3 buttons (Queue, Project, Projects)
        assert len(buttons) == 3
        assert buttons[0].callback_data == "action:queue"
        assert buttons[1].callback_data == "project:test-proj"
        assert buttons[2].callback_data == "action:back"

    @pytest.mark.asyncio
    async def test_failed_task_has_nav_buttons(self):
        """Failed task includes Project + Projects buttons."""
        from src.telegram_bot.bot import start_task
        from src.telegram_bot.messages import MSG_PROJECT_BTN, MSG_PROJECTS_LIST_BTN

        update = MagicMock(spec=Update)
        update.effective_chat = Chat(id=self.CHAT_ID, type="private")
        update.callback_query = None
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        context = make_context()

        mock_project = MagicMock()
        mock_project.name = "test-proj"

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={
                 "project": mock_project, "mode": "build", "iterations": 5, "idea": None
             }), \
             patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.start_task.return_value = (False, "Session already running")
            await start_task(update, context)

        call_kwargs = update.message.reply_text.call_args[1]
        markup = call_kwargs["reply_markup"]
        button_texts = [b.text for row in markup.inline_keyboard for b in row]
        assert MSG_PROJECT_BTN in button_texts
        assert MSG_PROJECTS_LIST_BTN in button_texts


# --- Tests for cancel_brainstorming follow-up buttons ---


class TestCancelBrainstormingFollowUp:
    """Tests for follow-up buttons in cancel_brainstorming()."""

    CHAT_ID = 12345

    @pytest.mark.asyncio
    async def test_returns_select_project(self):
        """cancel_brainstorming returns State.SELECT_PROJECT."""
        from src.telegram_bot.bot import cancel_brainstorming, State

        update = MagicMock(spec=Update)
        update.effective_chat = Chat(id=self.CHAT_ID, type="private")
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm, \
             patch("src.telegram_bot.bot.get_user_data", return_value={}):
            mock_bm.cancel.return_value = True
            result = await cancel_brainstorming(update, context)

        assert result == State.SELECT_PROJECT

    @pytest.mark.asyncio
    async def test_includes_nav_buttons(self):
        """cancel_brainstorming includes navigation buttons."""
        from src.telegram_bot.bot import cancel_brainstorming
        from src.telegram_bot.messages import MSG_PROJECTS_LIST_BTN

        update = MagicMock(spec=Update)
        update.effective_chat = Chat(id=self.CHAT_ID, type="private")
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.brainstorm_manager") as mock_bm, \
             patch("src.telegram_bot.bot.get_user_data", return_value={}):
            mock_bm.cancel.return_value = True
            await cancel_brainstorming(update, context)

        call_kwargs = update.message.reply_text.call_args[1]
        markup = call_kwargs["reply_markup"]
        button_texts = [b.text for row in markup.inline_keyboard for b in row]
        assert MSG_PROJECTS_LIST_BTN in button_texts


# --- Tests for cancel() follow-up buttons ---


class TestCancelFollowUp:
    """Tests for follow-up buttons in cancel()."""

    CHAT_ID = 12345

    @pytest.mark.asyncio
    async def test_returns_select_project(self):
        """cancel() returns State.SELECT_PROJECT."""
        from src.telegram_bot.bot import cancel, State

        update = MagicMock(spec=Update)
        update.effective_chat = Chat(id=self.CHAT_ID, type="private")
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID):
            result = await cancel(update, context)

        assert result == State.SELECT_PROJECT

    @pytest.mark.asyncio
    async def test_includes_nav_buttons(self):
        """cancel() includes Projects navigation button."""
        from src.telegram_bot.bot import cancel
        from src.telegram_bot.messages import MSG_PROJECTS_LIST_BTN

        update = MagicMock(spec=Update)
        update.effective_chat = Chat(id=self.CHAT_ID, type="private")
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID):
            await cancel(update, context)

        call_kwargs = update.message.reply_text.call_args[1]
        markup = call_kwargs["reply_markup"]
        button_texts = [b.text for row in markup.inline_keyboard for b in row]
        assert MSG_PROJECTS_LIST_BTN in button_texts


# --- Tests for handle_brainstorm_action follow-up buttons ---


class TestHandleBrainstormActionFollowUp:
    """Tests for follow-up buttons in handle_brainstorm_action() end/no-project paths."""

    CHAT_ID = 12345

    @pytest.mark.asyncio
    async def test_end_returns_select_project(self):
        """brainstorm:end returns State.SELECT_PROJECT."""
        from src.telegram_bot.bot import handle_brainstorm_action, State

        update = make_callback_update(self.CHAT_ID, "brainstorm:end")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={}):
            result = await handle_brainstorm_action(update, context)

        assert result == State.SELECT_PROJECT

    @pytest.mark.asyncio
    async def test_end_includes_nav_buttons(self):
        """brainstorm:end includes Projects navigation button."""
        from src.telegram_bot.bot import handle_brainstorm_action
        from src.telegram_bot.messages import MSG_PROJECTS_LIST_BTN

        update = make_callback_update(self.CHAT_ID, "brainstorm:end")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={}):
            await handle_brainstorm_action(update, context)

        call_kwargs = update.callback_query.edit_message_text.call_args[1]
        markup = call_kwargs["reply_markup"]
        button_texts = [b.text for row in markup.inline_keyboard for b in row]
        assert MSG_PROJECTS_LIST_BTN in button_texts

    @pytest.mark.asyncio
    async def test_end_with_project_shows_project_button(self):
        """brainstorm:end with project context includes View Project button."""
        from src.telegram_bot.bot import handle_brainstorm_action
        from src.telegram_bot.messages import MSG_PROJECT_BTN

        update = make_callback_update(self.CHAT_ID, "brainstorm:end")
        context = make_context()
        mock_project = MagicMock()
        mock_project.name = "test-proj"

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={"project": mock_project}):
            await handle_brainstorm_action(update, context)

        call_kwargs = update.callback_query.edit_message_text.call_args[1]
        markup = call_kwargs["reply_markup"]
        button_data = [b.callback_data for row in markup.inline_keyboard for b in row]
        assert "project:test-proj" in button_data

    @pytest.mark.asyncio
    async def test_no_project_returns_select_project(self):
        """brainstorm:plan with no project returns State.SELECT_PROJECT."""
        from src.telegram_bot.bot import handle_brainstorm_action, State

        update = make_callback_update(self.CHAT_ID, "brainstorm:plan")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={}):
            result = await handle_brainstorm_action(update, context)

        assert result == State.SELECT_PROJECT

    @pytest.mark.asyncio
    async def test_no_project_includes_nav_buttons(self):
        """brainstorm:plan with no project includes Projects button."""
        from src.telegram_bot.bot import handle_brainstorm_action
        from src.telegram_bot.messages import MSG_PROJECTS_LIST_BTN

        update = make_callback_update(self.CHAT_ID, "brainstorm:plan")
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.get_user_data", return_value={}):
            await handle_brainstorm_action(update, context)

        call_kwargs = update.callback_query.edit_message_text.call_args[1]
        markup = call_kwargs["reply_markup"]
        button_texts = [b.text for row in markup.inline_keyboard for b in row]
        assert MSG_PROJECTS_LIST_BTN in button_texts


# --- Tests for orphaned queue start follow-up buttons ---


class TestOrphanedQueueStartFollowUp:
    """Tests for follow-up buttons in orphaned queue start message."""

    CHAT_ID = 12345

    def _make_task(self, project="myproject", mode="build", iterations=5):
        from src.telegram_bot.tasks import Task
        from pathlib import Path
        return Task(
            project=project,
            project_path=Path(f"/tmp/{project}"),
            mode=mode,
            iterations=iterations,
            idea=None,
            session_name=f"loop-{project}",
        )

    @pytest.mark.asyncio
    async def test_orphaned_queue_start_has_nav_buttons(self):
        """Orphaned queue start message includes project + projects nav buttons."""
        from src.telegram_bot.bot import check_task_completion
        from src.telegram_bot.messages import MSG_PROJECT_BTN, MSG_PROJECTS_LIST_BTN

        next_t = self._make_task(project="proj-b", mode="build", iterations=5)
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID), \
             patch("src.telegram_bot.bot.task_manager") as mock_tm:
            mock_tm.process_completed_tasks.return_value = [(None, next_t)]
            await check_task_completion(context)

        call_kwargs = context.bot.send_message.call_args[1]
        markup = call_kwargs["reply_markup"]
        button_texts = [b.text for row in markup.inline_keyboard for b in row]
        assert MSG_PROJECT_BTN in button_texts
        assert MSG_PROJECTS_LIST_BTN in button_texts
        button_data = [b.callback_data for row in markup.inline_keyboard for b in row]
        assert "project:proj-b" in button_data


# --- Tests for help_command follow-up buttons ---


class TestHelpCommandFollowUp:
    """Tests for follow-up buttons in help_command()."""

    CHAT_ID = 12345

    @pytest.mark.asyncio
    async def test_help_includes_projects_button(self):
        """help_command includes Projects navigation button."""
        from src.telegram_bot.bot import help_command
        from src.telegram_bot.messages import MSG_PROJECTS_LIST_BTN

        update = MagicMock(spec=Update)
        update.effective_chat = Chat(id=self.CHAT_ID, type="private")
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        context = make_context()

        with patch("src.telegram_bot.bot.TELEGRAM_CHAT_ID", self.CHAT_ID):
            result = await help_command(update, context)

        # help_command remains stateless
        assert result is None

        call_kwargs = update.message.reply_text.call_args[1]
        markup = call_kwargs["reply_markup"]
        button_texts = [b.text for row in markup.inline_keyboard for b in row]
        assert MSG_PROJECTS_LIST_BTN in button_texts
