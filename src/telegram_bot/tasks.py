"""Task management for running loop.sh in tmux sessions."""

import asyncio
import json
import logging
import os
import shlex
import subprocess
import threading
import time
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import PROJECTS_ROOT
from .git_utils import get_commit_hash

logger = logging.getLogger(__name__)

# Path to loop.sh — built into the Docker image at /opt/loop/scripts/loop.sh
# Falls back to project-local ./loop/loop.sh for development
LOOP_SCRIPT = Path("/opt/loop/scripts/loop.sh")
if not LOOP_SCRIPT.exists():
    LOOP_SCRIPT = Path("loop/loop.sh")  # relative, resolved per-project in _start_task_now


@dataclass
class Task:
    """Represents a running loop task."""

    project: str
    project_path: Path
    mode: str  # "plan" | "build"
    iterations: int
    idea: str | None
    session_name: str
    start_commit: str | None = None  # HEAD hash at task start for diff calculation
    last_reported_iteration: int = 0  # Last iteration number sent to Telegram
    progress_message_id: int | None = None  # Telegram message ID for progress edits
    stale_warned: bool = False  # Whether stale-progress warning was already sent
    started_at: datetime = field(default_factory=datetime.now)
    status: str = "running"  # "running" | "completed" | "failed"


@dataclass
class BrainstormSession:
    """Represents an active brainstorming session with Claude.

    Stores state for multi-turn conversations using Claude CLI --resume.
    Uses tmux session for non-blocking execution with async polling.
    One session per chat_id, keyed by chat_id in BrainstormManager.
    """

    chat_id: int
    project: str
    project_path: Path
    session_id: str | None  # Claude CLI session_id for --resume (None until first response)
    tmux_session: str  # tmux session name: brainstorm-{chat_id}
    output_file: Path  # JSONL output file for polling
    initial_prompt: str
    started_at: datetime = field(default_factory=datetime.now)
    status: str = "waiting"  # "waiting" | "responding" | "ready" | "error"
    last_response: str = ""


@dataclass
class QueuedTask:
    """Represents a task waiting in queue."""

    id: str
    project: str
    project_path: Path
    mode: str  # "plan" | "build"
    iterations: int
    idea: str | None
    queued_at: datetime = field(default_factory=datetime.now)


MAX_QUEUE_SIZE = 10


