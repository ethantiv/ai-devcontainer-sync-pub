"""Tests for tasks module — TaskManager queue management, BrainstormManager persistence."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.telegram_bot.messages import (
    ERR_NO_RESULT,
    ERR_NO_SESSION,
    ERR_NOT_READY,
    ERR_SESSION_ACTIVE,
    ERR_START_FAILED,
    ERR_TIMEOUT,
    MSG_BRAINSTORM_CLAUDE_THINKING,
    MSG_BRAINSTORM_STARTING,
    MSG_FAILED_TO_START_CLAUDE,
    MSG_IDEA_SAVED,
    MSG_NO_ACTIVE_BRAINSTORM,
    MSG_SESSION_NOT_READY,
    MSG_SUMMARY_PROMPT,
    MSG_TIMEOUT_WAITING,
)


@pytest.fixture
def task_manager(tmp_path):
    """Create a TaskManager with mocked tmux calls and disk space check."""
    with (
        patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)),
        patch("src.telegram_bot.tasks.check_disk_space", return_value=(True, 5000.0)),
    ):
        from src.telegram_bot.tasks import TaskManager
        tm = TaskManager()
        yield tm


@pytest.fixture
def brainstorm_manager(tmp_path):
    """Create a BrainstormManager with mocked tmux and persistent storage."""
    with (
        patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)),
        # _load_sessions checks for file existence, which is fine with tmp_path
        patch("src.telegram_bot.tasks.BrainstormManager._is_session_running", return_value=False),
    ):
        from src.telegram_bot.tasks import BrainstormManager
        bm = BrainstormManager()
        # TMP_DIR is now auto-created as tmp_path/.brainstorm by __init__
        yield bm


class TestTaskManagerQueue:
    """Tests for TaskManager queue management."""

    def test_start_task_when_no_session_running(self, task_manager):
        """Task starts directly when no tmux session is running."""
        with (
            patch.object(task_manager, "_is_session_running", return_value=False),
            patch.object(task_manager, "_start_task_now", return_value=(True, "Started")),
        ):
            success, msg = task_manager.start_task("proj", Path("/tmp/proj"), "build", 5)
        assert success is True
        assert msg == "Started"

    def test_start_task_queues_when_session_running(self, task_manager):
        """Task is queued when a tmux session is already running."""
        with patch.object(task_manager, "_is_session_running", return_value=True):
            success, msg = task_manager.start_task("proj", Path("/tmp/proj"), "build", 5)
        assert success is True
        assert "Queued" in msg
        assert len(task_manager.get_queue(Path("/tmp/proj"))) == 1

    def test_queue_respects_max_size(self, task_manager):
        """Queue rejects tasks when MAX_QUEUE_SIZE is reached."""
        with patch.object(task_manager, "_is_session_running", return_value=True):
            # Fill the queue up to MAX_QUEUE_SIZE (10)
            for i in range(10):
                success, _ = task_manager.start_task("proj", Path("/tmp/proj"), "build", 5)
                assert success is True

            # 11th should fail
            success, msg = task_manager.start_task("proj", Path("/tmp/proj"), "build", 5)
            assert success is False
            assert "full" in msg.lower()

    def test_cancel_queued_task(self, task_manager):
        """Cancelling a queued task removes it from the queue."""
        with patch.object(task_manager, "_is_session_running", return_value=True):
            task_manager.start_task("proj", Path("/tmp/proj"), "build", 5)

        queue = task_manager.get_queue(Path("/tmp/proj"))
        task_id = queue[0].id

        assert task_manager.cancel_queued_task(Path("/tmp/proj"), task_id) is True
        assert len(task_manager.get_queue(Path("/tmp/proj"))) == 0

    def test_cancel_nonexistent_task_returns_false(self, task_manager):
        assert task_manager.cancel_queued_task(Path("/tmp/proj"), "nonexistent") is False

    def test_get_queue_returns_empty_for_unknown_project(self, task_manager):
        assert task_manager.get_queue(Path("/tmp/unknown")) == []

    def test_start_task_refuses_when_disk_low(self, task_manager):
        """start_task() returns (False, MSG_DISK_LOW) when disk space is critically low."""
        with (
            patch.object(task_manager, "_is_session_running", return_value=False),
            patch("src.telegram_bot.tasks.check_disk_space", return_value=(False, 100.0)),
        ):
            success, msg = task_manager.start_task("proj", Path("/tmp/proj"), "build", 5)
        assert success is False
        assert "Disk space low" in msg

    def test_start_task_proceeds_when_disk_ok(self, task_manager):
        """start_task() proceeds normally when disk space is sufficient."""
        with (
            patch.object(task_manager, "_is_session_running", return_value=False),
            patch.object(task_manager, "_start_task_now", return_value=(True, "Started")),
            patch("src.telegram_bot.tasks.check_disk_space", return_value=(True, 5000.0)),
        ):
            success, msg = task_manager.start_task("proj", Path("/tmp/proj"), "build", 5)
        assert success is True
        assert msg == "Started"


class TestTaskManagerIsSessionRunning:
    """Tests for _is_session_running() tmux check."""

    def test_returns_true_when_session_exists(self, task_manager):
        mock_result = MagicMock(returncode=0)
        with patch("src.telegram_bot.tasks.subprocess.run", return_value=mock_result):
            assert task_manager._is_session_running("loop-proj") is True

    def test_returns_false_when_session_absent(self, task_manager):
        mock_result = MagicMock(returncode=1)
        with patch("src.telegram_bot.tasks.subprocess.run", return_value=mock_result):
            assert task_manager._is_session_running("loop-proj") is False

    def test_returns_false_on_timeout(self, task_manager):
        with patch(
            "src.telegram_bot.tasks.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="tmux", timeout=5),
        ):
            assert task_manager._is_session_running("loop-proj") is False


class TestTaskManagerDuration:
    """Tests for get_task_duration()."""

    def test_formats_seconds(self, task_manager):
        from src.telegram_bot.tasks import Task
        task = Task(
            project="proj",
            project_path=Path("/tmp/proj"),
            mode="build",
            iterations=5,
            idea=None,
            session_name="loop-proj",
        )
        # Override started_at to a known value
        from datetime import timedelta
        task.started_at = datetime.now() - timedelta(seconds=45)
        result = task_manager.get_task_duration(task)
        assert result == "45s"

    def test_formats_minutes_and_seconds(self, task_manager):
        from src.telegram_bot.tasks import Task
        from datetime import timedelta
        task = Task(
            project="proj",
            project_path=Path("/tmp/proj"),
            mode="plan",
            iterations=3,
            idea=None,
            session_name="loop-proj",
        )
        task.started_at = datetime.now() - timedelta(minutes=3, seconds=15)
        result = task_manager.get_task_duration(task)
        assert result == "3m 15s"


class TestTaskManagerIteration:
    """Tests for get_current_iteration() — reading progress file."""

    def test_reads_iteration_number(self, tmp_path, task_manager):
        from src.telegram_bot.tasks import Task
        task = Task(
            project="proj",
            project_path=tmp_path,
            mode="build",
            iterations=5,
            idea=None,
            session_name="loop-proj",
        )
        progress_dir = tmp_path / "loop" / "logs"
        progress_dir.mkdir(parents=True)
        (progress_dir / ".progress").write_text("3")
        assert task_manager.get_current_iteration(task) == 3

    def test_returns_none_when_no_file(self, tmp_path, task_manager):
        from src.telegram_bot.tasks import Task
        task = Task(
            project="proj",
            project_path=tmp_path,
            mode="build",
            iterations=5,
            idea=None,
            session_name="loop-proj",
        )
        assert task_manager.get_current_iteration(task) is None

    def test_returns_none_on_invalid_content(self, tmp_path, task_manager):
        from src.telegram_bot.tasks import Task
        task = Task(
            project="proj",
            project_path=tmp_path,
            mode="build",
            iterations=5,
            idea=None,
            session_name="loop-proj",
        )
        progress_dir = tmp_path / "loop" / "logs"
        progress_dir.mkdir(parents=True)
        (progress_dir / ".progress").write_text("not a number")
        assert task_manager.get_current_iteration(task) is None


class TestBrainstormManagerTmpDir:
    """Tests for BrainstormManager.TMP_DIR — persistent brainstorm output dir."""

    def test_tmp_dir_under_projects_root(self, tmp_path):
        """TMP_DIR should be PROJECTS_ROOT/.brainstorm (not /tmp)."""
        with (
            patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)),
            patch("src.telegram_bot.tasks.BrainstormManager._is_session_running", return_value=False),
        ):
            from src.telegram_bot.tasks import BrainstormManager
            bm = BrainstormManager()
        assert bm.TMP_DIR == tmp_path / ".brainstorm"

    def test_tmp_dir_created_on_init(self, tmp_path):
        """__init__ creates .brainstorm directory if it doesn't exist."""
        with (
            patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)),
            patch("src.telegram_bot.tasks.BrainstormManager._is_session_running", return_value=False),
        ):
            from src.telegram_bot.tasks import BrainstormManager
            bm = BrainstormManager()
        assert bm.TMP_DIR.is_dir()

    def test_tmp_dir_survives_existing_directory(self, tmp_path):
        """__init__ succeeds if .brainstorm already exists (exist_ok=True)."""
        (tmp_path / ".brainstorm").mkdir()
        with (
            patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)),
            patch("src.telegram_bot.tasks.BrainstormManager._is_session_running", return_value=False),
        ):
            from src.telegram_bot.tasks import BrainstormManager
            bm = BrainstormManager()
        assert bm.TMP_DIR.is_dir()

    def test_output_files_go_to_brainstorm_dir(self, tmp_path):
        """_output_file_path() returns a path under .brainstorm directory."""
        with (
            patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)),
            patch("src.telegram_bot.tasks.BrainstormManager._is_session_running", return_value=False),
        ):
            from src.telegram_bot.tasks import BrainstormManager
            bm = BrainstormManager()
        path = bm._output_file_path(12345)
        assert path.parent == tmp_path / ".brainstorm"
        assert "brainstorm_12345_" in path.name
        assert path.suffix == ".jsonl"


class TestBrainstormManagerSessionPersistence:
    """Tests for BrainstormManager session serialization/deserialization."""

    def test_save_and_load_round_trip(self, tmp_path):
        """Sessions saved to JSON can be restored (round-trip)."""
        from src.telegram_bot.tasks import BrainstormManager, BrainstormSession

        with patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)):
            bm = BrainstormManager.__new__(BrainstormManager)
            bm.sessions = {}

            session = BrainstormSession(
                chat_id=12345,
                project="test-proj",
                project_path=Path("/tmp/test-proj"),
                session_id="sess-abc",
                tmux_session="brainstorm-12345",
                output_file=Path("/tmp/brainstorm_12345_abcdef.jsonl"),
                initial_prompt="Discuss feature X",
                started_at=datetime(2026, 2, 7, 10, 30, 0),
                status="ready",
                last_response="Claude's response here",
            )
            bm.sessions[12345] = session
            bm._save_sessions()

            # Verify file was written
            sessions_file = tmp_path / ".brainstorm_sessions.json"
            assert sessions_file.exists()
            data = json.loads(sessions_file.read_text())
            assert len(data) == 1
            assert data[0]["chat_id"] == 12345
            assert data[0]["project"] == "test-proj"
            assert data[0]["session_id"] == "sess-abc"
            assert data[0]["status"] == "ready"

    def test_load_skips_stale_sessions(self, tmp_path):
        """Sessions whose tmux session no longer exists are removed on load."""
        from src.telegram_bot.tasks import BrainstormManager

        sessions_file = tmp_path / ".brainstorm_sessions.json"
        sessions_file.write_text(json.dumps([{
            "chat_id": 12345,
            "project": "test-proj",
            "project_path": str(tmp_path),
            "session_id": "sess-abc",
            "tmux_session": "brainstorm-12345",
            "initial_prompt": "test",
            "started_at": "2026-02-07T10:30:00",
            "status": "ready",
        }]))

        with (
            patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)),
            # tmux session does NOT exist
            patch("src.telegram_bot.tasks.BrainstormManager._is_session_running", return_value=False),
        ):
            bm = BrainstormManager()

        # Stale session should NOT be loaded
        assert len(bm.sessions) == 0

    def test_load_restores_active_sessions(self, tmp_path):
        """Sessions whose tmux session exists are restored."""
        from src.telegram_bot.tasks import BrainstormManager

        sessions_file = tmp_path / ".brainstorm_sessions.json"
        sessions_file.write_text(json.dumps([{
            "chat_id": 12345,
            "project": "test-proj",
            "project_path": str(tmp_path),
            "session_id": "sess-abc",
            "tmux_session": "brainstorm-12345",
            "initial_prompt": "test prompt",
            "started_at": "2026-02-07T10:30:00",
            "status": "ready",
        }]))

        with (
            patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)),
            # tmux session exists
            patch("src.telegram_bot.tasks.BrainstormManager._is_session_running", return_value=True),
        ):
            bm = BrainstormManager()

        assert 12345 in bm.sessions
        assert bm.sessions[12345].project == "test-proj"
        assert bm.sessions[12345].session_id == "sess-abc"

    def test_load_handles_missing_file(self, tmp_path):
        """No crash when sessions file doesn't exist."""
        with patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)):
            from src.telegram_bot.tasks import BrainstormManager
            bm = BrainstormManager()
        assert len(bm.sessions) == 0

    def test_load_handles_corrupt_json(self, tmp_path):
        """Corrupt JSON file is handled gracefully."""
        sessions_file = tmp_path / ".brainstorm_sessions.json"
        sessions_file.write_text("not valid json {{{")

        with patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)):
            from src.telegram_bot.tasks import BrainstormManager
            bm = BrainstormManager()
        assert len(bm.sessions) == 0


