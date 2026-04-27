#!/usr/bin/env python3
"""Minimal macOS menu bar launcher for FRIDAY."""

from __future__ import annotations

import subprocess
from pathlib import Path

import rumps


ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "run_project.sh"


def _run(action: str) -> None:
    subprocess.Popen(
        [str(RUNNER), action],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class FridayMenuBar(rumps.App):
    def __init__(self) -> None:
        super().__init__(
            name="FRIDAY",
            title="🤖",
            menu=[
                "Start",
                "Stop",
                "Restart",
                "Status",
                None,
                "Open UI",
                "Show Logs",
                None,
                "Quit",
            ],
        )

    @rumps.clicked("Start")
    def start(self, _: object) -> None:
        _run("start")
        rumps.notification("FRIDAY", "Starting", "Launching local services.")

    @rumps.clicked("Stop")
    def stop(self, _: object) -> None:
        _run("stop")
        rumps.notification("FRIDAY", "Stopping", "Stopping local services.")

    @rumps.clicked("Restart")
    def restart(self, _: object) -> None:
        _run("restart")
        rumps.notification("FRIDAY", "Restarting", "Restarting local services.")

    @rumps.clicked("Status")
    def status(self, _: object) -> None:
        status = subprocess.run(
            [str(RUNNER), "status"],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        output = (status.stdout or status.stderr or "No status output.").strip()
        rumps.alert("FRIDAY Status", message=output[:1200])

    @rumps.clicked("Open UI")
    def open_ui(self, _: object) -> None:
        _run("open")

    @rumps.clicked("Show Logs")
    def show_logs(self, _: object) -> None:
        script = f'tell application "Terminal" to do script "cd \\"{ROOT}\\" && ./run_project.sh logs"'
        subprocess.run(["osascript", "-e", script], check=False)

    @rumps.clicked("Quit")
    def quit_app(self, _: object) -> None:
        rumps.quit_application()


if __name__ == "__main__":
    FridayMenuBar().run()