class TaskManager:
    """Manages loop tasks running in tmux sessions."""

    def __init__(self) -> None:
        self.active_tasks: dict[str, Task] = {}
        self.queues: dict[str, list[QueuedTask]] = {}
        self._queue_lock = threading.Lock()

    def _session_name(self, project: str) -> str:
        """Generate tmux session name for a project."""
        return f"loop-{project}"

    def _is_session_running(self, session_name: str) -> bool:
        """Check if a tmux session exists."""
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", session_name],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False

    def _get_loop_script(self, project_path: Path) -> str:
        """Get the loop.sh script path for a project."""
        if LOOP_SCRIPT.is_absolute() and LOOP_SCRIPT.exists():
            return str(LOOP_SCRIPT)
        # Fallback to project-local
        local_script = project_path / "loop" / "loop.sh"
        if local_script.exists():
            return str(local_script)
        return str(LOOP_SCRIPT)

    def start_task(
        self,
        project: str,
        project_path: Path,
        mode: str,
        iterations: int,
        idea: str | None = None,
    ) -> tuple[bool, str]:
        """Start a loop task or add to queue if busy.

        Returns:
            (success, message) - success=True means started or queued
        """
        session_name = self._session_name(project)
        path_key = str(project_path)

        # If session running, add to queue instead
        if self._is_session_running(session_name):
            with self._queue_lock:
                queue = self.queues.setdefault(path_key, [])
                if len(queue) >= MAX_QUEUE_SIZE:
                    return False, f"Kolejka pełna ({MAX_QUEUE_SIZE} zadań)"

                queue.append(QueuedTask(
                    id=str(uuid.uuid4())[:8],
                    project=project,
                    project_path=project_path,
                    mode=mode,
                    iterations=iterations,
                    idea=idea,
                ))
            return True, f"Dodano do kolejki #{len(queue)}"

        return self._start_task_now(project, project_path, mode, iterations, idea)

    def _start_task_now(
        self,
        project: str,
        project_path: Path,
        mode: str,
        iterations: int,
        idea: str | None = None,
    ) -> tuple[bool, str]:
        """Actually start a task in tmux session."""
        session_name = self._session_name(project)
        loop_script = self._get_loop_script(project_path)

        # Capture HEAD before task starts for completion diff
        start_commit = get_commit_hash(project_path)

        # Build command
        cmd_parts = [loop_script, "-a", "-i", str(iterations)]
        if mode == "plan":
            cmd_parts.append("-p")
        if idea:
            cmd_parts.extend(["-I", shlex.quote(idea)])

        cmd = " ".join(cmd_parts)
        full_cmd = f"cd {shlex.quote(str(project_path))} && {cmd}"

        # Start tmux session
        result = subprocess.run(
            ["tmux", "new-session", "-d", "-s", session_name, full_cmd],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return False, f"Failed to start: {result.stderr}"

        task = Task(
            project=project,
            project_path=project_path,
            mode=mode,
            iterations=iterations,
            idea=idea,
            session_name=session_name,
            start_commit=start_commit,
        )
        self.active_tasks[str(project_path)] = task

        return True, f"Started {mode} ({iterations} iterations)"

    def check_running(self, project_path: Path) -> bool:
        """Check if a task is running for the given project (read-only, no side effects)."""
        task = self.active_tasks.get(str(project_path))
        if not task:
            return False
        return self._is_session_running(task.session_name)

    def get_task(self, project_path: Path) -> Task | None:
        """Get the active task for a project (read-only)."""
        task = self.active_tasks.get(str(project_path))
        if task and self._is_session_running(task.session_name):
            return task
        return None

    def list_active(self) -> list[Task]:
        """List all active tasks (read-only, no cleanup)."""
        return [
            task for task in self.active_tasks.values()
            if self._is_session_running(task.session_name)
        ]

    def get_task_duration(self, task: Task) -> str:
        """Get human-readable duration of a task."""
        delta = datetime.now() - task.started_at
        minutes = int(delta.total_seconds() // 60)
        seconds = int(delta.total_seconds() % 60)
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def get_current_iteration(self, task: Task) -> int | None:
        """Read current iteration number from progress file."""
        try:
            progress_file = task.project_path / "loop" / "logs" / ".progress"
            return int(progress_file.read_text().strip())
        except (FileNotFoundError, ValueError, OSError):
            return None

    def get_queue(self, project_path: Path) -> list[QueuedTask]:
        """Get queued tasks for a project."""
        return self.queues.get(str(project_path), [])

    def cancel_queued_task(self, project_path: Path, task_id: str) -> bool:
        """Cancel a queued task by id. Returns True if found and removed."""
        path_key = str(project_path)
        with self._queue_lock:
            queue = self.queues.get(path_key, [])
            for i, task in enumerate(queue):
                if task.id == task_id:
                    queue.pop(i)
                    return True
        return False

    def _start_next_in_queue(self, project_path: Path) -> Task | None:
        """Start the next task in queue if available. Returns started Task or None."""
        path_key = str(project_path)

        with self._queue_lock:
            queue = self.queues.get(path_key, [])
            if not queue:
                return None
            next_task = queue.pop(0)

        success, _ = self._start_task_now(
            project=next_task.project,
            project_path=next_task.project_path,
            mode=next_task.mode,
            iterations=next_task.iterations,
            idea=next_task.idea,
        )

        if success:
            return self.active_tasks.get(path_key)

        # Restore task to queue if start failed
        with self._queue_lock:
            self.queues.setdefault(path_key, []).insert(0, next_task)

        return None

    def process_completed_tasks(self) -> list[tuple[Task | None, Task | None]]:
        """Check for completed tasks and start next in queue.

        Returns:
            List of (completed_task, next_started_task) tuples.
            completed_task is None if queue was orphaned (no active task).
        """
        results: list[tuple[Task | None, Task | None]] = []
        logger.debug(
            f"process_completed_tasks: {len(self.active_tasks)} active, "
            f"{sum(len(q) for q in self.queues.values())} queued"
        )

        # 1. Check tracked active tasks
        for path_key in list(self.active_tasks.keys()):
            task = self.active_tasks[path_key]
            if not self._is_session_running(task.session_name):
                logger.info(f"Task completed: {task.project} ({task.mode})")
                completed_task = self.active_tasks.pop(path_key)

                queue_len = len(self.queues.get(path_key, []))
                logger.info(f"Queue for {task.project}: {queue_len} items")

                next_task = self._start_next_in_queue(Path(path_key))
                if next_task:
                    logger.info(f"Started next: {next_task.project} ({next_task.mode})")
                results.append((completed_task, next_task))

        # 2. Check orphaned queues (have items but no active task and no running session)
        with self._queue_lock:
            orphaned_paths = [
                path_key
                for path_key, queue in self.queues.items()
                if queue and path_key not in self.active_tasks
            ]

        for path_key in orphaned_paths:
            with self._queue_lock:
                queue = self.queues.get(path_key, [])
                if not queue:
                    continue
                project = queue[0].project

            session_name = self._session_name(project)
            if not self._is_session_running(session_name):
                next_task = self._start_next_in_queue(Path(path_key))
                if next_task:
                    results.append((None, next_task))

        return results


class BrainstormManager:
    """Manages brainstorming sessions with Claude CLI.

    Uses tmux sessions for non-blocking execution with async polling.
    Claude CLI runs with --resume flag for multi-turn conversations.
    Sessions are keyed by chat_id (one session per Telegram chat).
    """

    # Configuration
    POLL_INTERVAL = 0.5  # seconds between polling
    MAX_WAIT = 300  # 5 minutes max wait for response
    TMP_DIR = Path("/tmp")

    def __init__(self) -> None:
        self.sessions: dict[int, BrainstormSession] = {}
        self._load_sessions()

    def _sessions_file(self) -> Path:
        """Path to persistent sessions file (survives container restarts)."""
        return Path(PROJECTS_ROOT) / ".brainstorm_sessions.json"

    def _save_sessions(self) -> None:
        """Serialize active sessions to JSON for persistence across restarts."""
        data = []
        for session in self.sessions.values():
            data.append({
                "chat_id": session.chat_id,
                "project": session.project,
                "project_path": str(session.project_path),
                "session_id": session.session_id,
                "tmux_session": session.tmux_session,
                "initial_prompt": session.initial_prompt,
                "started_at": session.started_at.isoformat(),
                "status": session.status,
            })
        path = self._sessions_file()
        tmp_path = path.with_suffix(".tmp")
        try:
            tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            os.replace(tmp_path, path)
        except OSError:
            logger.warning("Failed to save brainstorm sessions to %s", path)

    def _load_sessions(self) -> None:
        """Restore sessions from JSON, validating tmux sessions exist."""
        path = self._sessions_file()
        if not path.exists():
            return

        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to load brainstorm sessions from %s", path)
            return

        for entry in data:
            tmux_name = entry.get("tmux_session", "")
            if not self._is_session_running(tmux_name):
                continue

            session = BrainstormSession(
                chat_id=entry["chat_id"],
                project=entry["project"],
                project_path=Path(entry["project_path"]),
                session_id=entry.get("session_id"),
                tmux_session=tmux_name,
                output_file=self._output_file_path(entry["chat_id"]),
                initial_prompt=entry.get("initial_prompt", ""),
                started_at=datetime.fromisoformat(entry["started_at"]),
                status=entry.get("status", "ready"),
            )
            self.sessions[session.chat_id] = session
            logger.info("Restored brainstorm session for chat %d, project %s", session.chat_id, session.project)

        # Save cleaned state (without stale entries)
        self._save_sessions()

    def _tmux_session_name(self, chat_id: int) -> str:
        """Generate tmux session name for a brainstorm session."""
        return f"brainstorm-{chat_id}"

    def _output_file_path(self, chat_id: int) -> Path:
        """Generate unique output file path for a session."""
        return self.TMP_DIR / f"brainstorm_{chat_id}_{uuid.uuid4().hex[:8]}.jsonl"

    def _is_session_running(self, tmux_name: str) -> bool:
        """Check if a tmux session exists."""
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", tmux_name],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False

    def _start_claude_in_tmux(
        self,
        tmux_name: str,
        project_path: Path,
        prompt: str,
        output_file: Path,
        resume_session_id: str | None = None,
    ) -> bool:
        """Start Claude CLI in a tmux session.

        Returns:
            True if tmux session started successfully.
        """
        cmd_parts = ["claude", "-p", "--verbose", "--output-format", "stream-json"]
        if resume_session_id:
            cmd_parts.extend(["--resume", resume_session_id])
        cmd_parts.append(shlex.quote(prompt))

        full_cmd = f"cd {shlex.quote(str(project_path))} && {' '.join(cmd_parts)} > {output_file} 2>&1"

        result = subprocess.run(
            ["tmux", "new-session", "-d", "-s", tmux_name, "bash", "-c", full_cmd],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def _cleanup_session(self, chat_id: int) -> None:
        """Clean up session resources (tmux, temp files) and persist state."""
        session = self.sessions.pop(chat_id, None)
        if not session:
            return

        if self._is_session_running(session.tmux_session):
            subprocess.run(
                ["tmux", "kill-session", "-t", session.tmux_session],
                capture_output=True,
                timeout=5,
            )

        try:
            session.output_file.unlink(missing_ok=True)
        except OSError:
            pass

        self._save_sessions()

    def _parse_stream_json(self, output_file: Path) -> tuple[bool, str, str | None]:
        """Parse stream-json output file for final result.

        Returns:
            (found_result, response_or_error, session_id)
        """
        if not output_file.exists():
            return False, "", None

        content = output_file.read_text().strip()
        if not content:
            return False, "", None

        for line in reversed(content.split("\n")):
            if not line.strip():
                continue
            try:
                msg: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                continue

            if msg.get("type") == "result":
                result_text = msg.get("result", "")
                session_id = msg.get("session_id")
                if msg.get("is_error", False):
                    return True, f"Claude error: {result_text}", session_id
                return True, result_text, session_id

        return False, "", None

    async def _wait_for_response(
        self,
        output_file: Path,
        tmux_name: str,
        timeout: float | None = None,
    ) -> tuple[bool, str, str | None]:
        """Wait for Claude CLI to complete and parse response.

        Args:
            output_file: Path to stream-json output file
            tmux_name: Name of tmux session to check
            timeout: Optional timeout in seconds (default: MAX_WAIT)

        Returns:
            (success, response_or_error, session_id)
        """
        timeout = timeout or self.MAX_WAIT
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check if Claude finished (tmux session ended)
            if not self._is_session_running(tmux_name):
                # Parse final result
                found, response, session_id = self._parse_stream_json(output_file)
                if found:
                    return True, response, session_id
                # Session ended but no result found - check for errors
                if output_file.exists():
                    content = output_file.read_text().strip()
                    if content:
                        return False, f"Claude zakończył bez wyniku:\n{content[-500:]}", None
                return False, "Claude zakończył bez odpowiedzi", None

            await asyncio.sleep(self.POLL_INTERVAL)

        return False, "Timeout oczekiwania na odpowiedź Claude", None

    async def start(
        self,
        chat_id: int,
        project: str,
        project_path: Path,
        prompt: str,
    ) -> AsyncGenerator[tuple[str, bool], None]:
        """Start a new brainstorming session.

        Yields:
            (status_message, is_final) tuples for progress updates.
            Final tuple contains Claude's response or error.
        """
        if chat_id in self.sessions:
            yield "Sesja brainstorming już aktywna. Użyj /done lub /cancel.", True
            return

        tmux_name = self._tmux_session_name(chat_id)
        output_file = self._output_file_path(chat_id)

        # Create session record
        session = BrainstormSession(
            chat_id=chat_id,
            project=project,
            project_path=project_path,
            session_id=None,
            tmux_session=tmux_name,
            output_file=output_file,
            initial_prompt=prompt,
            status="waiting",
        )
        self.sessions[chat_id] = session

        yield "Uruchamiam Claude...", False

        # Start Claude in tmux with /brainstorming skill prefix and context
        brainstorm_context = (
            "CONTEXT: This is a Telegram brainstorming session. "
            "DO NOT write code, create files, or make commits. "
            "Focus only on discussion and design exploration. "
            "The user will send /done when ready to save the final IDEA. "
            "Until then, continue the conversation naturally.\n\n"
        )
        brainstorm_prompt = f"/brainstorming {brainstorm_context}{prompt}"
        if not self._start_claude_in_tmux(tmux_name, project_path, brainstorm_prompt, output_file):
            self._cleanup_session(chat_id)
            yield "Nie udało się uruchomić Claude", True
            return

        session.status = "responding"
        yield "Claude myśli...", False

        # Wait for response
        success, response, session_id = await self._wait_for_response(output_file, tmux_name)

        if not success:
            self._cleanup_session(chat_id)
            yield response, True
            return

        # Update session with response
        session.session_id = session_id
        session.last_response = response
        session.status = "ready"
        self._save_sessions()

        yield response, True

    async def respond(
        self,
        chat_id: int,
        message: str,
    ) -> AsyncGenerator[tuple[str, bool], None]:
        """Continue a brainstorming session with user message.

        Yields:
            (status_message, is_final) tuples for progress updates.
        """
        session = self.sessions.get(chat_id)
        if not session:
            yield "Brak aktywnej sesji brainstorming. Użyj /brainstorming <prompt>.", True
            return

        if not session.session_id:
            yield "Sesja brainstorming nie jest gotowa.", True
            return

        # Create new output file for this turn
        output_file = self._output_file_path(chat_id)
        session.output_file = output_file
        session.status = "responding"

        tmux_name = session.tmux_session

        yield "Claude myśli...", False

        # Start Claude with --resume
        if not self._start_claude_in_tmux(
            tmux_name,
            session.project_path,
            message,
            output_file,
            resume_session_id=session.session_id,
        ):
            session.status = "error"
            yield "Nie udało się uruchomić Claude", True
            return

        # Wait for response
        success, response, new_session_id = await self._wait_for_response(output_file, tmux_name)

        if not success:
            session.status = "error"
            yield response, True
            return

        # Update session
        if new_session_id:
            session.session_id = new_session_id
        session.last_response = response
        session.status = "ready"
        self._save_sessions()

        yield response, True

    async def finish(self, chat_id: int) -> tuple[bool, str, str | None]:
        """Finish brainstorming and save result to docs/ROADMAP.md.

        Sends a final prompt to Claude to summarize the brainstorming,
        then writes the result to the project's docs/ROADMAP.md.

        Returns:
            (success, message, idea_content_if_success)
        """
        session = self.sessions.get(chat_id)
        if not session:
            return False, "Brak aktywnej sesji brainstorming.", None

        if not session.session_id:
            self._cleanup_session(chat_id)
            return False, "Sesja brainstorming nie jest gotowa.", None

        # Ask Claude to summarize as IDEA
        summary_prompt = (
            "Podsumuj nasze brainstorming jako specyfikację IDEA. "
            "Format: '# User Idea\\n\\n[opis projektu]'. "
            "Napisz tylko treść IDEA, bez dodatkowego tekstu."
        )

        output_file = self._output_file_path(chat_id)
        tmux_name = session.tmux_session

        if not self._start_claude_in_tmux(
            tmux_name,
            session.project_path,
            summary_prompt,
            output_file,
            resume_session_id=session.session_id,
        ):
            self._cleanup_session(chat_id)
            return False, "Nie udało się uruchomić Claude", None

        success, response, _ = await self._wait_for_response(output_file, tmux_name)

        if not success:
            self._cleanup_session(chat_id)
            return False, response, None

        idea_content = response

        # Write to docs/ROADMAP.md
        docs_dir = session.project_path / "docs"
        docs_dir.mkdir(exist_ok=True)
        idea_file = docs_dir / "ROADMAP.md"
        idea_file.write_text(idea_content)

        # Clean up session
        self._cleanup_session(chat_id)

        return True, f"IDEA zapisana do {idea_file}", idea_content

    def cancel(self, chat_id: int) -> bool:
        """Cancel a brainstorming session without saving.

        Returns:
            True if session was cancelled, False if no session existed.
        """
        if chat_id in self.sessions:
            self._cleanup_session(chat_id)
            return True
        return False


# Global task manager instance
task_manager = TaskManager()

# Global brainstorm manager instance
brainstorm_manager = BrainstormManager()