class TestBrainstormManagerParseStreamJson:
    """Tests for _parse_stream_json() — extracting results from JSONL output."""

    def test_parses_success_result(self, brainstorm_manager, tmp_path):
        output_file = tmp_path / "output.jsonl"
        output_file.write_text(
            '{"type":"assistant","message":"thinking..."}\n'
            '{"type":"result","result":"Claude response","session_id":"sess-123","is_error":false}\n'
        )
        found, response, session_id = brainstorm_manager._parse_stream_json(output_file)
        assert found is True
        assert response == "Claude response"
        assert session_id == "sess-123"

    def test_parses_error_result(self, brainstorm_manager, tmp_path):
        output_file = tmp_path / "output.jsonl"
        output_file.write_text(
            '{"type":"result","result":"Something went wrong","session_id":"sess-err","is_error":true}\n'
        )
        found, response, session_id = brainstorm_manager._parse_stream_json(output_file)
        assert found is True
        assert "Claude error" in response
        assert session_id == "sess-err"

    def test_returns_false_for_missing_file(self, brainstorm_manager, tmp_path):
        found, response, session_id = brainstorm_manager._parse_stream_json(tmp_path / "missing.jsonl")
        assert found is False
        assert response == ""
        assert session_id is None

    def test_returns_false_for_empty_file(self, brainstorm_manager, tmp_path):
        output_file = tmp_path / "empty.jsonl"
        output_file.write_text("")
        found, response, session_id = brainstorm_manager._parse_stream_json(output_file)
        assert found is False

    def test_returns_false_when_no_result_type(self, brainstorm_manager, tmp_path):
        output_file = tmp_path / "no_result.jsonl"
        output_file.write_text('{"type":"assistant","message":"still thinking"}\n')
        found, _, _ = brainstorm_manager._parse_stream_json(output_file)
        assert found is False

    def test_handles_malformed_json_lines(self, brainstorm_manager, tmp_path):
        """Malformed JSON lines are skipped; valid result line is still found."""
        output_file = tmp_path / "mixed.jsonl"
        output_file.write_text(
            'not json at all\n'
            '{"type":"result","result":"good response","session_id":"s1"}\n'
        )
        found, response, session_id = brainstorm_manager._parse_stream_json(output_file)
        assert found is True
        assert response == "good response"


class TestBrainstormManagerCancel:
    """Tests for cancel() — session cleanup."""

    def test_cancel_existing_session(self, brainstorm_manager):
        from src.telegram_bot.tasks import BrainstormSession
        session = BrainstormSession(
            chat_id=99,
            project="proj",
            project_path=Path("/tmp/proj"),
            session_id="sess-1",
            tmux_session="brainstorm-99",
            output_file=Path("/tmp/out.jsonl"),
            initial_prompt="test",
        )
        brainstorm_manager.sessions[99] = session

        with (
            patch.object(brainstorm_manager, "_is_session_running", return_value=False),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            assert brainstorm_manager.cancel(99) is True
        assert 99 not in brainstorm_manager.sessions

    def test_cancel_nonexistent_session(self, brainstorm_manager):
        assert brainstorm_manager.cancel(999) is False


class TestBrainstormManagerStartErrors:
    """Tests for start() — error conditions (async generator)."""

    @pytest.mark.asyncio
    async def test_start_yields_error_when_session_active(self, brainstorm_manager):
        """Starting a session when one is already active yields ERR_SESSION_ACTIVE."""
        from src.telegram_bot.tasks import BrainstormSession
        brainstorm_manager.sessions[42] = BrainstormSession(
            chat_id=42,
            project="proj",
            project_path=Path("/tmp/proj"),
            session_id="sess-1",
            tmux_session="brainstorm-42",
            output_file=Path("/tmp/out.jsonl"),
            initial_prompt="test",
        )

        results = []
        async for error_code, msg, is_final in brainstorm_manager.start(42, "proj", Path("/tmp/proj"), "new prompt"):
            results.append((error_code, msg, is_final))

        assert len(results) == 1
        assert results[0][0] == ERR_SESSION_ACTIVE
        assert results[0][2] is True  # is_final


class TestBrainstormManagerRespondErrors:
    """Tests for respond() — error conditions (async generator)."""

    @pytest.mark.asyncio
    async def test_respond_no_session_yields_error(self, brainstorm_manager):
        results = []
        async for error_code, msg, is_final in brainstorm_manager.respond(42, "hello"):
            results.append((error_code, msg, is_final))

        assert len(results) == 1
        assert results[0][0] == ERR_NO_SESSION
        assert results[0][2] is True

    @pytest.mark.asyncio
    async def test_respond_no_session_id_yields_not_ready(self, brainstorm_manager):
        from src.telegram_bot.tasks import BrainstormSession
        brainstorm_manager.sessions[42] = BrainstormSession(
            chat_id=42,
            project="proj",
            project_path=Path("/tmp/proj"),
            session_id=None,  # Not ready yet
            tmux_session="brainstorm-42",
            output_file=Path("/tmp/out.jsonl"),
            initial_prompt="test",
        )

        results = []
        async for error_code, msg, is_final in brainstorm_manager.respond(42, "hello"):
            results.append((error_code, msg, is_final))

        assert len(results) == 1
        assert results[0][0] == ERR_NOT_READY
        assert results[0][2] is True


class TestBrainstormManagerRespondHappyPath:
    """Tests for respond() async generator — successful session continuation.

    Covers: session continuation with --resume, prompt writing to tmux, response
    polling, session_id update, status transitions, output file creation,
    _save_sessions() persistence, and yield format (error_code, response, is_final).
    """

    def _setup_active_session(self, brainstorm_manager):
        """Create an active brainstorm session ready for respond()."""
        from src.telegram_bot.tasks import BrainstormSession

        session = BrainstormSession(
            chat_id=42,
            project="myproject",
            project_path=Path("/tmp/myproject"),
            session_id="sess-existing-123",
            tmux_session="brainstorm-42",
            output_file=Path("/tmp/old_output.jsonl"),
            initial_prompt="original prompt",
        )
        session.status = "ready"
        session.last_response = "previous response"
        brainstorm_manager.sessions[42] = session
        return session

    @pytest.mark.asyncio
    async def test_respond_happy_path_yields_two_tuples(self, brainstorm_manager):
        """Successful respond yields (thinking, final_response) — 2 tuples total."""
        self._setup_active_session(brainstorm_manager)

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "Here are my thoughts on that...", "sess-new-456"),
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            results = []
            async for error_code, msg, is_final in brainstorm_manager.respond(
                42, "What about caching?"
            ):
                results.append((error_code, msg, is_final))

        assert len(results) == 2
        # First yield: thinking status
        assert results[0] == (None, MSG_BRAINSTORM_CLAUDE_THINKING, False)
        # Second yield: final response
        assert results[1] == (None, "Here are my thoughts on that...", True)

    @pytest.mark.asyncio
    async def test_respond_updates_session_id_from_response(self, brainstorm_manager):
        """session_id from _wait_for_response replaces the old one on the session."""
        self._setup_active_session(brainstorm_manager)

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "response", "sess-updated-789"),
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            async for _ in brainstorm_manager.respond(42, "follow up"):
                pass

        session = brainstorm_manager.sessions[42]
        assert session.session_id == "sess-updated-789"

    @pytest.mark.asyncio
    async def test_respond_sets_status_ready_after_success(self, brainstorm_manager):
        """Session status is 'ready' after successful respond()."""
        self._setup_active_session(brainstorm_manager)

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "done", "s1"),
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            async for _ in brainstorm_manager.respond(42, "msg"):
                pass

        assert brainstorm_manager.sessions[42].status == "ready"

    @pytest.mark.asyncio
    async def test_respond_updates_last_response(self, brainstorm_manager):
        """last_response is updated to the new response text after respond()."""
        self._setup_active_session(brainstorm_manager)

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "new detailed answer", "s2"),
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            async for _ in brainstorm_manager.respond(42, "explain more"):
                pass

        assert brainstorm_manager.sessions[42].last_response == "new detailed answer"

    @pytest.mark.asyncio
    async def test_respond_passes_resume_session_id_to_tmux(self, brainstorm_manager):
        """respond() passes resume_session_id to _start_claude_in_tmux for --resume flag."""
        self._setup_active_session(brainstorm_manager)
        captured_kwargs = {}

        def capture_tmux_call(tmux_name, project_path, prompt, output_file, **kwargs):
            captured_kwargs.update(kwargs)
            captured_kwargs["tmux_name"] = tmux_name
            captured_kwargs["prompt"] = prompt
            return True

        with (
            patch.object(
                brainstorm_manager, "_start_claude_in_tmux", side_effect=capture_tmux_call
            ),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "ok", "s1"),
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            async for _ in brainstorm_manager.respond(42, "my follow-up question"):
                pass

        assert captured_kwargs["resume_session_id"] == "sess-existing-123"
        assert captured_kwargs["tmux_name"] == "brainstorm-42"
        assert captured_kwargs["prompt"] == "my follow-up question"

    @pytest.mark.asyncio
    async def test_respond_creates_new_output_file_per_turn(self, brainstorm_manager):
        """Each respond() call creates a new output file (different from previous turn)."""
        session = self._setup_active_session(brainstorm_manager)
        old_output = session.output_file
        captured_output = {}

        def capture_tmux_call(tmux_name, project_path, prompt, output_file, **kwargs):
            captured_output["file"] = output_file
            return True

        with (
            patch.object(
                brainstorm_manager, "_start_claude_in_tmux", side_effect=capture_tmux_call
            ),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "ok", "s1"),
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            async for _ in brainstorm_manager.respond(42, "msg"):
                pass

        new_output = captured_output["file"]
        assert new_output != old_output
        assert str(new_output).startswith(str(brainstorm_manager.TMP_DIR))
        assert "brainstorm_42_" in str(new_output)
        assert str(new_output).endswith(".jsonl")

    @pytest.mark.asyncio
    async def test_respond_saves_sessions_after_success(self, brainstorm_manager):
        """_save_sessions() is called after successful respond() to persist state."""
        self._setup_active_session(brainstorm_manager)

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "response", "s1"),
            ),
            patch.object(brainstorm_manager, "_save_sessions") as mock_save,
        ):
            async for _ in brainstorm_manager.respond(42, "msg"):
                pass

        mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_respond_tmux_failure_yields_error(self, brainstorm_manager):
        """When _start_claude_in_tmux fails, yields ERR_START_FAILED."""
        self._setup_active_session(brainstorm_manager)

        with patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=False):
            results = []
            async for error_code, msg, is_final in brainstorm_manager.respond(42, "msg"):
                results.append((error_code, msg, is_final))

        assert len(results) == 2
        assert results[0] == (None, MSG_BRAINSTORM_CLAUDE_THINKING, False)
        assert results[1][0] == ERR_START_FAILED
        assert results[1][2] is True

    @pytest.mark.asyncio
    async def test_respond_tmux_failure_sets_error_status(self, brainstorm_manager):
        """Session status is 'error' when tmux start fails."""
        self._setup_active_session(brainstorm_manager)

        with patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=False):
            async for _ in brainstorm_manager.respond(42, "msg"):
                pass

        assert brainstorm_manager.sessions[42].status == "error"

    @pytest.mark.asyncio
    async def test_respond_timeout_yields_error(self, brainstorm_manager):
        """When _wait_for_response returns ERR_TIMEOUT, error is propagated."""
        self._setup_active_session(brainstorm_manager)

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(ERR_TIMEOUT, "Timeout waiting", None),
            ),
        ):
            results = []
            async for error_code, msg, is_final in brainstorm_manager.respond(42, "msg"):
                results.append((error_code, msg, is_final))

        assert results[-1][0] == ERR_TIMEOUT
        assert results[-1][2] is True
        assert brainstorm_manager.sessions[42].status == "error"

    @pytest.mark.asyncio
    async def test_respond_sets_status_responding_during_wait(self, brainstorm_manager):
        """Session status transitions to 'responding' before _wait_for_response."""
        self._setup_active_session(brainstorm_manager)
        statuses_during_wait = []

        async def capture_status(*args, **kwargs):
            session = brainstorm_manager.sessions.get(42)
            if session:
                statuses_during_wait.append(session.status)
            return (None, "response", "s1")

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager, "_wait_for_response", side_effect=capture_status
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            async for _ in brainstorm_manager.respond(42, "msg"):
                pass

        assert statuses_during_wait == ["responding"]

    @pytest.mark.asyncio
    async def test_respond_preserves_session_id_when_none_returned(self, brainstorm_manager):
        """If _wait_for_response returns None as session_id, the old one is kept."""
        self._setup_active_session(brainstorm_manager)

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "response", None),
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            async for _ in brainstorm_manager.respond(42, "msg"):
                pass

        # Original session_id preserved when new one is None
        assert brainstorm_manager.sessions[42].session_id == "sess-existing-123"


