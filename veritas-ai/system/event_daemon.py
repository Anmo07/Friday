"""
Friday System — Event-Driven Daemon (Phase 43)
================================================
Background daemon that watches for system-level triggers:
  - System startup registration
  - Scheduled tasks (cron-like)
  - File change watchers

Runs alongside the main Friday loop as an independent async service.
"""

import asyncio
import os
import time
import logging
import threading
from datetime import datetime
from typing import Callable, Optional, List

logger = logging.getLogger("friday.event_daemon")


class ScheduledTask:
    """Represents a recurring task."""
    def __init__(self, name: str, interval_sec: float, callback: Callable):
        self.name = name
        self.interval_sec = interval_sec
        self.callback = callback
        self.last_run: Optional[float] = None

    def is_due(self) -> bool:
        if self.last_run is None:
            return True
        return (time.monotonic() - self.last_run) >= self.interval_sec

    def execute(self):
        try:
            self.callback()
            self.last_run = time.monotonic()
            logger.info(f"⏰ Scheduled task [{self.name}] executed.")
        except Exception as e:
            logger.error(f"Scheduled task [{self.name}] failed: {e}")


class FileWatcher:
    """Watches a directory for changes (new files, modifications)."""
    def __init__(self, path: str, callback: Callable, poll_interval: float = 5.0):
        self.path = os.path.abspath(path)
        self.callback = callback
        self.poll_interval = poll_interval
        self._snapshot: dict = {}
        self._take_snapshot()

    def _take_snapshot(self):
        """Record current state of the directory."""
        self._snapshot = {}
        if not os.path.isdir(self.path):
            return
        for entry in os.scandir(self.path):
            try:
                self._snapshot[entry.path] = entry.stat().st_mtime
            except OSError:
                pass

    def check(self) -> List[dict]:
        """Compare current state against snapshot. Return list of changes."""
        changes = []
        current = {}

        if not os.path.isdir(self.path):
            return changes

        for entry in os.scandir(self.path):
            try:
                current[entry.path] = entry.stat().st_mtime
            except OSError:
                continue

        # New or modified files
        for path, mtime in current.items():
            if path not in self._snapshot:
                changes.append({"type": "created", "path": path})
            elif self._snapshot[path] != mtime:
                changes.append({"type": "modified", "path": path})

        # Deleted files
        for path in self._snapshot:
            if path not in current:
                changes.append({"type": "deleted", "path": path})

        self._snapshot = current

        if changes:
            for change in changes:
                try:
                    self.callback(change)
                except Exception as e:
                    logger.error(f"FileWatcher callback error: {e}")

        return changes


class EventDaemon:
    """
    The main daemon that manages scheduled tasks, file watchers,
    and system event hooks. Runs in a background thread.
    """

    def __init__(self):
        self._scheduled_tasks: List[ScheduledTask] = []
        self._file_watchers: List[FileWatcher] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_scheduled_task(self, name: str, interval_sec: float, callback: Callable):
        """Register a recurring task."""
        task = ScheduledTask(name, interval_sec, callback)
        self._scheduled_tasks.append(task)
        logger.info(f"Registered scheduled task: [{name}] every {interval_sec}s")

    def add_file_watcher(self, path: str, callback: Callable, poll_interval: float = 5.0):
        """Register a directory watcher."""
        watcher = FileWatcher(path, callback, poll_interval)
        self._file_watchers.append(watcher)
        logger.info(f"Registered file watcher: [{path}]")

    def start(self):
        """Start the daemon loop in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("🔄 Friday Event Daemon started.")

    def stop(self):
        """Stop the daemon."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Event Daemon stopped.")

    def _run_loop(self):
        """Core polling loop."""
        while self._running:
            # Check scheduled tasks
            for task in self._scheduled_tasks:
                if task.is_due():
                    task.execute()

            # Check file watchers
            for watcher in self._file_watchers:
                watcher.check()

            time.sleep(1.0)  # 1-second poll interval


# ---------------------------------------------------------------------------
# Predefined system event callbacks
# ---------------------------------------------------------------------------

def on_startup():
    """Called once when the daemon first starts."""
    logger.info("📢 Friday startup event fired.")


def on_file_change(change: dict):
    """Default file change handler."""
    logger.info(f"📁 File change detected: {change['type']} — {change['path']}")


# ---------------------------------------------------------------------------
# Factory: Create a pre-configured daemon
# ---------------------------------------------------------------------------

def create_default_daemon(watch_dir: Optional[str] = None) -> EventDaemon:
    """Build a daemon with sensible defaults for the Friday system."""
    daemon = EventDaemon()

    # Heartbeat every 60 seconds
    daemon.add_scheduled_task("heartbeat", 60.0, lambda: logger.debug("♥ Friday heartbeat"))

    # Watch the project directory for changes if specified
    if watch_dir and os.path.isdir(watch_dir):
        daemon.add_file_watcher(watch_dir, on_file_change)

    return daemon
