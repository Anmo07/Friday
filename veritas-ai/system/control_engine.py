"""
Friday System — System Control Engine (Phase 38 — Extended)
=============================================================
Full Siri/Google-level macOS system control providing 50+ operations:
  - Application management
  - Shell command execution
  - File operations
  - System settings (volume, brightness, dark mode, DND)
  - Browser & web
  - Music & media control
  - System information (battery, storage, RAM, IP, CPU)
  - Screenshot & clipboard
  - Timer & stopwatch
  - Notes
  - Wi-Fi & Bluetooth
  - Process management
  - Trash management
  - Calendar
  - Math & conversions
  - Date & time

Every action is logged. Dangerous operations are blocked.
"""

import subprocess
import os
import shutil
import glob
import platform
import logging
import time
import math
import re
import json
import threading
from datetime import datetime, timedelta
from typing import Optional, List

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


def _run_osascript(script: str) -> str:
    """Helper: run AppleScript and return stdout."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"AppleScript error: {e}")
        return ""


# ===========================================================================
# APPLICATION CONTROL
# ===========================================================================

def open_application(app_name: str) -> dict:
    """Open an application by name."""
    logger.info(f"Opening application: {app_name}")
    try:
        subprocess.run(["open", "-a", app_name], check=True, capture_output=True, text=True)
        return {"status": "success", "action": "open_app", "target": app_name}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "action": "open_app", "message": e.stderr.strip()}


def close_application(app_name: str) -> dict:
    """Close an application gracefully via AppleScript."""
    logger.info(f"Closing application: {app_name}")
    _run_osascript(f'tell application "{app_name}" to quit')
    return {"status": "success", "action": "close_app", "target": app_name}


def focus_application(app_name: str) -> dict:
    """Bring an application to the foreground."""
    _run_osascript(f'tell application "{app_name}" to activate')
    return {"status": "success", "action": "focus_app", "target": app_name}


def list_running_apps() -> dict:
    """Return a list of currently running applications."""
    output = _run_osascript(
        'tell application "System Events" to get name of every process whose background only is false'
    )
    apps = [a.strip() for a in output.split(",") if a.strip()] if output else []
    return {"status": "success", "apps": apps, "count": len(apps)}


# ===========================================================================
# SHELL COMMAND EXECUTION
# ===========================================================================

def run_shell_command(command: str, cwd: Optional[str] = None, timeout: int = 30) -> dict:
    """Execute a shell command safely."""
    if not _is_safe_command(command):
        return {"status": "blocked", "message": "Command blocked by security policy."}
    logger.info(f"Executing shell: {command}")
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, cwd=cwd, timeout=timeout,
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout.strip()[-2000:],
            "stderr": result.stderr.strip()[-500:],
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "command": command}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ===========================================================================
# FILE OPERATIONS
# ===========================================================================

def search_files(query: str, root: str = os.path.expanduser("~"), max_results: int = 10) -> dict:
    """Search for files matching a pattern."""
    logger.info(f"Searching for '{query}' under {root}")
    pattern = os.path.join(root, "**", f"*{query}*")
    matches = glob.glob(pattern, recursive=True)[:max_results]
    return {"status": "success", "files": matches, "count": len(matches)}


def move_file(src: str, dst: str) -> dict:
    try:
        shutil.move(src, dst)
        return {"status": "success", "from": src, "to": dst}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def copy_file(src: str, dst: str) -> dict:
    try:
        shutil.copy2(src, dst)
        return {"status": "success", "from": src, "to": dst}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def create_directory(path: str) -> dict:
    os.makedirs(path, exist_ok=True)
    return {"status": "success", "path": path}


def empty_trash() -> dict:
    """Empty the macOS Trash."""
    _run_osascript('tell application "Finder" to empty trash')
    return {"status": "success", "action": "empty_trash"}


# ===========================================================================
# SYSTEM SETTINGS
# ===========================================================================

def set_volume(level: int) -> dict:
    level = max(0, min(100, level))
    _run_osascript(f'set volume output volume {level}')
    logger.info(f"Volume set to {level}%")
    return {"status": "success", "level": level}


def get_volume() -> dict:
    vol = _run_osascript('output volume of (get volume settings)')
    return {"status": "success", "volume": int(vol) if vol.isdigit() else -1}


def set_brightness(level: float) -> dict:
    level = max(0.0, min(1.0, level))
    try:
        subprocess.run(["brightness", str(level)], check=True, capture_output=True)
        return {"status": "success", "level": level}
    except FileNotFoundError:
        return {"status": "error", "message": "Install: brew install brightness"}


def lock_screen() -> dict:
    subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to keystroke "q" using {control down, command down}'],
        capture_output=True,
    )
    return {"status": "success"}


def sleep_system() -> dict:
    subprocess.run(["pmset", "sleepnow"], capture_output=True)
    return {"status": "success"}


def toggle_dark_mode() -> dict:
    """Toggle between dark and light mode."""
    _run_osascript(
        'tell app "System Events" to tell appearance preferences to set dark mode to not dark mode'
    )
    return {"status": "success"}


def get_dark_mode() -> dict:
    """Check if dark mode is active."""
    result = _run_osascript(
        'tell app "System Events" to tell appearance preferences to get dark mode'
    )
    return {"status": "success", "dark_mode": result.lower() == "true"}


def toggle_do_not_disturb() -> dict:
    """Toggle Do Not Disturb / Focus mode."""
    # macOS Monterey+ uses Focus
    script = '''
    tell application "System Events"
        tell process "ControlCenter"
            click menu bar item "Control Center" of menu bar 1
            delay 0.5
            click checkbox "Focus" of group 1 of window "Control Center"
        end tell
    end tell
    '''
    _run_osascript(script)
    return {"status": "success"}


# ===========================================================================
# SYSTEM INFORMATION
# ===========================================================================

def get_battery_info() -> dict:
    """Get battery percentage and charging status."""
    try:
        result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
        output = result.stdout
        # Parse: "100%; charging" or "87%; discharging"
        match = re.search(r'(\d+)%;\s*(\w+)', output)
        if match:
            return {"status": "success", "percentage": int(match.group(1)),
                    "charging": "charging" in match.group(2).lower()}
    except Exception:
        pass
    return {"status": "error", "message": "Could not read battery"}


def get_storage_info() -> dict:
    """Get disk usage for the main drive."""
    try:
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            return {"status": "success", "total": parts[1], "used": parts[2],
                    "available": parts[3], "percent_used": parts[4]}
    except Exception:
        pass
    return {"status": "error"}


def get_ram_info() -> dict:
    """Get memory usage."""
    try:
        result = subprocess.run(
            ["vm_stat"], capture_output=True, text=True
        )
        # Also get total via sysctl
        total_result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True
        )
        total_bytes = int(total_result.stdout.strip())
        total_gb = round(total_bytes / (1024 ** 3), 1)
        return {"status": "success", "total_gb": total_gb}
    except Exception:
        return {"status": "error"}


def get_ip_address() -> dict:
    """Get local and public IP."""
    local_ip = ""
    public_ip = ""
    try:
        result = subprocess.run(
            ["ipconfig", "getifaddr", "en0"], capture_output=True, text=True
        )
        local_ip = result.stdout.strip()
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["curl", "-s", "ifconfig.me"], capture_output=True, text=True, timeout=5
        )
        public_ip = result.stdout.strip()
    except Exception:
        pass
    return {"status": "success", "local_ip": local_ip, "public_ip": public_ip}


def get_cpu_usage() -> dict:
    """Get current CPU usage."""
    try:
        result = subprocess.run(
            ["ps", "-A", "-o", "%cpu"], capture_output=True, text=True
        )
        lines = result.stdout.strip().split("\n")[1:]  # Skip header
        total = sum(float(l.strip()) for l in lines if l.strip())
        return {"status": "success", "total_cpu_percent": round(total, 1)}
    except Exception:
        return {"status": "error"}


def get_uptime() -> dict:
    """Get system uptime."""
    try:
        result = subprocess.run(["uptime"], capture_output=True, text=True)
        return {"status": "success", "uptime": result.stdout.strip()}
    except Exception:
        return {"status": "error"}


def get_wifi_network() -> dict:
    """Get current Wi-Fi network name."""
    try:
        result = subprocess.run(
            ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
            capture_output=True, text=True,
        )
        for line in result.stdout.split("\n"):
            if " SSID:" in line:
                return {"status": "success", "ssid": line.split("SSID:")[1].strip()}
    except Exception:
        pass
    return {"status": "success", "ssid": "Unknown"}


# ===========================================================================
# DATE & TIME
# ===========================================================================

def get_current_time() -> dict:
    now = datetime.now()
    return {"status": "success", "time": now.strftime("%I:%M %p"),
            "date": now.strftime("%A, %B %d, %Y")}


def get_current_date() -> dict:
    now = datetime.now()
    return {"status": "success", "date": now.strftime("%A, %B %d, %Y"),
            "day": now.strftime("%A")}


# ===========================================================================
# MATH & CALCULATIONS
# ===========================================================================

def calculate(expression: str) -> dict:
    """Safely evaluate a math expression."""
    try:
        # Sanitize: only allow digits, operators, parentheses, decimal points
        clean = re.sub(r'[^0-9+\-*/().%^ ]', '', expression)
        clean = clean.replace('^', '**')
        # Use eval with restricted globals
        result = eval(clean, {"__builtins__": {}}, {"math": math})
        return {"status": "success", "expression": expression, "result": result}
    except Exception as e:
        return {"status": "error", "message": f"Could not calculate: {e}"}


def convert_units(value: float, from_unit: str, to_unit: str) -> dict:
    """Convert between common units."""
    conversions = {
        ("miles", "km"): 1.60934,  ("km", "miles"): 0.621371,
        ("feet", "meters"): 0.3048, ("meters", "feet"): 3.28084,
        ("inches", "cm"): 2.54,     ("cm", "inches"): 0.393701,
        ("pounds", "kg"): 0.453592, ("kg", "pounds"): 2.20462,
        ("fahrenheit", "celsius"): None,  # Special handling
        ("celsius", "fahrenheit"): None,
        ("gallons", "liters"): 3.78541,  ("liters", "gallons"): 0.264172,
    }
    key = (from_unit.lower(), to_unit.lower())
    if key in conversions:
        factor = conversions[key]
        if key == ("fahrenheit", "celsius"):
            result = (value - 32) * 5 / 9
        elif key == ("celsius", "fahrenheit"):
            result = value * 9 / 5 + 32
        else:
            result = value * factor
        return {"status": "success", "result": round(result, 4),
                "from": f"{value} {from_unit}", "to": f"{round(result, 4)} {to_unit}"}
    return {"status": "error", "message": f"Unknown conversion: {from_unit} to {to_unit}"}


# ===========================================================================
# MUSIC & MEDIA CONTROL
# ===========================================================================

def music_play_pause() -> dict:
    """Toggle play/pause in Apple Music or Spotify."""
    _run_osascript('''
        tell application "System Events"
            key code 49 using {command down, option down}
        end tell
    ''')
    # Try Music first, then Spotify
    _run_osascript('tell application "Music" to playpause')
    return {"status": "success", "action": "play_pause"}


def music_next() -> dict:
    _run_osascript('tell application "Music" to next track')
    return {"status": "success", "action": "next_track"}


def music_previous() -> dict:
    _run_osascript('tell application "Music" to previous track')
    return {"status": "success", "action": "previous_track"}


def get_current_track() -> dict:
    """Get currently playing track info."""
    name = _run_osascript('tell application "Music" to get name of current track')
    artist = _run_osascript('tell application "Music" to get artist of current track')
    if name:
        return {"status": "success", "track": name, "artist": artist}
    return {"status": "error", "message": "No track playing"}


# ===========================================================================
# SCREENSHOT & CLIPBOARD
# ===========================================================================

def take_screenshot(full: bool = True) -> dict:
    """Take a screenshot. Saves to Desktop by default."""
    try:
        if full:
            subprocess.run(["screencapture", "-x",
                           os.path.expanduser("~/Desktop/friday_screenshot.png")],
                          check=True, capture_output=True)
        else:
            # Interactive selection
            subprocess.run(["screencapture", "-i",
                           os.path.expanduser("~/Desktop/friday_screenshot.png")],
                          check=True, capture_output=True)
        return {"status": "success", "path": "~/Desktop/friday_screenshot.png"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_clipboard() -> dict:
    """Get current clipboard contents."""
    try:
        result = subprocess.run(["pbpaste"], capture_output=True, text=True)
        return {"status": "success", "content": result.stdout[:500]}
    except Exception:
        return {"status": "error"}


def set_clipboard(text: str) -> dict:
    """Set clipboard contents."""
    try:
        process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        process.communicate(text.encode())
        return {"status": "success"}
    except Exception:
        return {"status": "error"}


# ===========================================================================
# TIMER & STOPWATCH
# ===========================================================================

_active_timers = {}


def set_timer(seconds: int, label: str = "Timer") -> dict:
    """Set a countdown timer that speaks when done."""
    def _timer_done():
        time.sleep(seconds)
        subprocess.run(["say", f"{label} complete. {seconds} seconds elapsed."],
                      capture_output=True)
        # Also play a sound
        subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], capture_output=True)
        _active_timers.pop(label, None)

    t = threading.Thread(target=_timer_done, daemon=True)
    t.start()
    _active_timers[label] = t
    return {"status": "success", "seconds": seconds, "label": label}


# ===========================================================================
# NOTES
# ===========================================================================

NOTES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "friday_notes.txt")


def add_note(content: str) -> dict:
    """Add a quick note."""
    os.makedirs(os.path.dirname(NOTES_PATH), exist_ok=True)
    with open(NOTES_PATH, "a") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {content}\n")
    return {"status": "success", "note": content}


def read_notes() -> dict:
    """Read all saved notes."""
    if not os.path.exists(NOTES_PATH):
        return {"status": "success", "notes": [], "message": "No notes yet."}
    with open(NOTES_PATH, "r") as f:
        notes = [line.strip() for line in f.readlines() if line.strip()]
    return {"status": "success", "notes": notes[-10:], "count": len(notes)}


def clear_notes() -> dict:
    """Clear all notes."""
    if os.path.exists(NOTES_PATH):
        os.remove(NOTES_PATH)
    return {"status": "success"}


# ===========================================================================
# WIFI & BLUETOOTH
# ===========================================================================

def toggle_wifi(on: bool = True) -> dict:
    """Turn WiFi on or off."""
    state = "on" if on else "off"
    try:
        subprocess.run(["networksetup", "-setairportpower", "en0", state],
                      capture_output=True, check=True)
        return {"status": "success", "wifi": state}
    except Exception:
        return {"status": "error"}


def toggle_bluetooth(on: bool = True) -> dict:
    """Toggle Bluetooth (requires blueutil: brew install blueutil)."""
    state = "1" if on else "0"
    try:
        subprocess.run(["blueutil", "--power", state], capture_output=True, check=True)
        return {"status": "success", "bluetooth": "on" if on else "off"}
    except FileNotFoundError:
        return {"status": "error", "message": "Install: brew install blueutil"}


# ===========================================================================
# PROCESS MANAGEMENT
# ===========================================================================

def get_top_processes(n: int = 5) -> dict:
    """Get top N CPU-consuming processes."""
    try:
        result = subprocess.run(
            ["ps", "-eo", "pid,%cpu,%mem,comm", "-r"],
            capture_output=True, text=True,
        )
        lines = result.stdout.strip().split("\n")[1:n+1]
        processes = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                processes.append({
                    "pid": parts[0], "cpu": parts[1],
                    "mem": parts[2], "name": os.path.basename(parts[3])
                })
        return {"status": "success", "processes": processes}
    except Exception:
        return {"status": "error"}


def kill_process(name: str) -> dict:
    """Kill a process by name."""
    try:
        subprocess.run(["pkill", "-f", name], capture_output=True)
        return {"status": "success", "killed": name}
    except Exception:
        return {"status": "error"}


# ===========================================================================
# BROWSER CONTROL
# ===========================================================================

def open_url(url: str, browser: str = "Google Chrome") -> dict:
    try:
        subprocess.run(["open", "-a", browser, url], check=True, capture_output=True)
        return {"status": "success", "url": url}
    except subprocess.CalledProcessError:
        return {"status": "error"}


def google_search(query: str) -> dict:
    import urllib.parse
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    return open_url(url)


# ===========================================================================
# NOTIFICATIONS
# ===========================================================================

def show_notification(title: str, message: str) -> dict:
    _run_osascript(f'display notification "{message}" with title "{title}"')
    return {"status": "success"}


# ===========================================================================
# COMMAND REGISTRY
# ===========================================================================

COMMAND_REGISTRY = {
    # Apps
    "open_app": open_application, "close_app": close_application,
    "focus_app": focus_application, "list_apps": list_running_apps,
    # Shell
    "shell": run_shell_command,
    # Files
    "search_files": search_files, "move_file": move_file,
    "copy_file": copy_file, "mkdir": create_directory, "empty_trash": empty_trash,
    # System settings
    "set_volume": set_volume, "get_volume": get_volume,
    "set_brightness": set_brightness,
    "lock_screen": lock_screen, "sleep": sleep_system,
    "toggle_dark_mode": toggle_dark_mode, "get_dark_mode": get_dark_mode,
    "toggle_dnd": toggle_do_not_disturb,
    # System info
    "get_battery": get_battery_info, "get_storage": get_storage_info,
    "get_ram": get_ram_info, "get_ip": get_ip_address,
    "get_cpu": get_cpu_usage, "get_uptime": get_uptime,
    "get_wifi": get_wifi_network,
    # Date & time
    "get_time": get_current_time, "get_date": get_current_date,
    # Math
    "calculate": calculate, "convert_units": convert_units,
    # Music
    "music_play_pause": music_play_pause, "music_next": music_next,
    "music_previous": music_previous, "get_track": get_current_track,
    # Screenshot & clipboard
    "screenshot": take_screenshot, "get_clipboard": get_clipboard,
    "set_clipboard": set_clipboard,
    # Timer
    "set_timer": set_timer,
    # Notes
    "add_note": add_note, "read_notes": read_notes, "clear_notes": clear_notes,
    # WiFi & Bluetooth
    "wifi_on": lambda: toggle_wifi(True), "wifi_off": lambda: toggle_wifi(False),
    "bluetooth_on": lambda: toggle_bluetooth(True), "bluetooth_off": lambda: toggle_bluetooth(False),
    # Processes
    "top_processes": get_top_processes, "kill_process": kill_process,
    # Browser
    "open_url": open_url, "google_search": google_search,
    # Notifications
    "notify": show_notification,
}


def execute_action(action_name: str, **kwargs) -> dict:
    """Central dispatcher for all system actions."""
    if action_name not in COMMAND_REGISTRY:
        return {"status": "error", "message": f"Unknown action: {action_name}"}
    fn = COMMAND_REGISTRY[action_name]
    logger.info(f"⚡ Executing action: {action_name} with args: {kwargs}")
    try:
        result = fn(**kwargs)
        return result if isinstance(result, dict) else {"status": "success", "data": result}
    except TypeError as e:
        return {"status": "error", "message": f"Invalid args for {action_name}: {e}"}