class TestBrainstormManagerStartHappyPath:
    """Tests for start() async generator — successful session creation and response flow.

    Covers: tmux session creation, initial prompt passing, JSONL output polling,
    session_id capture from _parse_stream_json(), status yields (error_code, response, is_final).
    """

    @pytest.mark.asyncio
    async def test_start_happy_path_yields_three_tuples(self, brainstorm_manager):
        """Successful start yields (starting, thinking, final_response) — 3 tuples total."""
        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "Great idea! Let's explore...", "sess-abc"),
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            results = []
            async for error_code, msg, is_final in brainstorm_manager.start(
                42, "myproject", Path("/tmp/myproject"), "Let's discuss architecture"
            ):
                results.append((error_code, msg, is_final))

        assert len(results) == 3
        # First yield: starting status
        assert results[0] == (None, MSG_BRAINSTORM_STARTING, False)
        # Second yield: thinking status
        assert results[1] == (None, MSG_BRAINSTORM_CLAUDE_THINKING, False)
        # Third yield: final response
        assert results[2] == (None, "Great idea! Let's explore...", True)

    @pytest.mark.asyncio
    async def test_start_registers_session_before_tmux(self, brainstorm_manager):
        """Session is registered in self.sessions before tmux starts."""
        registered_during_start = {}

        def capture_session(*args, **kwargs):
            # Capture session state when _start_claude_in_tmux is called
            registered_during_start.update(
                {cid: s.project for cid, s in brainstorm_manager.sessions.items()}
            )
            return True

        with (
            patch.object(
                brainstorm_manager, "_start_claude_in_tmux", side_effect=capture_session
            ),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "response", "sess-1"),
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            async for _ in brainstorm_manager.start(
                42, "proj", Path("/tmp/proj"), "prompt"
            ):
                pass

        assert 42 in registered_during_start
        assert registered_during_start[42] == "proj"

    @pytest.mark.asyncio
    async def test_start_captures_session_id_from_response(self, brainstorm_manager):
        """session_id from _wait_for_response is stored on the session object."""
        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "response text", "sess-xyz-123"),
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            async for _ in brainstorm_manager.start(
                42, "proj", Path("/tmp/proj"), "prompt"
            ):
                pass

        session = brainstorm_manager.sessions[42]
        assert session.session_id == "sess-xyz-123"
        assert session.status == "ready"
        assert session.last_response == "response text"

    @pytest.mark.asyncio
    async def test_start_passes_brainstorm_prefix_in_prompt(self, brainstorm_manager):
        """start() wraps the user prompt with /brainstorming skill prefix and context."""
        captured_args = {}

        def capture_tmux_call(tmux_name, project_path, prompt, output_file, **kwargs):
            captured_args["prompt"] = prompt
            captured_args["tmux_name"] = tmux_name
            return True

        with (
            patch.object(
                brainstorm_manager, "_start_claude_in_tmux", side_effect=capture_tmux_call
            ),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "ok", "s1"),
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            async for _ in brainstorm_manager.start(
                42, "proj", Path("/tmp/proj"), "discuss auth"
            ):
                pass

        assert captured_args["prompt"].startswith("/brainstorming ")
        assert "discuss auth" in captured_args["prompt"]
        assert "DO NOT write code" in captured_args["prompt"]
        assert captured_args["tmux_name"] == "brainstorm-42"

    @pytest.mark.asyncio
    async def test_start_saves_sessions_after_success(self, brainstorm_manager):
        """_save_sessions() is called after a successful start to persist state."""
        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "response", "sess-1"),
            ),
            patch.object(brainstorm_manager, "_save_sessions") as mock_save,
        ):
            async for _ in brainstorm_manager.start(
                42, "proj", Path("/tmp/proj"), "prompt"
            ):
                pass

        mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_tmux_failure_yields_error_and_cleans_up(self, brainstorm_manager):
        """When _start_claude_in_tmux fails, yields ERR_START_FAILED and cleans session."""
        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=False),
            patch.object(brainstorm_manager, "_cleanup_session") as mock_cleanup,
        ):
            results = []
            async for error_code, msg, is_final in brainstorm_manager.start(
                42, "proj", Path("/tmp/proj"), "prompt"
            ):
                results.append((error_code, msg, is_final))

        # Starting status + error — 2 yields total
        assert len(results) == 2
        assert results[0] == (None, MSG_BRAINSTORM_STARTING, False)
        assert results[1][0] == ERR_START_FAILED
        assert results[1][2] is True
        mock_cleanup.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_start_timeout_yields_error_and_cleans_up(self, brainstorm_manager):
        """When _wait_for_response returns ERR_TIMEOUT, session is cleaned up."""
        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(ERR_TIMEOUT, "Timeout waiting for Claude response", None),
            ),
            patch.object(brainstorm_manager, "_cleanup_session") as mock_cleanup,
        ):
            results = []
            async for error_code, msg, is_final in brainstorm_manager.start(
                42, "proj", Path("/tmp/proj"), "prompt"
            ):
                results.append((error_code, msg, is_final))

        assert len(results) == 3
        assert results[2][0] == ERR_TIMEOUT
        assert results[2][2] is True
        # _cleanup_session called to tear down the failed session
        mock_cleanup.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_start_no_result_yields_error_and_cleans_up(self, brainstorm_manager):
        """When _wait_for_response returns ERR_NO_RESULT, session is cleaned up."""
        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(ERR_NO_RESULT, "Claude ended without result", None),
            ),
            patch.object(brainstorm_manager, "_cleanup_session") as mock_cleanup,
        ):
            results = []
            async for error_code, msg, is_final in brainstorm_manager.start(
                42, "proj", Path("/tmp/proj"), "prompt"
            ):
                results.append((error_code, msg, is_final))

        assert results[-1][0] == ERR_NO_RESULT
        assert results[-1][2] is True
        mock_cleanup.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_start_sets_session_status_responding_during_wait(self, brainstorm_manager):
        """Session status transitions: waiting → responding during _wait_for_response."""
        statuses_during_wait = []

        async def capture_status(*args, **kwargs):
            session = brainstorm_manager.sessions.get(42)
            if session:
                statuses_during_wait.append(session.status)
            return (None, "response", "sess-1")

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager, "_wait_for_response", side_effect=capture_status
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            async for _ in brainstorm_manager.start(
                42, "proj", Path("/tmp/proj"), "prompt"
            ):
                pass

        assert statuses_during_wait == ["responding"]

    @pytest.mark.asyncio
    async def test_start_output_file_in_brainstorm_dir(self, brainstorm_manager):
        """Output file path is under TMP_DIR (.brainstorm directory)."""
        captured_output = {}

        def capture_tmux_call(tmux_name, project_path, prompt, output_file, **kwargs):
            captured_output["file"] = output_file
            return True

        with (
            patch.object(
                brainstorm_manager, "_start_claude_in_tmux", side_effect=capture_tmux_call
            ),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "ok", "s1"),
            ),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            async for _ in brainstorm_manager.start(
                42, "proj", Path("/tmp/proj"), "prompt"
            ):
                pass

        output_file = captured_output["file"]
        assert str(output_file).startswith(str(brainstorm_manager.TMP_DIR))
        assert "brainstorm_42_" in str(output_file)
        assert str(output_file).endswith(".jsonl")


class TestTaskManagerPersistence:
    """Tests for TaskManager task state persistence to disk."""

    @pytest.fixture
    def ptm(self, tmp_path):
        """Create a TaskManager with PROJECTS_ROOT patched to tmp_path.

        Uses a context manager-style fixture so the patch stays active
        for the entire test method.
        """
        with (
            patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)),
            patch("src.telegram_bot.tasks.check_disk_space", return_value=(True, 5000.0)),
        ):
            from src.telegram_bot.tasks import TaskManager
            tm = TaskManager()
            tm._tmp_path = tmp_path  # convenience ref for assertions
            yield tm

    def test_tasks_file_path(self, ptm):
        """_tasks_file() returns PROJECTS_ROOT/.tasks.json."""
        assert ptm._tasks_file() == ptm._tmp_path / ".tasks.json"

    def test_save_and_load_active_task(self, tmp_path):
        """Active tasks are persisted and restored on load."""
        from src.telegram_bot.tasks import Task

        with patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)):
            from src.telegram_bot.tasks import TaskManager
            tm = TaskManager()

            task = Task(
                project="proj",
                project_path=Path("/tmp/proj"),
                mode="build",
                iterations=5,
                idea="test idea",
                session_name="loop-proj",
                start_commit="abc123",
                last_reported_iteration=2,
                stale_warned=True,
            )
            tm.active_tasks["/tmp/proj"] = task
            tm._save_tasks()

            # Verify file written
            assert (tmp_path / ".tasks.json").exists()

            # Load into a new manager, with tmux session running
            tm2 = TaskManager.__new__(TaskManager)
            tm2.active_tasks = {}
            tm2.queues = {}
            tm2._queue_lock = __import__("threading").Lock()
            with patch.object(tm2, "_is_session_running", return_value=True):
                tm2._load_tasks()

        restored = tm2.active_tasks.get("/tmp/proj")
        assert restored is not None
        assert restored.project == "proj"
        assert restored.mode == "build"
        assert restored.iterations == 5
        assert restored.idea == "test idea"
        assert restored.session_name == "loop-proj"
        assert restored.start_commit == "abc123"

    def test_save_and_load_queued_tasks(self, tmp_path):
        """Queued tasks are persisted and restored."""
        from src.telegram_bot.tasks import QueuedTask

        with patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)):
            from src.telegram_bot.tasks import TaskManager
            tm = TaskManager()

            tm.queues["/tmp/proj"] = [
                QueuedTask(
                    id="abc1",
                    project="proj",
                    project_path=Path("/tmp/proj"),
                    mode="plan",
                    iterations=3,
                    idea="first idea",
                ),
                QueuedTask(
                    id="abc2",
                    project="proj",
                    project_path=Path("/tmp/proj"),
                    mode="build",
                    iterations=5,
                    idea=None,
                ),
            ]
            tm._save_tasks()

            tm2 = TaskManager.__new__(TaskManager)
            tm2.active_tasks = {}
            tm2.queues = {}
            tm2._queue_lock = __import__("threading").Lock()
            tm2._load_tasks()

        queue = tm2.queues.get("/tmp/proj", [])
        assert len(queue) == 2
        assert queue[0].id == "abc1"
        assert queue[0].mode == "plan"
        assert queue[0].idea == "first idea"
        assert queue[1].id == "abc2"
        assert queue[1].idea is None

    def test_load_removes_stale_tasks(self, tmp_path):
        """Tasks whose tmux session no longer exists are removed on load."""
        from src.telegram_bot.tasks import Task

        with patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)):
            from src.telegram_bot.tasks import TaskManager
            tm = TaskManager()

            task = Task(
                project="stale-proj",
                project_path=Path("/tmp/stale-proj"),
                mode="build",
                iterations=5,
                idea=None,
                session_name="loop-stale-proj",
            )
            tm.active_tasks["/tmp/stale-proj"] = task
            tm._save_tasks()

            # Load with tmux session NOT running — task should be removed
            tm2 = TaskManager.__new__(TaskManager)
            tm2.active_tasks = {}
            tm2.queues = {}
            tm2._queue_lock = __import__("threading").Lock()
            with patch.object(tm2, "_is_session_running", return_value=False):
                tm2._load_tasks()

        assert "/tmp/stale-proj" not in tm2.active_tasks

    def test_load_handles_missing_file(self, ptm):
        """No crash when .tasks.json doesn't exist."""
        ptm.active_tasks.clear()
        ptm.queues.clear()
        ptm._load_tasks()  # Should not raise
        assert len(ptm.active_tasks) == 0

    def test_load_handles_corrupt_json(self, tmp_path):
        """Corrupt JSON is handled gracefully."""
        (tmp_path / ".tasks.json").write_text("not valid {{{")
        with patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)):
            from src.telegram_bot.tasks import TaskManager
            tm = TaskManager()
        assert len(tm.active_tasks) == 0

    def test_save_uses_atomic_write(self, ptm):
        """Save uses temp file + os.replace for atomicity."""
        ptm._save_tasks()

        # After save, no .tmp file should remain
        assert not (ptm._tmp_path / ".tasks.json.tmp").exists()
        assert (ptm._tmp_path / ".tasks.json").exists()

    def test_save_called_after_start_task(self, ptm):
        """_save_tasks is called when a task starts successfully."""
        with (
            patch.object(ptm, "_is_session_running", return_value=False),
            patch("src.telegram_bot.tasks.subprocess.run") as mock_run,
            patch("src.telegram_bot.tasks.get_commit_hash", return_value="abc"),
            patch.object(ptm, "_save_tasks") as mock_save,
        ):
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            ptm.start_task("proj", Path("/tmp/proj"), "build", 5)
        mock_save.assert_called()

    def test_save_called_after_process_completed(self, ptm):
        """_save_tasks is called when a task completes."""
        from src.telegram_bot.tasks import Task
        task = Task(
            project="proj",
            project_path=Path("/tmp/proj"),
            mode="build",
            iterations=5,
            idea=None,
            session_name="loop-proj",
        )
        ptm.active_tasks["/tmp/proj"] = task

        with (
            patch.object(ptm, "_is_session_running", return_value=False),
            patch.object(ptm, "_save_tasks") as mock_save,
        ):
            ptm.process_completed_tasks()
        mock_save.assert_called()

    def test_save_called_after_cancel_queued(self, ptm):
        """_save_tasks is called when a queued task is cancelled."""
        with patch.object(ptm, "_is_session_running", return_value=True):
            ptm.start_task("proj", Path("/tmp/proj"), "build", 5)

        queue = ptm.get_queue(Path("/tmp/proj"))
        task_id = queue[0].id

        with patch.object(ptm, "_save_tasks") as mock_save:
            ptm.cancel_queued_task(Path("/tmp/proj"), task_id)
        mock_save.assert_called()

    def test_load_on_init(self, tmp_path):
        """TaskManager calls _load_tasks on __init__."""
        from src.telegram_bot.tasks import QueuedTask

        with patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)):
            from src.telegram_bot.tasks import TaskManager
            # Save some state first
            tm = TaskManager()
            tm.queues["/tmp/proj"] = [
                QueuedTask(
                    id="q1",
                    project="proj",
                    project_path=Path("/tmp/proj"),
                    mode="build",
                    iterations=5,
                    idea=None,
                ),
            ]
            tm._save_tasks()

            # Create new manager — should auto-load
            tm2 = TaskManager()
            queue = tm2.queues.get("/tmp/proj", [])
            assert len(queue) == 1
            assert queue[0].id == "q1"

    def test_completed_task_while_bot_down(self, tmp_path):
        """Task that completed while bot was down is detected and cleaned up."""
        from src.telegram_bot.tasks import Task, QueuedTask

        with patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)):
            from src.telegram_bot.tasks import TaskManager
            tm = TaskManager()

            task = Task(
                project="proj",
                project_path=Path("/tmp/proj"),
                mode="build",
                iterations=5,
                idea=None,
                session_name="loop-proj",
                status="running",
            )
            tm.active_tasks["/tmp/proj"] = task
            tm.queues["/tmp/proj"] = [
                QueuedTask(
                    id="q1",
                    project="proj",
                    project_path=Path("/tmp/proj"),
                    mode="plan",
                    iterations=3,
                    idea=None,
                ),
            ]
            tm._save_tasks()

            # Load with tmux NOT running — stale task removed, queue preserved
            tm2 = TaskManager.__new__(TaskManager)
            tm2.active_tasks = {}
            tm2.queues = {}
            tm2._queue_lock = __import__("threading").Lock()
            with patch.object(tm2, "_is_session_running", return_value=False):
                tm2._load_tasks()

        # Stale active task should be removed
        assert "/tmp/proj" not in tm2.active_tasks
        # Queue should still be present for process_completed_tasks to pick up
        assert len(tm2.queues.get("/tmp/proj", [])) == 1


