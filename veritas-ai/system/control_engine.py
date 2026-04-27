"""OS-level control engine for FRIDAY."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ControlResult:
    success: bool
    action: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    risk_level: str = "low"


class SystemControlEngine:
    """Execute lightweight OS actions with platform-aware fallbacks."""

    def __init__(self) -> None:
        self.platform = platform.system().lower()

    async def execute(self, command: str) -> ControlResult:
        normalized = " ".join(command.strip().split())
        lowered = normalized.lower()

        if not normalized:
            return ControlResult(False, "noop", "No command to run, Boss.")

        if lowered.startswith("confirm ") and len(normalized.split(" ", 1)) == 2:
            confirmed_command = normalized.split(" ", 1)[1].strip()
            result = await self._execute_unsafe(confirmed_command)
            self._write_audit_log(confirmed_command, result)
            return result

        if lowered.startswith("shutdown system") or lowered in {"shutdown", "power off"}:
            return await self.shutdown_system()

        if lowered.startswith(("open ", "launch ", "start ")):
            target = normalized.split(" ", 1)[1].strip()
            if lowered.startswith("start docker"):
                target = "Docker"
            if target.startswith(("http://", "https://")) or "www." in target.lower():
                return await self.open_url(target)
            return await self.open_app(target)

        if lowered.startswith(("close ", "quit ", "stop ")):
            target = normalized.split(" ", 1)[1].strip()
            return await self.close_app(target)

        if lowered.startswith(("run ", "execute ", "terminal ")):
            terminal_cmd = self._extract_terminal_command(normalized)
            risk = self._assess_terminal_risk(terminal_cmd)
            if self._requires_confirmation(risk):
                result = ControlResult(
                    success=False,
                    action="terminal",
                    summary="High-risk command blocked pending confirmation. Say: confirm <command>",
                    details={"command": terminal_cmd, "risk": risk},
                    requires_confirmation=True,
                    risk_level=risk,
                )
                self._write_audit_log(terminal_cmd, result)
                return result
            result = await self.run_terminal_command(terminal_cmd, risk_level=risk)
            self._write_audit_log(terminal_cmd, result)
            return result

        if lowered.startswith(("search file ", "find file ")):
            query = normalized.split(" ", 2)[2].strip()
            result = await self.search_file(query)
            self._write_audit_log(normalized, result)
            return result

        if lowered.startswith(("open browser ", "browse ", "search web for ", "google ")):
            result = await self.browser_search(self._extract_browser_query(normalized))
            self._write_audit_log(normalized, result)
            return result

        result = ControlResult(
            success=False,
            action="unmatched",
            summary="I can handle apps, terminal commands, files, and browser actions, Boss.",
            details={"command": command},
        )
        self._write_audit_log(normalized, result)
        return result

    async def _execute_unsafe(self, command: str) -> ControlResult:
        return await self.run_terminal_command(command, risk_level=self._assess_terminal_risk(command))

    async def open_app(self, app_name: str) -> ControlResult:
        if not app_name:
            return ControlResult(False, "open_app", "Tell me which app to open, Boss.")

        args = self._open_app_args(app_name)
        completed = await self._run_subprocess(args)
        success = completed.returncode == 0
        summary = (
            f"Opening {app_name}, Boss."
            if success
            else f"I couldn’t open {app_name}, Boss."
        )
        return ControlResult(
            success=success,
            action="open_app",
            summary=summary,
            details={"app": app_name, "stderr": completed.stderr.strip()},
        )

    async def close_app(self, app_name: str) -> ControlResult:
        if not app_name:
            return ControlResult(False, "close_app", "Tell me which app to close, Boss.")

        args = self._close_app_args(app_name)
        completed = await self._run_subprocess(args)
        success = completed.returncode == 0
        summary = (
            f"Closing {app_name}, Boss."
            if success
            else f"I couldn’t close {app_name} cleanly, Boss."
        )
        return ControlResult(
            success=success,
            action="close_app",
            summary=summary,
            details={"app": app_name, "stderr": completed.stderr.strip()},
        )

    async def run_terminal_command(self, command: str, *, risk_level: str = "low") -> ControlResult:
        if not command:
            return ControlResult(False, "terminal", "No terminal command to run, Boss.")

        if self._is_destructive_command(command):
            return ControlResult(
                success=False,
                action="terminal",
                summary="That command needs confirmation, Boss.",
                details={"command": command},
                requires_confirmation=True,
                risk_level="high",
            )

        completed = await self._run_subprocess(command, use_shell=True)
        output = completed.stdout.strip() or completed.stderr.strip()
        success = completed.returncode == 0
        summary = "Command finished, Boss." if success else "That command hit a wall, Boss."
        return ControlResult(
            success=success,
            action="terminal",
            summary=summary,
            details={
                "command": command,
                "output": output[:1600],
                "returncode": completed.returncode,
            },
            risk_level=risk_level,
        )

    async def search_file(self, pattern: str, root: str | None = None) -> ControlResult:
        query = pattern.strip()
        if not query:
            return ControlResult(False, "search_file", "Tell me what file to look for, Boss.")

        search_root = root or os.getcwd()
        if shutil.which("rg"):
            command = f"rg --files {shlex.quote(search_root)} | rg -i {shlex.quote(query)}"
        else:
            command = f"find {shlex.quote(search_root)} -type f | grep -i {shlex.quote(query)}"

        completed = await self._run_subprocess(command, use_shell=True)
        matches = [line for line in completed.stdout.splitlines() if line.strip()]
        success = completed.returncode == 0 or bool(matches)
        summary = (
            f"Found {len(matches)} match{'es' if len(matches) != 1 else ''} for {query}, Boss."
            if matches
            else f"No file match for {query}, Boss."
        )
        return ControlResult(
            success=success,
            action="search_file",
            summary=summary,
            details={"pattern": query, "matches": matches[:20]},
        )

    async def open_url(self, url: str) -> ControlResult:
        resolved = url if url.startswith(("http://", "https://")) else f"https://{url}"
        args = self._open_url_args(resolved)
        completed = await self._run_subprocess(args)
        success = completed.returncode == 0
        summary = (
            f"Opening {resolved}, Boss."
            if success
            else f"I couldn’t open that link, Boss."
        )
        return ControlResult(
            success=success,
            action="open_url",
            summary=summary,
            details={"url": resolved, "stderr": completed.stderr.strip()},
        )

    async def browser_search(self, query: str) -> ControlResult:
        if not query:
            return ControlResult(False, "browser_search", "Need something to search for, Boss.")
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        result = await self.open_url(url)
        result.action = "browser_search"
        result.summary = f"Searching the web for {query}, Boss." if result.success else result.summary
        result.details["query"] = query
        return result

    async def shutdown_system(self) -> ControlResult:
        return ControlResult(
            success=False,
            action="shutdown",
            summary="Shutdown is ready, but I’d confirm that one first, Boss.",
            requires_confirmation=True,
        )

    async def _run_subprocess(
        self,
        command: list[str] | str,
        *,
        use_shell: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        logger.debug("Running control command: %s", command)

        def _run() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                command,
                shell=use_shell,
                check=False,
                capture_output=True,
                text=True,
            )

        return await asyncio.to_thread(_run)

    def _extract_terminal_command(self, raw: str) -> str:
        for prefix in ("run terminal command ", "run command ", "run ", "execute ", "terminal "):
            if raw.lower().startswith(prefix):
                return raw[len(prefix):].strip().strip("`")
        return raw

    def _extract_browser_query(self, raw: str) -> str:
        for prefix in ("open browser ", "browse ", "search web for ", "google "):
            if raw.lower().startswith(prefix):
                return raw[len(prefix):].strip()
        return raw

    def _is_destructive_command(self, command: str) -> bool:
        lowered = command.lower()
        destructive_terms = ("rm ", "shutdown", "reboot", "halt", "mkfs", "diskutil erase", "format ")
        return any(term in lowered for term in destructive_terms)

    def _assess_terminal_risk(self, command: str) -> str:
        lowered = command.lower()
        high_risk_terms = (
            "rm -rf",
            "sudo ",
            "mkfs",
            "diskutil erase",
            "dd if=",
            "chmod -r 777",
            "reboot",
            "shutdown",
        )
        medium_risk_terms = ("brew install", "npm install -g", "pip install", "docker system prune")
        if any(term in lowered for term in high_risk_terms):
            return "high"
        if any(term in lowered for term in medium_risk_terms):
            return "medium"
        return "low"

    def _requires_confirmation(self, risk_level: str) -> bool:
        policy = settings.CONTROL_CONFIRMATION_POLICY
        if policy == "confirm_all":
            return True
        if policy == "confirm_high_risk":
            return risk_level == "high"
        if policy == "full_auto":
            return not settings.CONTROL_ALLOW_FULL_AUTO and risk_level == "high"
        return risk_level == "high"

    def _write_audit_log(self, command: str, result: ControlResult) -> None:
        log_path = settings.CONTROL_AUDIT_LOG_PATH
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        record = {
            "command": command,
            "action": result.action,
            "success": result.success,
            "requires_confirmation": result.requires_confirmation,
            "risk_level": result.risk_level,
            "details": result.details,
        }
        try:
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")
        except Exception as exc:
            logger.debug("Failed to write control audit log: %s", exc)

    def _open_app_args(self, app_name: str) -> list[str]:
        if self.platform == "darwin":
            return ["open", "-a", app_name]
        if self.platform == "windows":
            return ["cmd", "/c", "start", "", app_name]
        return ["gtk-launch", app_name] if shutil.which("gtk-launch") else ["xdg-open", app_name]

    def _close_app_args(self, app_name: str) -> list[str]:
        if self.platform == "darwin":
            return ["osascript", "-e", f'tell application "{app_name}" to quit']
        if self.platform == "windows":
            return ["taskkill", "/IM", f"{app_name}.exe", "/F"]
        return ["pkill", "-f", app_name]

    def _open_url_args(self, url: str) -> list[str]:
        if self.platform == "darwin":
            return ["open", url]
        if self.platform == "windows":
            return ["cmd", "/c", "start", "", url]
        return ["xdg-open", url]


control_engine = SystemControlEngine()
