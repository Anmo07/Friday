"""
Friday System — System Control Engine (Phase 38)
==================================================
Provides safe, auditable OS-level operations on macOS:
  - Application management (open/close/focus)
  - Shell command execution
  - File operations (search, move, copy, delete)
  - System settings (volume, brightness, lock, shutdown)
  - Browser control

Every action is logged and passes through the security layer (Phase 41).
"""

import subprocess
import os
import shutil
import glob
import platform
import logging
from typing import Optional

logger = logging.getLogger("friday.control_engine")

# ---------------------------------------------------------------------------
# Security: Command Validation
# ---------------------------------------------------------------------------

DANGEROUS_COMMANDS = {"rm -rf /", "mkfs", "dd if=", ":(){", "fork bomb", "shutdown -h now"}


def _is_safe_command(cmd: str) -> bool:
    """Reject obviously destructive commands."""
    normalized = cmd.lower().strip()
    for danger in DANGEROUS_COMMANDS:
        if danger in normalized:
            logger.warning(f"🛑 BLOCKED dangerous command: {cmd}")
            return False
    return True


# ---------------------------------------------------------------------------
# Application Control (macOS-optimized)
# ---------------------------------------------------------------------------

def open_application(app_name: str) -> dict:
    """Open an application by name using macOS `open -a`."""
    logger.info(f"Opening application: {app_name}")
    try:
        subprocess.run(["open", "-a", app_name], check=True, capture_output=True, text=True)
        return {"status": "success", "action": "open_app", "target": app_name}
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to open {app_name}: {e.stderr}")
        return {"status": "error", "action": "open_app", "message": e.stderr.strip()}


def close_application(app_name: str) -> dict:
    """Close an application gracefully via AppleScript."""
    logger.info(f"Closing application: {app_name}")
    script = f'tell application "{app_name}" to quit'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True)
        return {"status": "success", "action": "close_app", "target": app_name}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "action": "close_app", "message": str(e)}


def focus_application(app_name: str) -> dict:
    """Bring an application to the foreground."""
    script = f'tell application "{app_name}" to activate'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True)
        return {"status": "success", "action": "focus_app", "target": app_name}
    except subprocess.CalledProcessError:
        return {"status": "error", "action": "focus_app", "message": f"Could not focus {app_name}"}


def list_running_apps() -> list:
    """Return a list of currently running applications."""
    script = 'tell application "System Events" to get name of every process whose background only is false'
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if result.returncode == 0:
            apps = [a.strip() for a in result.stdout.split(",")]
            return apps
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Shell Command Execution
# ---------------------------------------------------------------------------

def run_shell_command(command: str, cwd: Optional[str] = None, timeout: int = 30) -> dict:
    """
    Execute a shell command safely. All output is captured and returned.
    Dangerous commands are blocked by the validation layer.
    """
    if not _is_safe_command(command):
        return {"status": "blocked", "action": "shell", "message": "Command blocked by security policy."}

    logger.info(f"Executing shell: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "action": "shell",
            "command": command,
            "stdout": result.stdout.strip()[-2000:],  # Cap output size
            "stderr": result.stderr.strip()[-500:],
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "action": "shell", "command": command}
    except Exception as e:
        return {"status": "error", "action": "shell", "message": str(e)}


# ---------------------------------------------------------------------------
# File Operations
# ---------------------------------------------------------------------------

def search_files(query: str, root: str = os.path.expanduser("~"), max_results: int = 10) -> list:
    """Search for files matching a glob pattern under the given root."""
    logger.info(f"Searching for '{query}' under {root}")
    pattern = os.path.join(root, "**", f"*{query}*")
    matches = glob.glob(pattern, recursive=True)
    return matches[:max_results]


def move_file(src: str, dst: str) -> dict:
    """Move a file or directory."""
    try:
        shutil.move(src, dst)
        logger.info(f"Moved: {src} → {dst}")
        return {"status": "success", "action": "move", "from": src, "to": dst}
    except Exception as e:
        return {"status": "error", "action": "move", "message": str(e)}


def copy_file(src: str, dst: str) -> dict:
    """Copy a file."""
    try:
        shutil.copy2(src, dst)
        logger.info(f"Copied: {src} → {dst}")
        return {"status": "success", "action": "copy", "from": src, "to": dst}
    except Exception as e:
        return {"status": "error", "action": "copy", "message": str(e)}