class TestProcessCompletedTasks:
    """Tests for TaskManager.process_completed_tasks() workflow.

    Covers: completed session detection, active task removal, queue-next start,
    return tuple format, and orphaned queue handling.
    """

    @pytest.fixture
    def ptm(self, tmp_path):
        """TaskManager with PROJECTS_ROOT patched to tmp_path."""
        with (
            patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)),
            patch("src.telegram_bot.tasks.check_disk_space", return_value=(True, 5000.0)),
        ):
            from src.telegram_bot.tasks import TaskManager
            tm = TaskManager()
            yield tm

    def _make_task(self, project="proj", mode="build", iterations=5):
        from src.telegram_bot.tasks import Task
        return Task(
            project=project,
            project_path=Path(f"/tmp/{project}"),
            mode=mode,
            iterations=iterations,
            idea=None,
            session_name=f"loop-{project}",
        )

    def test_completed_task_removed_from_active(self, ptm):
        """Completed task (tmux gone) is removed from active_tasks."""
        task = self._make_task()
        ptm.active_tasks["/tmp/proj"] = task

        with (
            patch.object(ptm, "_is_session_running", return_value=False),
            patch.object(ptm, "_save_tasks"),
        ):
            results, _ = ptm.process_completed_tasks()

        assert "/tmp/proj" not in ptm.active_tasks
        assert len(results) == 1
        completed, next_task = results[0]
        assert completed.project == "proj"
        assert next_task is None

    def test_active_task_not_removed_when_session_running(self, ptm):
        """Active task with running tmux session is not touched."""
        task = self._make_task()
        ptm.active_tasks["/tmp/proj"] = task

        with patch.object(ptm, "_is_session_running", return_value=True):
            results, _ = ptm.process_completed_tasks()

        assert "/tmp/proj" in ptm.active_tasks
        assert results == []

    def test_queue_next_started_after_completion(self, ptm):
        """When task completes and queue has items, next task starts."""
        task = self._make_task(project="proj")
        ptm.active_tasks["/tmp/proj"] = task

        # Add a queued task
        from src.telegram_bot.tasks import QueuedTask
        ptm.queues["/tmp/proj"] = [
            QueuedTask(
                id="q1",
                project="proj",
                project_path=Path("/tmp/proj"),
                mode="plan",
                iterations=3,
                idea=None,
            ),
        ]

        with (
            patch.object(ptm, "_is_session_running", return_value=False),
            patch.object(ptm, "_start_task_now", return_value=(True, "Started")) as mock_start,
            patch.object(ptm, "_save_tasks"),
        ):
            # After _start_task_now succeeds, simulate the new task in active_tasks
            from src.telegram_bot.tasks import Task
            new_task = Task(
                project="proj",
                project_path=Path("/tmp/proj"),
                mode="plan",
                iterations=3,
                idea=None,
                session_name="loop-proj",
            )

            def fake_start(**kwargs):
                ptm.active_tasks["/tmp/proj"] = new_task
                return (True, "Started")

            mock_start.side_effect = lambda **kwargs: fake_start(**kwargs)
            results, _ = ptm.process_completed_tasks()

        assert len(results) == 1
        completed, next_started = results[0]
        assert completed.project == "proj"
        assert completed.mode == "build"
        assert next_started is not None
        assert next_started.mode == "plan"
        mock_start.assert_called_once_with(
            project="proj",
            project_path=Path("/tmp/proj"),
            mode="plan",
            iterations=3,
            idea=None,
        )

    def test_queue_item_restored_on_start_failure(self, ptm):
        """When _start_task_now fails, queued task is restored to queue front."""
        task = self._make_task()
        ptm.active_tasks["/tmp/proj"] = task

        from src.telegram_bot.tasks import QueuedTask
        ptm.queues["/tmp/proj"] = [
            QueuedTask(
                id="q1",
                project="proj",
                project_path=Path("/tmp/proj"),
                mode="plan",
                iterations=3,
                idea=None,
            ),
        ]

        with (
            patch.object(ptm, "_is_session_running", return_value=False),
            patch.object(ptm, "_start_task_now", return_value=(False, "Failed")),
            patch.object(ptm, "_save_tasks"),
        ):
            results, _ = ptm.process_completed_tasks()

        assert len(results) == 1
        completed, next_started = results[0]
        assert completed.project == "proj"
        assert next_started is None
        # Queue item should be restored
        assert len(ptm.queues["/tmp/proj"]) == 1
        assert ptm.queues["/tmp/proj"][0].id == "q1"

    def test_empty_active_tasks_returns_empty(self, ptm):
        """Returns empty list when there are no active tasks."""
        with patch.object(ptm, "_is_session_running", return_value=False):
            results, expired = ptm.process_completed_tasks()
        assert results == []
        assert expired == []

    def test_orphaned_queue_starts_task(self, ptm):
        """Orphaned queue (no active task) starts next task automatically."""
        from src.telegram_bot.tasks import QueuedTask, Task

        # No active task, but queue has items
        ptm.queues["/tmp/proj"] = [
            QueuedTask(
                id="q1",
                project="proj",
                project_path=Path("/tmp/proj"),
                mode="build",
                iterations=5,
                idea=None,
            ),
        ]

        new_task = Task(
            project="proj",
            project_path=Path("/tmp/proj"),
            mode="build",
            iterations=5,
            idea=None,
            session_name="loop-proj",
        )

        def fake_start_task_now(**kwargs):
            ptm.active_tasks["/tmp/proj"] = new_task
            return (True, "Started")

        with (
            patch.object(ptm, "_is_session_running", return_value=False),
            patch.object(ptm, "_start_task_now", side_effect=lambda **kw: fake_start_task_now(**kw)),
            patch.object(ptm, "_save_tasks"),
        ):
            results, _ = ptm.process_completed_tasks()

        assert len(results) == 1
        completed, next_started = results[0]
        assert completed is None  # orphaned — no completed task
        assert next_started is not None
        assert next_started.project == "proj"

    def test_orphaned_queue_skipped_when_session_running(self, ptm):
        """Orphaned queue is skipped if a tmux session is running for it."""
        from src.telegram_bot.tasks import QueuedTask

        ptm.queues["/tmp/proj"] = [
            QueuedTask(
                id="q1",
                project="proj",
                project_path=Path("/tmp/proj"),
                mode="build",
                iterations=5,
                idea=None,
            ),
        ]

        with patch.object(ptm, "_is_session_running", return_value=True):
            results, _ = ptm.process_completed_tasks()

        # Session running but no active task — could be recovering, don't start
        assert results == []

    def test_multiple_completed_tasks(self, ptm):
        """Multiple tasks completing in one cycle are all processed."""
        task_a = self._make_task(project="proj-a")
        task_b = self._make_task(project="proj-b", mode="plan", iterations=3)
        ptm.active_tasks["/tmp/proj-a"] = task_a
        ptm.active_tasks["/tmp/proj-b"] = task_b

        with (
            patch.object(ptm, "_is_session_running", return_value=False),
            patch.object(ptm, "_save_tasks"),
        ):
            results, _ = ptm.process_completed_tasks()

        assert len(results) == 2
        projects = {r[0].project for r in results}
        assert projects == {"proj-a", "proj-b"}
        assert len(ptm.active_tasks) == 0

    def test_return_tuple_format(self, ptm):
        """Return value is (list[(Task|None, Task|None)], list[QueuedTask])."""
        task = self._make_task()
        ptm.active_tasks["/tmp/proj"] = task

        with (
            patch.object(ptm, "_is_session_running", return_value=False),
            patch.object(ptm, "_save_tasks"),
        ):
            result = ptm.process_completed_tasks()

        assert isinstance(result, tuple)
        assert len(result) == 2
        results, expired = result
        assert isinstance(results, list)
        assert isinstance(expired, list)
        assert len(results) == 1
        completed, next_task = results[0]
        from src.telegram_bot.tasks import Task
        assert isinstance(completed, Task)
        assert next_task is None


