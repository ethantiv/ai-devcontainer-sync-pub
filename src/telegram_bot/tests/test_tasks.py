"""Tests for tasks module — TaskManager queue management, BrainstormManager persistence."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.telegram_bot.messages import ERR_SESSION_ACTIVE, ERR_NO_SESSION, ERR_NOT_READY


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
            results = ptm.process_completed_tasks()

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
            results = ptm.process_completed_tasks()

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
            results = ptm.process_completed_tasks()

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
            results = ptm.process_completed_tasks()

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
            results = ptm.process_completed_tasks()
        assert results == []

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
            results = ptm.process_completed_tasks()

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
            results = ptm.process_completed_tasks()

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
            results = ptm.process_completed_tasks()

        assert len(results) == 2
        projects = {r[0].project for r in results}
        assert projects == {"proj-a", "proj-b"}
        assert len(ptm.active_tasks) == 0

    def test_return_tuple_format(self, ptm):
        """Return value is list of (Task|None, Task|None) tuples."""
        task = self._make_task()
        ptm.active_tasks["/tmp/proj"] = task

        with (
            patch.object(ptm, "_is_session_running", return_value=False),
            patch.object(ptm, "_save_tasks"),
        ):
            results = ptm.process_completed_tasks()

        assert isinstance(results, list)
        assert len(results) == 1
        completed, next_task = results[0]
        from src.telegram_bot.tasks import Task
        assert isinstance(completed, Task)
        assert next_task is None