def create_directory(path: str) -> dict:
    """Create a directory (with parents)."""
    try:
        os.makedirs(path, exist_ok=True)
        return {"status": "success", "action": "mkdir", "path": path}
    except Exception as e:
        return {"status": "error", "action": "mkdir", "message": str(e)}


# ---------------------------------------------------------------------------
# System Settings (macOS)
# ---------------------------------------------------------------------------

def set_volume(level: int) -> dict:
    """Set system volume (0-100)."""
    # macOS volume scale is 0-100 via osascript
    level = max(0, min(100, level))
    script = f'set volume output volume {level}'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        logger.info(f"Volume set to {level}%")
        return {"status": "success", "action": "set_volume", "level": level}
    except subprocess.CalledProcessError:
        return {"status": "error", "action": "set_volume"}


def get_volume() -> int:
    """Get current system volume."""
    script = 'output volume of (get volume settings)'
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        return int(result.stdout.strip())
    except Exception:
        return -1


def set_brightness(level: float) -> dict:
    """
    Set screen brightness (0.0 - 1.0).
    Requires `brightness` CLI tool: brew install brightness
    """
    level = max(0.0, min(1.0, level))
    try:
        subprocess.run(["brightness", str(level)], check=True, capture_output=True)
        return {"status": "success", "action": "set_brightness", "level": level}
    except FileNotFoundError:
        return {"status": "error", "action": "set_brightness", "message": "Install: brew install brightness"}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "action": "set_brightness", "message": str(e)}


def lock_screen() -> dict:
    """Lock the macOS screen."""
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to keystroke "q" using {control down, command down}'],
            check=True, capture_output=True,
        )
        return {"status": "success", "action": "lock_screen"}
    except subprocess.CalledProcessError:
        return {"status": "error", "action": "lock_screen"}


def sleep_system() -> dict:
    """Put the system to sleep."""
    try:
        subprocess.run(["pmset", "sleepnow"], check=True, capture_output=True)
        return {"status": "success", "action": "sleep"}
    except subprocess.CalledProcessError:
        return {"status": "error", "action": "sleep"}


# ---------------------------------------------------------------------------
# Browser Control
# ---------------------------------------------------------------------------

def open_url(url: str, browser: str = "Google Chrome") -> dict:
    """Open a URL in the specified browser."""
    try:
        subprocess.run(["open", "-a", browser, url], check=True, capture_output=True)
        return {"status": "success", "action": "open_url", "url": url, "browser": browser}
    except subprocess.CalledProcessError:
        return {"status": "error", "action": "open_url", "message": f"Failed to open URL in {browser}"}


def google_search(query: str) -> dict:
    """Open a Google search in the default browser."""
    import urllib.parse
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    return open_url(url)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def show_notification(title: str, message: str) -> dict:
    """Display a native macOS notification."""
    script = f'display notification "{message}" with title "{title}"'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        return {"status": "success", "action": "notification"}
    except subprocess.CalledProcessError:
        return {"status": "error", "action": "notification"}


# ---------------------------------------------------------------------------
# Command Registry — maps natural language intents to functions
# ---------------------------------------------------------------------------

COMMAND_REGISTRY = {
    "open_app": open_application,
    "close_app": close_application,
    "focus_app": focus_application,
    "list_apps": list_running_apps,
    "shell": run_shell_command,
    "search_files": search_files,
    "move_file": move_file,
    "copy_file": copy_file,
    "mkdir": create_directory,
    "set_volume": set_volume,
    "get_volume": get_volume,
    "set_brightness": set_brightness,
    "lock_screen": lock_screen,
    "sleep": sleep_system,
    "open_url": open_url,
    "google_search": google_search,
    "notify": show_notification,
}


def execute_action(action_name: str, **kwargs) -> dict:
    """
    Central dispatcher. Phase 39 agents use this to execute system actions.
    """
    if action_name not in COMMAND_REGISTRY:
        return {"status": "error", "message": f"Unknown action: {action_name}"}

    fn = COMMAND_REGISTRY[action_name]
    logger.info(f"⚡ Executing action: {action_name} with args: {kwargs}")
    try:
        return fn(**kwargs)
    except TypeError as e:
        return {"status": "error", "message": f"Invalid args for {action_name}: {e}"}