class TestQueueTTLExpiry:
    """Tests for queue TTL expiry in process_completed_tasks().

    Queued tasks older than QUEUE_TTL seconds are automatically removed
    during periodic checks. Expired tasks are returned separately so
    bot.py can notify the user.
    """

    @pytest.fixture
    def ptm(self, tmp_path):
        """TaskManager with PROJECTS_ROOT patched to tmp_path."""
        with (
            patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)),
            patch("src.telegram_bot.tasks.check_disk_space", return_value=(True, 5000.0)),
        ):
            from src.telegram_bot.tasks import TaskManager
            tm = TaskManager()
            yield tm

    def _make_queued(self, id="q1", project="proj", mode="plan",
                     iterations=3, idea=None, queued_at=None):
        from src.telegram_bot.tasks import QueuedTask
        qt = QueuedTask(
            id=id,
            project=project,
            project_path=Path(f"/tmp/{project}"),
            mode=mode,
            iterations=iterations,
            idea=idea,
        )
        if queued_at is not None:
            qt.queued_at = queued_at
        return qt

    def test_expired_task_removed_from_queue(self, ptm):
        """Tasks older than QUEUE_TTL are removed from queue."""
        from datetime import timedelta

        # Queued 2 hours ago — well past the 1-hour default TTL
        old_time = datetime.now() - timedelta(hours=2)
        ptm.queues["/tmp/proj"] = [self._make_queued(queued_at=old_time)]

        with (
            patch.object(ptm, "_is_session_running", return_value=True),
            patch.object(ptm, "_save_tasks"),
        ):
            _, expired = ptm.process_completed_tasks()

        assert len(ptm.queues.get("/tmp/proj", [])) == 0
        assert len(expired) == 1
        assert expired[0].id == "q1"

    def test_fresh_task_not_expired(self, ptm):
        """Tasks within QUEUE_TTL are not removed."""
        ptm.queues["/tmp/proj"] = [self._make_queued()]  # just created, fresh

        with (
            patch.object(ptm, "_is_session_running", return_value=True),
            patch.object(ptm, "_save_tasks"),
        ):
            _, expired = ptm.process_completed_tasks()

        assert len(ptm.queues.get("/tmp/proj", [])) == 1
        assert expired == []

    def test_task_just_under_ttl_not_expired(self, ptm):
        """Task queued slightly less than QUEUE_TTL seconds ago is not expired."""
        from datetime import timedelta
        from src.telegram_bot.tasks import QUEUE_TTL

        # 10 seconds under boundary — definitely not expired
        just_under = datetime.now() - timedelta(seconds=QUEUE_TTL - 10)
        ptm.queues["/tmp/proj"] = [self._make_queued(queued_at=just_under)]

        with (
            patch.object(ptm, "_is_session_running", return_value=True),
            patch.object(ptm, "_save_tasks"),
        ):
            _, expired = ptm.process_completed_tasks()

        assert len(ptm.queues.get("/tmp/proj", [])) == 1
        assert expired == []

    def test_mixed_expired_and_fresh_tasks(self, ptm):
        """Only expired tasks are removed; fresh ones remain in order."""
        from datetime import timedelta

        old_time = datetime.now() - timedelta(hours=2)
        ptm.queues["/tmp/proj"] = [
            self._make_queued(id="old1", queued_at=old_time),
            self._make_queued(id="fresh1"),  # just created
            self._make_queued(id="old2", queued_at=old_time),
        ]

        with (
            patch.object(ptm, "_is_session_running", return_value=True),
            patch.object(ptm, "_save_tasks"),
        ):
            _, expired = ptm.process_completed_tasks()

        remaining = ptm.queues.get("/tmp/proj", [])
        assert len(remaining) == 1
        assert remaining[0].id == "fresh1"
        assert len(expired) == 2
        expired_ids = {e.id for e in expired}
        assert expired_ids == {"old1", "old2"}

    def test_expired_tasks_across_multiple_projects(self, ptm):
        """TTL check works across multiple project queues."""
        from datetime import timedelta

        old_time = datetime.now() - timedelta(hours=2)
        ptm.queues["/tmp/proj-a"] = [self._make_queued(id="qa", project="proj-a", queued_at=old_time)]
        ptm.queues["/tmp/proj-b"] = [self._make_queued(id="qb", project="proj-b")]  # fresh

        with (
            patch.object(ptm, "_is_session_running", return_value=True),
            patch.object(ptm, "_save_tasks"),
        ):
            _, expired = ptm.process_completed_tasks()

        assert len(ptm.queues.get("/tmp/proj-a", [])) == 0
        assert len(ptm.queues.get("/tmp/proj-b", [])) == 1
        assert len(expired) == 1
        assert expired[0].id == "qa"

    def test_expiry_saves_tasks(self, ptm):
        """Removing expired tasks triggers _save_tasks()."""
        from datetime import timedelta

        old_time = datetime.now() - timedelta(hours=2)
        ptm.queues["/tmp/proj"] = [self._make_queued(queued_at=old_time)]

        with (
            patch.object(ptm, "_is_session_running", return_value=True),
            patch.object(ptm, "_save_tasks") as mock_save,
        ):
            ptm.process_completed_tasks()

        mock_save.assert_called()

    def test_return_format_with_completions_and_expired(self, ptm):
        """process_completed_tasks returns (completions, expired) tuple."""
        from datetime import timedelta
        from src.telegram_bot.tasks import Task

        old_time = datetime.now() - timedelta(hours=2)
        ptm.queues["/tmp/proj"] = [self._make_queued(queued_at=old_time)]

        # Also add a completed task
        task = Task(
            project="proj2",
            project_path=Path("/tmp/proj2"),
            mode="build",
            iterations=5,
            idea=None,
            session_name="loop-proj2",
        )
        ptm.active_tasks["/tmp/proj2"] = task

        with (
            patch.object(ptm, "_is_session_running", return_value=False),
            patch.object(ptm, "_save_tasks"),
        ):
            completions, expired = ptm.process_completed_tasks()

        assert len(completions) == 1
        assert completions[0][0].project == "proj2"
        assert len(expired) == 1
        assert expired[0].id == "q1"


class TestPersistenceConcurrent:
    """Tests for task persistence under concurrent scenarios.

    Covers: save during queue operations, load with mixed valid/stale tasks,
    atomic write verification (os.replace pattern), _queue_lock behavior.
    """

    @pytest.fixture
    def ptm(self, tmp_path):
        """Create a TaskManager with PROJECTS_ROOT patched to tmp_path."""
        with (
            patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)),
            patch("src.telegram_bot.tasks.check_disk_space", return_value=(True, 5000.0)),
        ):
            from src.telegram_bot.tasks import TaskManager
            tm = TaskManager()
            tm._tmp_path = tmp_path
            yield tm

    def _make_task(self, project="proj", mode="build", iterations=5,
                   session_name=None, idea=None):
        from src.telegram_bot.tasks import Task
        return Task(
            project=project,
            project_path=Path(f"/tmp/{project}"),
            mode=mode,
            iterations=iterations,
            idea=idea,
            session_name=session_name or f"loop-{project}",
        )

    def _make_queued(self, id="q1", project="proj", mode="plan",
                     iterations=3, idea=None):
        from src.telegram_bot.tasks import QueuedTask
        return QueuedTask(
            id=id,
            project=project,
            project_path=Path(f"/tmp/{project}"),
            mode=mode,
            iterations=iterations,
            idea=idea,
        )

    def test_save_during_queue_add_is_consistent(self, ptm):
        """Saving while adding to queue produces consistent file state.

        Queue operations hold _queue_lock; _save_tasks acquires it separately
        for the queue portion, so the file always reflects a complete snapshot.
        """
        ptm.active_tasks["/tmp/proj"] = self._make_task()
        ptm.queues["/tmp/proj"] = [
            self._make_queued(id="q1"),
            self._make_queued(id="q2"),
        ]
        ptm._save_tasks()

        data = json.loads((ptm._tmp_path / ".tasks.json").read_text())
        assert "/tmp/proj" in data["active_tasks"]
        assert len(data["queues"]["/tmp/proj"]) == 2
        assert data["queues"]["/tmp/proj"][0]["id"] == "q1"
        assert data["queues"]["/tmp/proj"][1]["id"] == "q2"

    def test_save_preserves_queue_order_after_pop(self, ptm):
        """After popping from queue front, save reflects correct order."""
        ptm.queues["/tmp/proj"] = [
            self._make_queued(id="q1"),
            self._make_queued(id="q2"),
            self._make_queued(id="q3"),
        ]

        with ptm._queue_lock:
            ptm.queues["/tmp/proj"].pop(0)

        ptm._save_tasks()
        data = json.loads((ptm._tmp_path / ".tasks.json").read_text())
        ids = [q["id"] for q in data["queues"]["/tmp/proj"]]
        assert ids == ["q2", "q3"]

    def test_save_with_empty_queue_after_cancel(self, ptm):
        """Cancelling last queued task results in empty queue in saved state."""
        ptm.queues["/tmp/proj"] = [self._make_queued(id="q1")]

        with ptm._queue_lock:
            ptm.queues["/tmp/proj"].pop(0)

        ptm._save_tasks()
        data = json.loads((ptm._tmp_path / ".tasks.json").read_text())
        assert data["queues"]["/tmp/proj"] == []

    def test_load_mixed_valid_and_stale_tasks(self, tmp_path):
        """Load restores valid tasks and removes stale ones in the same file."""
        from src.telegram_bot.tasks import Task

        with patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)):
            from src.telegram_bot.tasks import TaskManager
            tm = TaskManager()

            # Two active tasks — one valid, one stale
            tm.active_tasks["/tmp/alive"] = Task(
                project="alive",
                project_path=Path("/tmp/alive"),
                mode="build",
                iterations=5,
                idea=None,
                session_name="loop-alive",
            )
            tm.active_tasks["/tmp/dead"] = Task(
                project="dead",
                project_path=Path("/tmp/dead"),
                mode="plan",
                iterations=3,
                idea=None,
                session_name="loop-dead",
            )
            tm._save_tasks()

            # Load: alive session running, dead session gone
            tm2 = TaskManager.__new__(TaskManager)
            tm2.active_tasks = {}
            tm2.queues = {}
            tm2._queue_lock = __import__("threading").Lock()

            def session_check(name):
                return name == "loop-alive"

            with patch.object(tm2, "_is_session_running", side_effect=session_check):
                tm2._load_tasks()

        assert "/tmp/alive" in tm2.active_tasks
        assert tm2.active_tasks["/tmp/alive"].project == "alive"
        assert "/tmp/dead" not in tm2.active_tasks

    def test_load_cleans_stale_and_preserves_queues(self, tmp_path):
        """Load removes stale active tasks but preserves queues for those projects."""
        from src.telegram_bot.tasks import Task, QueuedTask

        with patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)):
            from src.telegram_bot.tasks import TaskManager
            tm = TaskManager()

            tm.active_tasks["/tmp/proj"] = Task(
                project="proj",
                project_path=Path("/tmp/proj"),
                mode="build",
                iterations=5,
                idea=None,
                session_name="loop-proj",
            )
            tm.queues["/tmp/proj"] = [
                QueuedTask(
                    id="q1",
                    project="proj",
                    project_path=Path("/tmp/proj"),
                    mode="plan",
                    iterations=3,
                    idea=None,
                ),
            ]
            tm._save_tasks()

            tm2 = TaskManager.__new__(TaskManager)
            tm2.active_tasks = {}
            tm2.queues = {}
            tm2._queue_lock = __import__("threading").Lock()
            with patch.object(tm2, "_is_session_running", return_value=False):
                tm2._load_tasks()

        # Active task removed (stale), queue preserved
        assert "/tmp/proj" not in tm2.active_tasks
        assert len(tm2.queues.get("/tmp/proj", [])) == 1
        assert tm2.queues["/tmp/proj"][0].id == "q1"

    def test_atomic_write_no_tmp_on_success(self, ptm):
        """Successful save leaves no .tmp file behind (atomic os.replace)."""
        ptm.active_tasks["/tmp/proj"] = self._make_task()
        ptm._save_tasks()

        assert (ptm._tmp_path / ".tasks.json").exists()
        assert not (ptm._tmp_path / ".tasks.json.tmp").exists()

    def test_atomic_write_content_valid_json(self, ptm):
        """Saved file contains valid JSON that can be round-tripped."""
        ptm.active_tasks["/tmp/proj"] = self._make_task(idea="test idea")
        ptm.queues["/tmp/proj"] = [self._make_queued(id="q1", idea="queue idea")]
        ptm._save_tasks()

        raw = (ptm._tmp_path / ".tasks.json").read_text()
        data = json.loads(raw)  # Must not raise
        assert "active_tasks" in data
        assert "queues" in data
        assert data["active_tasks"]["/tmp/proj"]["idea"] == "test idea"
        assert data["queues"]["/tmp/proj"][0]["idea"] == "queue idea"

    def test_save_survives_os_replace_failure(self, ptm):
        """When os.replace fails (e.g., permission error), save logs warning but doesn't crash."""
        ptm.active_tasks["/tmp/proj"] = self._make_task()

        import os as _os
        with patch("src.telegram_bot.tasks.os.replace", side_effect=OSError("Permission denied")):
            ptm._save_tasks()  # Should not raise

    def test_queue_lock_not_held_during_file_write(self, ptm):
        """_save_tasks releases _queue_lock before file I/O to prevent deadlocks.

        The lock is only held during queue dict serialization, not during
        the tmp file write + os.replace operation.
        """
        ptm.queues["/tmp/proj"] = [self._make_queued()]

        original_write = Path.write_text
        lock_held_during_write = []

        def spy_write(self_path, content, *args, **kwargs):
            # Check if lock is held (non-blocking acquire returns False if held)
            acquired = ptm._queue_lock.acquire(blocking=False)
            if acquired:
                ptm._queue_lock.release()
                lock_held_during_write.append(False)
            else:
                lock_held_during_write.append(True)
            return original_write(self_path, content, *args, **kwargs)

        with patch.object(Path, "write_text", spy_write):
            ptm._save_tasks()

        # Lock should NOT be held during file write
        assert lock_held_during_write and not any(lock_held_during_write)

    def test_load_restores_queued_at_timestamps(self, tmp_path):
        """Load preserves queued_at timestamps through round-trip serialization."""
        from src.telegram_bot.tasks import QueuedTask

        with patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)):
            from src.telegram_bot.tasks import TaskManager
            tm = TaskManager()

            qt = QueuedTask(
                id="q1",
                project="proj",
                project_path=Path("/tmp/proj"),
                mode="plan",
                iterations=3,
                idea=None,
                queued_at=datetime(2026, 1, 15, 10, 30, 0),
            )
            tm.queues["/tmp/proj"] = [qt]
            tm._save_tasks()

            tm2 = TaskManager.__new__(TaskManager)
            tm2.active_tasks = {}
            tm2.queues = {}
            tm2._queue_lock = __import__("threading").Lock()
            tm2._load_tasks()

        restored = tm2.queues["/tmp/proj"][0]
        assert restored.queued_at == datetime(2026, 1, 15, 10, 30, 0)

    def test_load_restores_started_at_and_fields(self, tmp_path):
        """Load preserves started_at, last_reported_iteration, and stale_warned."""
        from src.telegram_bot.tasks import Task

        with patch("src.telegram_bot.tasks.PROJECTS_ROOT", str(tmp_path)):
            from src.telegram_bot.tasks import TaskManager
            tm = TaskManager()

            task = Task(
                project="proj",
                project_path=Path("/tmp/proj"),
                mode="build",
                iterations=5,
                idea=None,
                session_name="loop-proj",
                last_reported_iteration=3,
                stale_warned=True,
                started_at=datetime(2026, 1, 15, 14, 0, 0),
                status="running",
            )
            tm.active_tasks["/tmp/proj"] = task
            tm._save_tasks()

            tm2 = TaskManager.__new__(TaskManager)
            tm2.active_tasks = {}
            tm2.queues = {}
            tm2._queue_lock = __import__("threading").Lock()
            with patch.object(tm2, "_is_session_running", return_value=True):
                tm2._load_tasks()

        restored = tm2.active_tasks["/tmp/proj"]
        assert restored.last_reported_iteration == 3
        assert restored.stale_warned is True
        assert restored.started_at == datetime(2026, 1, 15, 14, 0, 0)
        assert restored.status == "running"

    def test_save_multiple_projects_independent(self, ptm):
        """Multiple projects are saved and loaded independently."""
        ptm.active_tasks["/tmp/projA"] = self._make_task(project="projA", session_name="loop-projA")
        ptm.active_tasks["/tmp/projB"] = self._make_task(project="projB", session_name="loop-projB")
        ptm.queues["/tmp/projA"] = [self._make_queued(id="qA", project="projA")]
        ptm.queues["/tmp/projB"] = [
            self._make_queued(id="qB1", project="projB"),
            self._make_queued(id="qB2", project="projB"),
        ]
        ptm._save_tasks()

        data = json.loads((ptm._tmp_path / ".tasks.json").read_text())
        assert len(data["active_tasks"]) == 2
        assert len(data["queues"]["/tmp/projA"]) == 1
        assert len(data["queues"]["/tmp/projB"]) == 2


