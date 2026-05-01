#!/usr/bin/env python3
"""Enhanced macOS menu bar launcher for FRIDAY with status monitoring."""

from __future__ import annotations

import subprocess
from pathlib import Path
import threading
import time

import rumps

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "run_project.sh"
ICON_PATH = ROOT / "resources" / "icons" / "friday_icon.png"


def _run(action: str) -> str:
    """Run an action and return output."""
    try:
        result = subprocess.run(
            [str(RUNNER), action],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() or result.stderr.strip() or "Done"
    except subprocess.TimeoutExpired:
        return "Timeout"
    except Exception as e:
        return f"Error: {e}"


class FridayMenuBar(rumps.App):
    def __init__(self) -> None:
        # Set the icon
        super().__init__(
            name="FRIDAY",
            title="FRIDAY",
            icon=str(ICON_PATH),
            menu=[
                "Start",
                "Stop",
                "Restart",
                "Status",
                "Mode: Docker",
                None,
                "Open UI",
                "Show Logs",
                None,
                "About",
                None,
                "Quit",
            ],
        )
        self.tooltip = "FRIDAY AI Assistant"
        self._mode = "docker"
        self._status = "stopped"
        self._update_status()
        # Start a thread to periodically update status
        self._timer = threading.Timer(5.0, self._update_status_loop)
        self._timer.daemon = True
        self._timer.start()

    def _update_status_loop(self) -> None:
        self._update_status()
        self._timer = threading.Timer(5.0, self._update_status_loop)
        self._timer.daemon = True
        self._timer.start()

    def _update_status(self) -> None:
        try:
            output = _run("status")
            if "running" in output.lower() or "up" in output.lower():
                self._status = "running"
                self.title = "FRIDAY ●"
            else:
                self._status = "stopped"
                self.title = "FRIDAY ○"
        except Exception:
            self._status = "unknown"
            self.title = "FRIDAY ?"

    @rumps.clicked("Start")
    def start(self, _: object) -> None:
        output = _run("start")
        rumps.notification("FRIDAY", "Starting", output[:100])
        self._update_status()

    @rumps.clicked("Stop")
    def stop(self, _: object) -> None:
        output = _run("stop")
        rumps.notification("FRIDAY", "Stopping", output[:100])
        self._update_status()

    @rumps.clicked("Restart")
    def restart(self, _: object) -> None:
        _run("stop")
        _run("start")
        rumps.notification("FRIDAY", "Restarting", "Services restarted.")
        self._update_status()

    @rumps.clicked("Status")
    def status(self, _: object) -> None:
        output = _run("status")
        rumps.alert("FRIDAY Status", message=output[:1200] or "No output")

    @rumps.clicked("Mode: Docker")
    def toggle_mode(self, _: object) -> None:
        self._mode = "local" if self._mode == "docker" else "docker"
        # Update menu title
        for i, item in enumerate(self.menu):
            if item.title == "Mode: Docker" or item.title == "Mode: Local":
                self.menu[i].title = f"Mode: {self._mode.capitalize()}"
                break
        rumps.notification("FRIDAY", f"Mode switched to {self._mode}", f"Will use {self._mode} on next start/restart.")

    @rumps.clicked("Open UI")
    def open_ui(self, _: object) -> None:
        _run("open")
        rumps.notification("FRIDAY", "UI", "Opening http://localhost:3000")

    @rumps.clicked("Show Logs")
    def show_logs(self, _: object) -> None:
        script = f'tell application "Terminal" to do script "cd \\"{ROOT}\\" && ./run_project.sh logs"'
        subprocess.run(["osascript", "-e", script], check=False)
        rumps.notification("FRIDAY", "Logs", "Opening logs in Terminal")

    @rumps.clicked("About")
    def about(self, _: object) -> None:
        about_text = (
            "FRIDAY AI Assistant v0.2.0\n"
            "Enhanced with memory, emotion, cross-app integration & more.\n"
            "© 2026 Friday Project\n"
            "https://github.com/Anmo07/Friday"
        )
        rumps.alert("About FRIDAY", message=about_text)

    @rumps.clicked("Quit")
    def quit_app(self, _: object) -> None:
        # Stop the timer
        self._timer.cancel()
        rumps.quit_application()


if __name__ == "__main__":
    FridayMenuBar().run()