class TestBrainstormManagerFinish:
    """Tests for BrainstormManager.finish() — session lookup, tmux cleanup,
    ROADMAP.md writing, _cleanup_session() call, return (success, message, content) tuple.

    finish() is an async method that:
    1. Looks up session by chat_id
    2. Validates session_id exists (session ready)
    3. Starts Claude in tmux with MSG_SUMMARY_PROMPT (--resume)
    4. Waits for Claude response
    5. Writes response to docs/ROADMAP.md
    6. Cleans up session
    7. Returns (True, MSG_IDEA_SAVED, idea_content) on success
    """

    def _setup_active_session(self, brainstorm_manager, tmp_path):
        """Create an active brainstorm session ready for finish()."""
        from src.telegram_bot.tasks import BrainstormSession

        project_path = tmp_path / "myproject"
        project_path.mkdir(exist_ok=True)

        session = BrainstormSession(
            chat_id=42,
            project="myproject",
            project_path=project_path,
            session_id="sess-finish-123",
            tmux_session="brainstorm-42",
            output_file=Path(str(tmp_path) + "/.brainstorm/old_output.jsonl"),
            initial_prompt="original prompt",
        )
        session.status = "ready"
        session.last_response = "previous response"
        brainstorm_manager.sessions[42] = session
        return session

    @pytest.mark.asyncio
    async def test_no_session_returns_error(self, brainstorm_manager):
        """finish() returns (False, MSG_NO_ACTIVE_BRAINSTORM, None) when no session exists."""
        success, message, content = await brainstorm_manager.finish(999)

        assert success is False
        assert message == MSG_NO_ACTIVE_BRAINSTORM
        assert content is None

    @pytest.mark.asyncio
    async def test_no_session_id_cleans_up_and_returns_error(self, brainstorm_manager, tmp_path):
        """finish() cleans up and returns error when session has no session_id (not ready)."""
        session = self._setup_active_session(brainstorm_manager, tmp_path)
        session.session_id = None  # Not ready yet

        with patch.object(brainstorm_manager, "_cleanup_session") as mock_cleanup:
            success, message, content = await brainstorm_manager.finish(42)

        assert success is False
        assert message == MSG_SESSION_NOT_READY
        assert content is None
        mock_cleanup.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_tmux_start_failure_cleans_up(self, brainstorm_manager, tmp_path):
        """finish() cleans up and returns error when Claude tmux start fails."""
        self._setup_active_session(brainstorm_manager, tmp_path)

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=False),
            patch.object(brainstorm_manager, "_cleanup_session") as mock_cleanup,
        ):
            success, message, content = await brainstorm_manager.finish(42)

        assert success is False
        assert message == MSG_FAILED_TO_START_CLAUDE
        assert content is None
        mock_cleanup.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_tmux_start_uses_resume_and_summary_prompt(self, brainstorm_manager, tmp_path):
        """finish() starts Claude with MSG_SUMMARY_PROMPT and --resume using session_id."""
        session = self._setup_active_session(brainstorm_manager, tmp_path)

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True) as mock_start,
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "# Roadmap\n\nA cool project", "sess-new"),
            ),
            patch.object(brainstorm_manager, "_cleanup_session"),
        ):
            await brainstorm_manager.finish(42)

        mock_start.assert_called_once()
        call_args = mock_start.call_args
        # Verify resume_session_id is passed
        assert call_args.kwargs.get("resume_session_id") == "sess-finish-123"
        # Verify MSG_SUMMARY_PROMPT is used as the prompt
        assert call_args.args[2] == MSG_SUMMARY_PROMPT
        # Verify project_path matches session
        assert call_args.args[1] == session.project_path

    @pytest.mark.asyncio
    async def test_wait_error_cleans_up(self, brainstorm_manager, tmp_path):
        """finish() cleans up and returns error when _wait_for_response returns an error."""
        self._setup_active_session(brainstorm_manager, tmp_path)

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(ERR_TIMEOUT, MSG_TIMEOUT_WAITING, None),
            ),
            patch.object(brainstorm_manager, "_cleanup_session") as mock_cleanup,
        ):
            success, message, content = await brainstorm_manager.finish(42)

        assert success is False
        assert message == MSG_TIMEOUT_WAITING
        assert content is None
        mock_cleanup.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_wait_no_result_error(self, brainstorm_manager, tmp_path):
        """finish() returns error when Claude ends without result."""
        self._setup_active_session(brainstorm_manager, tmp_path)

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(ERR_NO_RESULT, "Claude ended without response", None),
            ),
            patch.object(brainstorm_manager, "_cleanup_session") as mock_cleanup,
        ):
            success, message, content = await brainstorm_manager.finish(42)

        assert success is False
        assert message == "Claude ended without response"
        assert content is None
        mock_cleanup.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_success_writes_roadmap_file(self, brainstorm_manager, tmp_path):
        """finish() writes Claude's response to docs/ROADMAP.md in the project directory."""
        self._setup_active_session(brainstorm_manager, tmp_path)
        idea_text = "# Roadmap\n\nBuild a distributed cache layer"

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, idea_text, "sess-new"),
            ),
            patch.object(brainstorm_manager, "_cleanup_session"),
        ):
            success, message, content = await brainstorm_manager.finish(42)

        assert success is True
        roadmap = tmp_path / "myproject" / "docs" / "ROADMAP.md"
        assert roadmap.exists()
        assert roadmap.read_text() == idea_text

    @pytest.mark.asyncio
    async def test_success_creates_docs_dir(self, brainstorm_manager, tmp_path):
        """finish() creates docs/ directory if it doesn't exist."""
        self._setup_active_session(brainstorm_manager, tmp_path)

        docs_dir = tmp_path / "myproject" / "docs"
        assert not docs_dir.exists()

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "some content", "sess-new"),
            ),
            patch.object(brainstorm_manager, "_cleanup_session"),
        ):
            await brainstorm_manager.finish(42)

        assert docs_dir.exists()

    @pytest.mark.asyncio
    async def test_success_return_tuple_format(self, brainstorm_manager, tmp_path):
        """finish() returns (True, MSG_IDEA_SAVED with path, idea_content) on success."""
        session = self._setup_active_session(brainstorm_manager, tmp_path)
        idea_text = "# Roadmap\n\nAmazing project"

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, idea_text, "sess-new"),
            ),
            patch.object(brainstorm_manager, "_cleanup_session"),
        ):
            success, message, content = await brainstorm_manager.finish(42)

        assert success is True
        expected_path = session.project_path / "docs" / "ROADMAP.md"
        assert message == MSG_IDEA_SAVED.format(path=expected_path)
        assert content == idea_text

    @pytest.mark.asyncio
    async def test_success_calls_cleanup_session(self, brainstorm_manager, tmp_path):
        """finish() calls _cleanup_session after writing ROADMAP.md on success."""
        self._setup_active_session(brainstorm_manager, tmp_path)

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "idea content", "sess-new"),
            ),
            patch.object(brainstorm_manager, "_cleanup_session") as mock_cleanup,
        ):
            await brainstorm_manager.finish(42)

        mock_cleanup.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_session_removed_after_finish(self, brainstorm_manager, tmp_path):
        """finish() removes session from sessions dict (via real _cleanup_session)."""
        self._setup_active_session(brainstorm_manager, tmp_path)
        assert 42 in brainstorm_manager.sessions

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "idea content", "sess-new"),
            ),
            patch.object(brainstorm_manager, "_is_session_running", return_value=False),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            await brainstorm_manager.finish(42)

        # Session should be removed by _cleanup_session
        assert 42 not in brainstorm_manager.sessions

    @pytest.mark.asyncio
    async def test_cleanup_session_called_on_every_path(self, brainstorm_manager, tmp_path):
        """_cleanup_session is called on all failure paths except no-session."""
        # Path 1: no session_id — cleanup called
        session = self._setup_active_session(brainstorm_manager, tmp_path)
        session.session_id = None
        with patch.object(brainstorm_manager, "_cleanup_session") as mock_cleanup:
            await brainstorm_manager.finish(42)
        mock_cleanup.assert_called_once_with(42)

        # Path 2: tmux start failure — cleanup called
        self._setup_active_session(brainstorm_manager, tmp_path)
        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=False),
            patch.object(brainstorm_manager, "_cleanup_session") as mock_cleanup,
        ):
            await brainstorm_manager.finish(42)
        mock_cleanup.assert_called_once_with(42)

        # Path 3: wait error — cleanup called
        self._setup_active_session(brainstorm_manager, tmp_path)
        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(ERR_TIMEOUT, MSG_TIMEOUT_WAITING, None),
            ),
            patch.object(brainstorm_manager, "_cleanup_session") as mock_cleanup,
        ):
            await brainstorm_manager.finish(42)
        mock_cleanup.assert_called_once_with(42)


class TestBrainstormHistory:
    """Tests for brainstorm session history archiving and retrieval."""

    def test_archive_session_creates_history_file(self, brainstorm_manager, tmp_path):
        """_archive_session() creates .brainstorm_history.json with entry."""
        from src.telegram_bot.tasks import BrainstormSession
        session = BrainstormSession(
            chat_id=42,
            project="myproject",
            project_path=tmp_path / "myproject",
            session_id="sess-1",
            tmux_session="brainstorm-42",
            output_file=tmp_path / ".brainstorm" / "out.jsonl",
            initial_prompt="Build a REST API",
            last_response="Here is the plan...",
        )
        brainstorm_manager._archive_session(session, "saved")

        history_file = tmp_path / ".brainstorm_history.json"
        assert history_file.exists()
        history = json.loads(history_file.read_text())
        assert len(history) == 1
        assert history[0]["project"] == "myproject"
        assert history[0]["topic"] == "Build a REST API"
        assert history[0]["outcome"] == "saved"
        assert history[0]["last_response"] == "Here is the plan..."

    def test_archive_session_appends_to_existing_history(self, brainstorm_manager, tmp_path):
        """_archive_session() appends to existing history, not overwrites."""
        from src.telegram_bot.tasks import BrainstormSession
        # Pre-populate history
        history_file = tmp_path / ".brainstorm_history.json"
        history_file.write_text(json.dumps([{"project": "old", "topic": "old topic"}]))

        session = BrainstormSession(
            chat_id=42,
            project="newproj",
            project_path=tmp_path / "newproj",
            session_id="sess-2",
            tmux_session="brainstorm-42",
            output_file=tmp_path / ".brainstorm" / "out.jsonl",
            initial_prompt="New idea",
        )
        brainstorm_manager._archive_session(session, "cancelled")

        history = json.loads(history_file.read_text())
        assert len(history) == 2
        assert history[0]["project"] == "old"
        assert history[1]["project"] == "newproj"
        assert history[1]["outcome"] == "cancelled"

    def test_archive_session_truncates_long_topic(self, brainstorm_manager, tmp_path):
        """_archive_session() truncates initial_prompt to 100 chars + ellipsis."""
        from src.telegram_bot.tasks import BrainstormSession
        long_prompt = "A" * 200
        session = BrainstormSession(
            chat_id=42,
            project="proj",
            project_path=tmp_path / "proj",
            session_id="sess-1",
            tmux_session="brainstorm-42",
            output_file=tmp_path / ".brainstorm" / "out.jsonl",
            initial_prompt=long_prompt,
        )
        brainstorm_manager._archive_session(session, "saved")

        history = json.loads((tmp_path / ".brainstorm_history.json").read_text())
        assert history[0]["topic"] == "A" * 100 + "..."

    def test_archive_session_truncates_long_response(self, brainstorm_manager, tmp_path):
        """_archive_session() truncates last_response to 500 chars."""
        from src.telegram_bot.tasks import BrainstormSession
        session = BrainstormSession(
            chat_id=42,
            project="proj",
            project_path=tmp_path / "proj",
            session_id="sess-1",
            tmux_session="brainstorm-42",
            output_file=tmp_path / ".brainstorm" / "out.jsonl",
            initial_prompt="topic",
            last_response="R" * 1000,
        )
        brainstorm_manager._archive_session(session, "saved")

        history = json.loads((tmp_path / ".brainstorm_history.json").read_text())
        assert len(history[0]["last_response"]) == 500

    def test_load_history_empty_when_no_file(self, brainstorm_manager):
        """_load_history() returns empty list when file doesn't exist."""
        assert brainstorm_manager._load_history() == []

    def test_load_history_corrupt_file(self, brainstorm_manager, tmp_path):
        """_load_history() returns empty list on corrupt JSON."""
        (tmp_path / ".brainstorm_history.json").write_text("not json{{{")
        assert brainstorm_manager._load_history() == []

    def test_save_history_atomic_write(self, brainstorm_manager, tmp_path):
        """_save_history() uses atomic write (no .tmp file left over)."""
        brainstorm_manager._save_history([{"project": "test"}])
        assert (tmp_path / ".brainstorm_history.json").exists()
        assert not (tmp_path / ".brainstorm_history.tmp").exists()

    def test_list_brainstorm_history_empty(self, brainstorm_manager):
        """list_brainstorm_history() returns empty list when no history."""
        assert brainstorm_manager.list_brainstorm_history() == []

    def test_list_brainstorm_history_sorted_newest_first(self, brainstorm_manager, tmp_path):
        """list_brainstorm_history() returns entries sorted by finished_at descending."""
        history = [
            {"project": "a", "finished_at": "2026-01-01T10:00:00"},
            {"project": "b", "finished_at": "2026-02-01T10:00:00"},
            {"project": "c", "finished_at": "2026-01-15T10:00:00"},
        ]
        (tmp_path / ".brainstorm_history.json").write_text(json.dumps(history))

        result = brainstorm_manager.list_brainstorm_history()
        assert [e["project"] for e in result] == ["b", "c", "a"]

    def test_list_brainstorm_history_filter_by_project(self, brainstorm_manager, tmp_path):
        """list_brainstorm_history(project=...) filters by project name."""
        history = [
            {"project": "alpha", "finished_at": "2026-01-01T10:00:00"},
            {"project": "beta", "finished_at": "2026-02-01T10:00:00"},
            {"project": "alpha", "finished_at": "2026-01-15T10:00:00"},
        ]
        (tmp_path / ".brainstorm_history.json").write_text(json.dumps(history))

        result = brainstorm_manager.list_brainstorm_history(project="alpha")
        assert len(result) == 2
        assert all(e["project"] == "alpha" for e in result)

    def test_cancel_archives_session(self, brainstorm_manager, tmp_path):
        """cancel() archives session with 'cancelled' outcome before cleanup."""
        from src.telegram_bot.tasks import BrainstormSession
        session = BrainstormSession(
            chat_id=99,
            project="proj",
            project_path=tmp_path / "proj",
            session_id="sess-1",
            tmux_session="brainstorm-99",
            output_file=tmp_path / ".brainstorm" / "out.jsonl",
            initial_prompt="Some idea",
            last_response="Claude said something",
        )
        brainstorm_manager.sessions[99] = session

        with (
            patch.object(brainstorm_manager, "_is_session_running", return_value=False),
            patch.object(brainstorm_manager, "_save_sessions"),
        ):
            brainstorm_manager.cancel(99)

        history = brainstorm_manager._load_history()
        assert len(history) == 1
        assert history[0]["outcome"] == "cancelled"
        assert history[0]["project"] == "proj"

    @pytest.mark.asyncio
    async def test_finish_archives_session_on_success(self, brainstorm_manager, tmp_path):
        """finish() archives session with 'saved' outcome on success."""
        from src.telegram_bot.tasks import BrainstormSession
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        session = BrainstormSession(
            chat_id=42,
            project="myproject",
            project_path=project_dir,
            session_id="sess-finish",
            tmux_session="brainstorm-42",
            output_file=tmp_path / ".brainstorm" / "out.jsonl",
            initial_prompt="Build something",
            last_response="Previous response",
        )
        brainstorm_manager.sessions[42] = session

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "# Idea\n\nGreat project", "sess-new"),
            ),
            patch.object(brainstorm_manager, "_cleanup_session"),
        ):
            success, _, _ = await brainstorm_manager.finish(42)

        assert success is True
        history = brainstorm_manager._load_history()
        assert len(history) == 1
        assert history[0]["outcome"] == "saved"
        assert history[0]["project"] == "myproject"

    def test_cancel_nonexistent_does_not_archive(self, brainstorm_manager, tmp_path):
        """cancel() on nonexistent session doesn't create history entry."""
        brainstorm_manager.cancel(999)
        assert brainstorm_manager._load_history() == []

    def test_archive_session_stores_conversation(self, brainstorm_manager, tmp_path):
        """_archive_session() stores the full conversation list in history."""
        from src.telegram_bot.tasks import BrainstormSession
        conversation = [
            {"role": "user", "text": "Build a REST API"},
            {"role": "assistant", "text": "Here is the plan..."},
            {"role": "user", "text": "Add auth"},
            {"role": "assistant", "text": "Sure, here's auth..."},
        ]
        session = BrainstormSession(
            chat_id=42,
            project="myproject",
            project_path=tmp_path / "myproject",
            session_id="sess-1",
            tmux_session="brainstorm-42",
            output_file=tmp_path / ".brainstorm" / "out.jsonl",
            initial_prompt="Build a REST API",
            last_response="Sure, here's auth...",
            conversation=conversation,
        )
        brainstorm_manager._archive_session(session, "saved")

        history = json.loads((tmp_path / ".brainstorm_history.json").read_text())
        assert history[0]["conversation"] == conversation
        assert history[0]["session_id"] == "sess-1"
        assert history[0]["turns"] == 2  # 4 entries / 2 = 2 turns

    def test_archive_session_counts_turns_from_conversation(self, brainstorm_manager, tmp_path):
        """_archive_session() counts turns from conversation pairs, not response splitting."""
        from src.telegram_bot.tasks import BrainstormSession
        session = BrainstormSession(
            chat_id=42,
            project="proj",
            project_path=tmp_path / "proj",
            session_id="sess-1",
            tmux_session="brainstorm-42",
            output_file=tmp_path / ".brainstorm" / "out.jsonl",
            initial_prompt="topic",
            conversation=[
                {"role": "user", "text": "q1"},
                {"role": "assistant", "text": "a1"},
                {"role": "user", "text": "q2"},
                {"role": "assistant", "text": "a2"},
                {"role": "user", "text": "q3"},
                {"role": "assistant", "text": "a3"},
            ],
        )
        brainstorm_manager._archive_session(session, "saved")

        history = json.loads((tmp_path / ".brainstorm_history.json").read_text())
        assert history[0]["turns"] == 3


class TestBrainstormExport:
    """Tests for brainstorm session export to Markdown."""

    def test_export_session_success(self, brainstorm_manager, tmp_path):
        """export_session() creates a Markdown file with conversation data."""
        project_dir = tmp_path / "myproject" / "docs" / "brainstorms"
        history = [{
            "project": "myproject",
            "topic": "Build a REST API",
            "started_at": "2026-02-01T10:00:00",
            "finished_at": "2026-02-01T11:00:00",
            "outcome": "saved",
            "turns": 1,
            "conversation": [
                {"role": "user", "text": "Build a REST API"},
                {"role": "assistant", "text": "Here is the plan..."},
            ],
            "session_id": "sess-1",
        }]
        (tmp_path / ".brainstorm_history.json").write_text(json.dumps(history))

        success, message, path = brainstorm_manager.export_session(0)

        assert success is True
        assert path is not None
        assert path.exists()
        content = path.read_text()
        assert "# Brainstorm: Build a REST API" in content
        assert "**Project:** myproject" in content
        assert "## User" in content
        assert "## Assistant" in content
        assert "Build a REST API" in content
        assert "Here is the plan..." in content

    def test_export_session_invalid_index(self, brainstorm_manager, tmp_path):
        """export_session() returns error for out-of-range index."""
        success, message, path = brainstorm_manager.export_session(0)
        assert success is False
        assert path is None
        assert "not found" in message

    def test_export_session_no_conversation(self, brainstorm_manager, tmp_path):
        """export_session() returns error when entry has no conversation data."""
        history = [{
            "project": "myproject",
            "topic": "Old session",
            "started_at": "2026-01-01T10:00:00",
            "finished_at": "2026-01-01T11:00:00",
            "conversation": [],
        }]
        (tmp_path / ".brainstorm_history.json").write_text(json.dumps(history))

        success, message, path = brainstorm_manager.export_session(0)
        assert success is False
        assert "No conversation data" in message

    def test_export_session_creates_brainstorms_dir(self, brainstorm_manager, tmp_path):
        """export_session() creates docs/brainstorms/ directory if it doesn't exist."""
        history = [{
            "project": "newproj",
            "topic": "New idea",
            "started_at": "2026-02-10T09:00:00",
            "finished_at": "2026-02-10T10:00:00",
            "conversation": [
                {"role": "user", "text": "Hello"},
                {"role": "assistant", "text": "Hi there"},
            ],
        }]
        (tmp_path / ".brainstorm_history.json").write_text(json.dumps(history))

        success, _, path = brainstorm_manager.export_session(0)
        assert success is True
        assert (tmp_path / "newproj" / "docs" / "brainstorms").is_dir()

    def test_export_session_filename_format(self, brainstorm_manager, tmp_path):
        """export_session() uses {project}_{YYYYMMDD_HHMM}.md filename."""
        history = [{
            "project": "myapp",
            "topic": "Feature design",
            "started_at": "2026-03-15T14:30:00",
            "finished_at": "2026-03-15T15:30:00",
            "conversation": [
                {"role": "user", "text": "Design a feature"},
                {"role": "assistant", "text": "OK"},
            ],
        }]
        (tmp_path / ".brainstorm_history.json").write_text(json.dumps(history))

        success, _, path = brainstorm_manager.export_session(0)
        assert success is True
        assert path.name == "myapp_20260315_1430.md"

    def test_export_session_negative_index(self, brainstorm_manager, tmp_path):
        """export_session() returns error for negative index."""
        success, message, path = brainstorm_manager.export_session(-1)
        assert success is False


class TestBrainstormResumable:
    """Tests for finding and resuming archived brainstorm sessions."""

    def test_get_resumable_session_found(self, brainstorm_manager, tmp_path):
        """get_resumable_session() returns most recent entry with conversation and session_id."""
        history = [
            {
                "project": "myproject",
                "finished_at": "2026-01-01T10:00:00",
                "conversation": [{"role": "user", "text": "q"}],
                "session_id": "sess-old",
            },
            {
                "project": "myproject",
                "finished_at": "2026-02-01T10:00:00",
                "conversation": [{"role": "user", "text": "q2"}],
                "session_id": "sess-new",
            },
        ]
        (tmp_path / ".brainstorm_history.json").write_text(json.dumps(history))

        result = brainstorm_manager.get_resumable_session("myproject")
        assert result is not None
        assert result["session_id"] == "sess-new"

    def test_get_resumable_session_none_without_conversation(self, brainstorm_manager, tmp_path):
        """get_resumable_session() returns None when entries have no conversation."""
        history = [{
            "project": "myproject",
            "finished_at": "2026-02-01T10:00:00",
            "conversation": [],
            "session_id": "sess-1",
        }]
        (tmp_path / ".brainstorm_history.json").write_text(json.dumps(history))

        assert brainstorm_manager.get_resumable_session("myproject") is None

    def test_get_resumable_session_none_without_session_id(self, brainstorm_manager, tmp_path):
        """get_resumable_session() returns None when entries have no session_id."""
        history = [{
            "project": "myproject",
            "finished_at": "2026-02-01T10:00:00",
            "conversation": [{"role": "user", "text": "q"}],
        }]
        (tmp_path / ".brainstorm_history.json").write_text(json.dumps(history))

        assert brainstorm_manager.get_resumable_session("myproject") is None

    def test_get_resumable_session_filters_by_project(self, brainstorm_manager, tmp_path):
        """get_resumable_session() only returns entries for the specified project."""
        history = [{
            "project": "other-project",
            "finished_at": "2026-02-01T10:00:00",
            "conversation": [{"role": "user", "text": "q"}],
            "session_id": "sess-1",
        }]
        (tmp_path / ".brainstorm_history.json").write_text(json.dumps(history))

        assert brainstorm_manager.get_resumable_session("myproject") is None

    def test_get_resumable_session_empty_history(self, brainstorm_manager):
        """get_resumable_session() returns None with no history."""
        assert brainstorm_manager.get_resumable_session("myproject") is None

    @pytest.mark.asyncio
    async def test_resume_archived_session_happy_path(self, brainstorm_manager, tmp_path):
        """resume_archived_session() creates session and returns Claude response."""
        history_entry = {
            "project": "myproject",
            "topic": "Build API",
            "started_at": "2026-02-01T10:00:00",
            "finished_at": "2026-02-01T11:00:00",
            "conversation": [
                {"role": "user", "text": "Build a REST API"},
                {"role": "assistant", "text": "Here is the plan..."},
            ],
            "session_id": "sess-archived",
        }
        project_path = tmp_path / "myproject"
        project_path.mkdir()

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True) as mock_tmux,
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "Continuing our discussion...", "sess-new"),
            ),
        ):
            results = []
            async for error_code, status, is_final in brainstorm_manager.resume_archived_session(
                chat_id=42,
                project="myproject",
                project_path=project_path,
                history_entry=history_entry,
            ):
                results.append((error_code, status, is_final))

        # Should have 3 tuples: starting, thinking, response
        assert len(results) == 3
        assert results[0] == (None, MSG_BRAINSTORM_STARTING, False)
        assert results[2][0] is None
        assert results[2][1] == "Continuing our discussion..."
        assert results[2][2] is True

        # Verify --resume was used with archived session_id
        mock_tmux.assert_called_once()
        call_kwargs = mock_tmux.call_args
        assert call_kwargs[1]["resume_session_id"] == "sess-archived"

        # Session should be registered
        assert 42 in brainstorm_manager.sessions
        session = brainstorm_manager.sessions[42]
        assert session.session_id == "sess-new"
        assert session.status == "ready"
        # Original conversation should be preserved + new response added
        assert len(session.conversation) == 3  # 2 from archive + 1 new response

    @pytest.mark.asyncio
    async def test_resume_archived_session_active_session_error(self, brainstorm_manager, tmp_path):
        """resume_archived_session() yields error when session already active."""
        from src.telegram_bot.tasks import BrainstormSession
        brainstorm_manager.sessions[42] = BrainstormSession(
            chat_id=42, project="proj", project_path=tmp_path / "proj",
            session_id="s", tmux_session="t", output_file=tmp_path / "f",
            initial_prompt="p",
        )

        results = []
        async for item in brainstorm_manager.resume_archived_session(
            42, "proj", tmp_path / "proj", {"session_id": "s"},
        ):
            results.append(item)

        assert len(results) == 1
        assert results[0][0] == ERR_SESSION_ACTIVE

    @pytest.mark.asyncio
    async def test_resume_archived_session_no_session_id(self, brainstorm_manager, tmp_path):
        """resume_archived_session() yields error when history has no session_id."""
        results = []
        async for item in brainstorm_manager.resume_archived_session(
            42, "proj", tmp_path / "proj", {"conversation": []},
        ):
            results.append(item)

        assert len(results) == 1
        assert results[0][0] == ERR_NOT_READY

    @pytest.mark.asyncio
    async def test_resume_archived_session_tmux_failure(self, brainstorm_manager, tmp_path):
        """resume_archived_session() cleans up and yields error on tmux failure."""
        history_entry = {
            "conversation": [{"role": "user", "text": "q"}],
            "session_id": "sess-1",
            "topic": "topic",
        }

        with patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=False):
            results = []
            async for item in brainstorm_manager.resume_archived_session(
                42, "proj", tmp_path / "proj", history_entry,
            ):
                results.append(item)

        assert results[-1][0] == ERR_START_FAILED
        assert 42 not in brainstorm_manager.sessions  # cleaned up

    @pytest.mark.asyncio
    async def test_resume_archived_session_timeout(self, brainstorm_manager, tmp_path):
        """resume_archived_session() cleans up on timeout."""
        history_entry = {
            "conversation": [{"role": "user", "text": "q"}],
            "session_id": "sess-1",
            "topic": "topic",
        }

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(ERR_TIMEOUT, "Timeout", None),
            ),
        ):
            results = []
            async for item in brainstorm_manager.resume_archived_session(
                42, "proj", tmp_path / "proj", history_entry,
            ):
                results.append(item)

        assert results[-1][0] == ERR_TIMEOUT
        assert 42 not in brainstorm_manager.sessions


class TestBrainstormConversationAccumulation:
    """Tests for conversation accumulation during start() and respond()."""

    @pytest.mark.asyncio
    async def test_start_accumulates_conversation(self, brainstorm_manager, tmp_path):
        """start() adds user prompt and assistant response to conversation list."""
        project_path = tmp_path / "proj"
        project_path.mkdir()

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "Claude's response", "sess-1"),
            ),
        ):
            async for _ in brainstorm_manager.start(42, "proj", project_path, "My prompt"):
                pass

        session = brainstorm_manager.sessions[42]
        assert len(session.conversation) == 2
        assert session.conversation[0] == {"role": "user", "text": "My prompt"}
        assert session.conversation[1] == {"role": "assistant", "text": "Claude's response"}

    @pytest.mark.asyncio
    async def test_respond_accumulates_conversation(self, brainstorm_manager, tmp_path):
        """respond() adds user message and assistant response to conversation."""
        from src.telegram_bot.tasks import BrainstormSession
        session = BrainstormSession(
            chat_id=42, project="proj", project_path=tmp_path / "proj",
            session_id="sess-1", tmux_session="brainstorm-42",
            output_file=tmp_path / ".brainstorm" / "out.jsonl",
            initial_prompt="original", status="ready",
            conversation=[
                {"role": "user", "text": "original"},
                {"role": "assistant", "text": "first response"},
            ],
        )
        brainstorm_manager.sessions[42] = session

        with (
            patch.object(brainstorm_manager, "_start_claude_in_tmux", return_value=True),
            patch.object(
                brainstorm_manager,
                "_wait_for_response",
                return_value=(None, "Second response", "sess-2"),
            ),
        ):
            async for _ in brainstorm_manager.respond(42, "Follow-up question"):
                pass

        assert len(session.conversation) == 4
        assert session.conversation[2] == {"role": "user", "text": "Follow-up question"}
        assert session.conversation[3] == {"role": "assistant", "text": "Second response"}


class TestTaskHistory:
    """Tests for TaskManager task history archival and retrieval."""

    def _make_task(self, tmp_path, project="myproject", mode="build", iterations=5):
        """Helper to create a Task instance for testing."""
        from src.telegram_bot.tasks import Task

        return Task(
            project=project,
            project_path=tmp_path / project,
            mode=mode,
            iterations=iterations,
            idea=None,
            session_name=f"loop-{project}",
            started_at=datetime(2026, 2, 10, 10, 0, 0),
        )

    def test_archive_creates_history_file(self, task_manager, tmp_path):
        """_archive_completed_task() creates .task_history.json with entry."""
        task = self._make_task(tmp_path)
        # Create progress file so get_current_iteration works
        log_dir = tmp_path / "myproject" / "loop" / "logs"
        log_dir.mkdir(parents=True)
        (log_dir / ".progress").write_text("5")

        task_manager._archive_completed_task(task)

        history_file = tmp_path / ".task_history.json"
        assert history_file.exists()
        history = json.loads(history_file.read_text())
        assert len(history) == 1
        assert history[0]["project"] == "myproject"
        assert history[0]["mode"] == "build"
        assert history[0]["iterations_completed"] == 5
        assert history[0]["iterations_total"] == 5
        assert history[0]["status"] == "success"
        assert "log_dir" in history[0]

    def test_archive_appends_to_existing(self, task_manager, tmp_path):
        """_archive_completed_task() appends, not overwrites."""
        history_file = tmp_path / ".task_history.json"
        history_file.write_text(json.dumps([{"project": "old"}]))

        task = self._make_task(tmp_path, project="newproj")
        task_manager._archive_completed_task(task)

        history = json.loads(history_file.read_text())
        assert len(history) == 2
        assert history[0]["project"] == "old"
        assert history[1]["project"] == "newproj"

    def test_archive_partial_iterations_is_fail(self, task_manager, tmp_path):
        """Task with fewer iterations completed than total gets status 'fail'."""
        task = self._make_task(tmp_path, iterations=10)
        log_dir = tmp_path / "myproject" / "loop" / "logs"
        log_dir.mkdir(parents=True)
        (log_dir / ".progress").write_text("3")

        task_manager._archive_completed_task(task)

        history = task_manager._load_task_history()
        assert history[0]["status"] == "fail"
        assert history[0]["iterations_completed"] == 3
        assert history[0]["iterations_total"] == 10

    def test_archive_no_progress_file_uses_total(self, task_manager, tmp_path):
        """Without progress file, iterations_completed falls back to iterations_total."""
        task = self._make_task(tmp_path, iterations=5)
        # No progress file created

        task_manager._archive_completed_task(task)

        history = task_manager._load_task_history()
        assert history[0]["iterations_completed"] == 5
        assert history[0]["status"] == "success"

    def test_list_task_history_sorted_newest_first(self, task_manager, tmp_path):
        """list_task_history() returns entries sorted by finished_at descending."""
        history = [
            {"project": "a", "finished_at": "2026-01-01T10:00:00"},
            {"project": "b", "finished_at": "2026-02-01T10:00:00"},
            {"project": "c", "finished_at": "2026-01-15T10:00:00"},
        ]
        (tmp_path / ".task_history.json").write_text(json.dumps(history))

        result = task_manager.list_task_history()
        assert [e["project"] for e in result] == ["b", "c", "a"]

    def test_list_task_history_filter_by_project(self, task_manager, tmp_path):
        """list_task_history(project=...) filters by project name."""
        history = [
            {"project": "alpha", "finished_at": "2026-01-01T10:00:00"},
            {"project": "beta", "finished_at": "2026-02-01T10:00:00"},
            {"project": "alpha", "finished_at": "2026-01-15T10:00:00"},
        ]
        (tmp_path / ".task_history.json").write_text(json.dumps(history))

        result = task_manager.list_task_history(project="alpha")
        assert len(result) == 2
        assert all(e["project"] == "alpha" for e in result)

    def test_list_task_history_empty_file(self, task_manager, tmp_path):
        """list_task_history() returns [] when no history file exists."""
        result = task_manager.list_task_history()
        assert result == []

    def test_load_corrupted_history(self, task_manager, tmp_path):
        """_load_task_history() returns [] on corrupted JSON."""
        (tmp_path / ".task_history.json").write_text("not json")
        result = task_manager._load_task_history()
        assert result == []

    def test_get_task_log_summary_no_script(self, task_manager, tmp_path):
        """get_task_log_summary() returns None when summary.js not found."""
        with patch("pathlib.Path.exists", return_value=False):
            result = task_manager.get_task_log_summary(str(tmp_path))
        assert result is None

    def test_get_task_log_summary_success(self, task_manager, tmp_path):
        """get_task_log_summary() returns formatted summary from subprocess."""
        fake_summary = "=== Loop Run Summary ===\nTool Usage: Read: 5"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=fake_summary)
            # Patch Path.exists to return True for the summary script
            with patch("pathlib.Path.exists", return_value=True):
                result = task_manager.get_task_log_summary(str(tmp_path / "logs"))
        assert result == fake_summary

    def test_process_completed_archives_task(self, task_manager, tmp_path):
        """process_completed_tasks() archives task when tmux session ends."""
        from src.telegram_bot.tasks import Task

        project_path = tmp_path / "testproj"
        project_path.mkdir()

        task = Task(
            project="testproj",
            project_path=project_path,
            mode="plan",
            iterations=3,
            idea=None,
            session_name="loop-testproj",
            started_at=datetime(2026, 2, 10, 10, 0, 0),
        )
        task_manager.active_tasks[str(project_path)] = task

        with patch.object(task_manager, "_is_session_running", return_value=False):
            task_manager.process_completed_tasks()

        history = task_manager._load_task_history()
        assert len(history) == 1
        assert history[0]["project"] == "testproj"
        assert history[0]["mode"] == "plan"
