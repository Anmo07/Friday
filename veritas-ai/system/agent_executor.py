"""
Friday System — Autonomous Agent Executor (Phase 39 — Full Siri/Google Level)
===============================================================================
Three-tier intent resolution:
  1. Conversational patterns (greetings, jokes, identity)
  2. System command patterns (60+ patterns covering every Siri/Google capability)
  3. LLM fallback via Ollama for general conversation

Covers: apps, files, volume, brightness, music, screenshots, battery, WiFi,
        Bluetooth, dark mode, DND, time, date, math, timers, notes, clipboard,
        processes, storage, RAM, IP, weather, unit conversion, and more.
"""

import re
import os
import logging
import random
from typing import Optional
from system.control_engine import execute_action

logger = logging.getLogger("friday.agent_executor")


# ---------------------------------------------------------------------------
# Tier 1: Conversational Patterns
# ---------------------------------------------------------------------------

CONVERSATIONAL_RESPONSES = [
    (r"^(?:hi|hello|hey|howdy|hola|greetings)[\s!.,?]*$", [
        "Hey there! I'm Friday, your autonomous system assistant. What can I do for you?",
        "Hello! Friday here. Ready to help.",
        "Hey! What would you like me to do?",
    ]),
    (r"(?:how are you|how do you do|how.?s it going|what.?s up|sup)\b", [
        "I'm running smoothly! All systems are online. How can I help?",
        "Doing great! All engines operational. What do you need?",
    ]),
    (r"(?:who are you|what are you|what.?s your name|your name)\b", [
        "I'm Friday — your autonomous AI system assistant, like Siri but I live in your terminal and can control your entire Mac. Ask me anything!",
    ]),
    (r"(?:what can you do|help me|capabilities|show commands|what do you know)\b", [
        "I can: open/close apps, control volume & brightness, play/pause music, "
        "take screenshots, check battery & storage, toggle WiFi & dark mode, "
        "do math, set timers, take notes, search Google, manage processes, "
        "and run multi-step workflows. Try 'what time is it' or 'open Safari'!",
    ]),
    (r"(?:thank you|thanks|thx|cheers|appreciate)\b", [
        "You're welcome! Anything else?",
        "Happy to help! What's next?",
    ]),
    (r"(?:good morning)[\s!]*$", [
        "Good morning! Want me to start your morning briefing? Just say 'morning briefing'.",
    ]),
    (r"(?:good night|good evening)[\s!]*$", [
        "Good night! Say 'end my day' if you want me to close everything.",
    ]),
    (r"(?:tell me a joke|joke|make me laugh|funny)\b", [
        "Why do programmers prefer dark mode? Because light attracts bugs.",
        "There are only 10 types of people: those who understand binary, and those who don't.",
        "A SQL query walks into a bar, sees two tables and asks: Can I join you?",
        "Why do Java developers wear glasses? Because they can't C#.",
        "!false — it's funny because it's true.",
    ]),
    (r"(?:you.?re (?:great|awesome|amazing|the best|cool|smart))\b", [
        "Thanks! I'm here to make your life easier. What's next?",
        "I try my best! What can I help with?",
    ]),
    (r"(?:i love you|love you)\b", [
        "That's sweet! I'm just an AI, but I appreciate the sentiment. How can I help?",
    ]),
    (r"(?:are you (?:real|alive|sentient|conscious))\b", [
        "I'm an AI running locally on your Mac. Not sentient, but I can get a lot done for you!",
    ]),
    (r"(?:sing|sing a song|sing for me)\b", [
        "🎵 Daisy, Daisy, give me your answer do... I'm afraid I'm better at running commands than singing!",
    ]),
]


def _match_conversational(text: str) -> Optional[str]:
    clean = text.lower().strip().rstrip(".!?")
    for pattern, responses in CONVERSATIONAL_RESPONSES:
        if re.search(pattern, clean):
            return random.choice(responses)
    return None


# ---------------------------------------------------------------------------
# Tier 2: System Intent Patterns (60+)
# ---------------------------------------------------------------------------

INTENT_PATTERNS = [
    # === APPLICATION CONTROL ===
    (r"(?:open|launch|start)\s+(.+)", "open_app", lambda m: {"app_name": m.group(1).strip()}),
    (r"(?:close|quit|kill)\s+(.+)", "close_app", lambda m: {"app_name": m.group(1).strip()}),
    (r"(?:focus|switch to|go to|bring up)\s+(.+)", "focus_app", lambda m: {"app_name": m.group(1).strip()}),
    (r"(?:list|show|what).+(?:running|open|active)\s*(?:apps|applications|programs)?", "list_apps", lambda m: {}),

    # === SHELL COMMANDS ===
    (r"(?:run|execute)\s+(?:command\s+)?(.+)", "shell", lambda m: {"command": m.group(1).strip()}),
    (r"(?:terminal|shell)\s+(.+)", "shell", lambda m: {"command": m.group(1).strip()}),

    # === FILE OPERATIONS ===
    (r"(?:search|find|locate)\s+(?:file|files?|for)\s+(.+)", "search_files", lambda m: {"query": m.group(1).strip()}),
    (r"(?:create|make)\s+(?:a\s+)?(?:folder|directory)\s+(?:called\s+)?(.+)", "mkdir", lambda m: {"path": m.group(1).strip()}),
    (r"(?:empty|clear)\s+(?:the\s+)?trash", "empty_trash", lambda m: {}),

    # === VOLUME ===
    (r"(?:get|check|show|what.?s|what is)\s+(?:the\s+)?volume", "get_volume", lambda m: {}),
    (r"(?:set|change)\s+(?:the\s+)?volume\s+(?:to\s+)?(\d+)", "set_volume", lambda m: {"level": int(m.group(1))}),
    (r"(?:turn\s+)?(?:volume\s+)?(?:up|louder|increase)", "set_volume", lambda m: {"level": 80}),
    (r"(?:turn\s+)?(?:volume\s+)?(?:down|quieter|decrease|lower)", "set_volume", lambda m: {"level": 30}),
    (r"(?:mute|silence|shut up)\b", "set_volume", lambda m: {"level": 0}),
    (r"(?:unmute|un-mute)\b", "set_volume", lambda m: {"level": 50}),
    (r"(?:max|maximum|full)\s+volume", "set_volume", lambda m: {"level": 100}),

    # === BRIGHTNESS ===
    (r"(?:set|change)\s+brightness\s+(?:to\s+)?(\d+)", "set_brightness", lambda m: {"level": int(m.group(1)) / 100.0}),
    (r"(?:brightness\s+)?(?:up|brighter|increase brightness)", "set_brightness", lambda m: {"level": 0.8}),
    (r"(?:brightness\s+)?(?:down|dimmer|dim|decrease brightness)", "set_brightness", lambda m: {"level": 0.3}),

    # === DARK MODE ===
    (r"(?:toggle|switch|change)\s+(?:to\s+)?dark\s+mode", "toggle_dark_mode", lambda m: {}),
    (r"(?:toggle|switch|change)\s+(?:to\s+)?light\s+mode", "toggle_dark_mode", lambda m: {}),
    (r"(?:is|am i|are we)\s+(?:in\s+)?dark\s+mode", "get_dark_mode", lambda m: {}),
    (r"(?:enable|turn on)\s+dark\s+mode", "toggle_dark_mode", lambda m: {}),

    # === DO NOT DISTURB ===
    (r"(?:toggle|turn on|turn off|enable|disable)\s+(?:do not disturb|dnd|focus)", "toggle_dnd", lambda m: {}),

    # === LOCK / SLEEP ===
    (r"lock\s+(?:the\s+)?(?:screen|computer|mac)", "lock_screen", lambda m: {}),
    (r"(?:put.+sleep|sleep\s+(?:the\s+)?(?:computer|mac|system))", "sleep", lambda m: {}),

    # === MATH (must be BEFORE time/date to prevent 'times' matching 'time') ===
    (r"(\d+)\s*(?:times|x|×)\s*(\d+)", "calculate", lambda m: {"expression": f"{m.group(1)}*{m.group(2)}"}),
    (r"(\d+)\s*(?:plus|\+)\s*(\d+)", "calculate", lambda m: {"expression": f"{m.group(1)}+{m.group(2)}"}),
    (r"(\d+)\s*(?:minus|-)\s*(\d+)", "calculate", lambda m: {"expression": f"{m.group(1)}-{m.group(2)}"}),
    (r"(\d+)\s*(?:divided by|÷|/)\s*(\d+)", "calculate", lambda m: {"expression": f"{m.group(1)}/{m.group(2)}"}),
    (r"(\d+(?:\.\d+)?)\s*(?:percent|%)\s+(?:of)\s+(\d+(?:\.\d+)?)", "calculate", lambda m: {"expression": f"{m.group(1)}/100*{m.group(2)}"}),
    (r"(?:calculate|compute|what.?s|what is|how much is)\s+([\d\s+\-*/().^%]+)", "calculate", lambda m: {"expression": m.group(1).strip()}),
    (r"(?:square root|sqrt)\s+(?:of\s+)?(\d+(?:\.\d+)?)", "calculate", lambda m: {"expression": f"{m.group(1)}**0.5"}),
    (r"convert\s+([\d.]+)\s+(\w+)\s+(?:to|in|into)\s+(\w+)", "convert_units",
     lambda m: {"value": float(m.group(1)), "from_unit": m.group(2), "to_unit": m.group(3)}),

    # === TIME & DATE ===
    (r"what\s+time\s+is\s+it", "get_time", lambda m: {}),
    (r"(?:what.?s?\s+)?(?:the\s+)?(?:current\s+)?time\b(?!s)", "get_time", lambda m: {}),
    (r"(?:what.?s?\s+)?(?:the\s+)?(?:today.?s?\s+)?date", "get_date", lambda m: {}),
    (r"(?:what\s+)?day\s+(?:is\s+)?(?:it|today)", "get_date", lambda m: {}),

    # === BATTERY ===
    (r"(?:how much|what.?s|check|show|get)\s+(?:the\s+)?(?:battery|charge|power)", "get_battery", lambda m: {}),
    (r"(?:battery|charge)\s+(?:level|status|percentage|percent)", "get_battery", lambda m: {}),
    (r"am i charging", "get_battery", lambda m: {}),

    # === STORAGE ===
    (r"(?:how much|check|show|get)\s+(?:disk\s+)?(?:storage|space|disk)", "get_storage", lambda m: {}),
    (r"(?:storage|disk)\s+(?:usage|space|left|available)", "get_storage", lambda m: {}),

    # === RAM / MEMORY ===
    (r"(?:how much|check|show|get)\s+(?:ram|memory)", "get_ram", lambda m: {}),
    (r"(?:ram|memory)\s+(?:usage|info|status)", "get_ram", lambda m: {}),

    # === IP ADDRESS ===
    (r"(?:what.?s|show|get|check)\s+(?:my\s+)?(?:ip|ip address)", "get_ip", lambda m: {}),
    (r"(?:my\s+)?ip\s+address", "get_ip", lambda m: {}),

    # === CPU ===
    (r"(?:cpu|processor)\s+(?:usage|info|load|status)", "get_cpu", lambda m: {}),
    (r"(?:how.?s|check)\s+(?:the\s+)?cpu", "get_cpu", lambda m: {}),

    # === UPTIME ===
    (r"(?:system\s+)?uptime", "get_uptime", lambda m: {}),
    (r"how long.+(?:been on|running|up)", "get_uptime", lambda m: {}),

    # === WIFI ===
    (r"(?:what.?s|show|get)\s+(?:my\s+)?(?:wifi|wi-fi)\s*(?:network|name)?", "get_wifi", lambda m: {}),
    (r"(?:turn on|enable|connect)\s+(?:the\s+)?(?:wifi|wi-fi)", "wifi_on", lambda m: {}),
    (r"(?:turn off|disable|disconnect)\s+(?:the\s+)?(?:wifi|wi-fi)", "wifi_off", lambda m: {}),

    # === BLUETOOTH ===
    (r"(?:turn on|enable)\s+bluetooth", "bluetooth_on", lambda m: {}),
    (r"(?:turn off|disable)\s+bluetooth", "bluetooth_off", lambda m: {}),

    # === MUSIC / MEDIA ===
    (r"(?:play|pause|resume)\s+(?:the\s+)?(?:music|song|track|audio)", "music_play_pause", lambda m: {}),
    (r"(?:play|pause)\b(?!\s+\w)", "music_play_pause", lambda m: {}),
    (r"(?:next|skip)\s+(?:song|track)?", "music_next", lambda m: {}),
    (r"(?:previous|prev|back|last)\s+(?:song|track)?", "music_previous", lambda m: {}),
    (r"(?:what.?s|what is)\s+(?:this\s+)?(?:playing|song|track|currently playing)", "get_track", lambda m: {}),

    # === SCREENSHOT ===
    (r"(?:take|capture|grab)\s+(?:a\s+)?screenshot", "screenshot", lambda m: {"full": True}),
    (r"screenshot", "screenshot", lambda m: {"full": True}),

    # === CLIPBOARD ===
    (r"(?:what.?s|show|get|read)\s+(?:on\s+)?(?:my\s+)?(?:clipboard|copied)", "get_clipboard", lambda m: {}),
    (r"(?:copy|set clipboard)\s+(?:to\s+)?(.+)", "set_clipboard", lambda m: {"text": m.group(1).strip()}),

    # === TIMER ===
    (r"(?:set|start)\s+(?:a\s+)?timer\s+(?:for\s+)?(\d+)\s*(?:seconds?|secs?|s)\b", "set_timer", lambda m: {"seconds": int(m.group(1))}),
    (r"(?:set|start)\s+(?:a\s+)?timer\s+(?:for\s+)?(\d+)\s*(?:minutes?|mins?|m)\b", "set_timer", lambda m: {"seconds": int(m.group(1)) * 60}),
    (r"(?:set|start)\s+(?:a\s+)?timer\s+(?:for\s+)?(\d+)\s*(?:hours?|hrs?|h)\b", "set_timer", lambda m: {"seconds": int(m.group(1)) * 3600}),

    # === NOTES ===
    (r"(?:take a note|add note|note|write down|remember)\s+(.+)", "add_note", lambda m: {"content": m.group(1).strip()}),
    (r"(?:show|read|get|list)\s+(?:my\s+)?notes", "read_notes", lambda m: {}),
    (r"(?:clear|delete|erase)\s+(?:all\s+)?(?:my\s+)?notes", "clear_notes", lambda m: {}),

    # (Math & conversion patterns moved above TIME to avoid 'times' → 'time' conflict)

    # === PROCESSES ===
    (r"(?:show|list|get|what.?s)\s+(?:the\s+)?(?:top\s+)?(?:running\s+)?processes", "top_processes", lambda m: {}),
    (r"(?:what.?s|show)\s+(?:using|eating|consuming)\s+(?:my\s+)?(?:cpu|ram|memory)", "top_processes", lambda m: {}),
    (r"(?:kill|stop|end)\s+(?:process\s+)?(.+)", "kill_process", lambda m: {"name": m.group(1).strip()}),

    # === BROWSER / WEB ===
    (r"(?:open|go to|navigate to|visit)\s+(?:the\s+)?(?:url|website|site)?\s*(https?://\S+)", "open_url", lambda m: {"url": m.group(1)}),
    (r"(?:google|search|look up|search for)\s+(.+)", "google_search", lambda m: {"query": m.group(1).strip()}),

    # === NOTIFICATIONS ===
    (r"(?:remind|notify|alert)\s+(?:me\s+)?(?:to\s+)?(.+)", "notify", lambda m: {"title": "Friday Reminder", "message": m.group(1).strip()}),
]


class IntentPlanner:
    def parse(self, text: str) -> Optional[tuple]:
        if not text:
            return None
        clean = text.lower().strip().rstrip(".")
        for pattern, action, extractor in INTENT_PATTERNS:
            match = re.search(pattern, clean)
            if match:
                try:
                    kwargs = extractor(match)
                    logger.info(f"🧠 Intent matched: [{action}] with args {kwargs}")
                    return action, kwargs
                except Exception as e:
                    logger.error(f"Extractor error: {e}")
        return None


# ---------------------------------------------------------------------------
# Tier 3: LLM Fallback via Ollama
# ---------------------------------------------------------------------------

def _ask_ollama(prompt: str) -> Optional[str]:
    try:
        import requests
        ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        response = requests.post(
            f"{ollama_host}/api/generate",
            json={
                "model": "llama3.2",
                "prompt": (
                    "You are Friday, an AI assistant like Jarvis from Iron Man. "
                    "Be helpful, concise, and witty. Keep responses under 2 sentences. "
                    f"User: {prompt}"
                ),
                "stream": False,
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception as e:
        logger.debug(f"Ollama unavailable: {e}")
    return None


# ---------------------------------------------------------------------------
# Agent Executor
# ---------------------------------------------------------------------------

class AgentExecutor:

    def __init__(self):
        self.planner = IntentPlanner()

    def process_command(self, text: str) -> dict:
        # Tier 1: Conversational
        convo = _match_conversational(text)
        if convo:
            logger.info(f"💬 Conversational match")
            return {"status": "conversational", "action": "conversation",
                    "speech_response": convo, "result": None}

        # Tier 2: System intent
        intent = self.planner.parse(text)
        if intent is not None:
            action_name, kwargs = intent
            result = execute_action(action_name, **kwargs)
            speech = self._generate_response(action_name, kwargs, result)
            return {"status": result.get("status", "unknown") if isinstance(result, dict) else "success",
                    "action": action_name, "result": result, "speech_response": speech}

        # Tier 3: LLM fallback
        llm = _ask_ollama(text)
        if llm:
            logger.info(f"🤖 LLM response")
            return {"status": "llm_response", "action": "conversation",
                    "speech_response": llm, "result": None}

        return {"status": "no_match", "action": "",
                "speech_response": "I'm not sure about that. Try 'help' to see what I can do.",
                "result": None}

    def _generate_response(self, action: str, kwargs: dict, result: dict) -> str:
        if not isinstance(result, dict):
            return "Done."
        status = result.get("status", "error")

        if status == "blocked":
            return "Blocked by security policy."
        if status == "error":
            return f"Sorry, error: {result.get('message', 'unknown')}"

        # ---- System info responses ----
        if action == "get_battery":
            pct = result.get("percentage", "?")
            charging = "and charging" if result.get("charging") else "and not charging"
            return f"Battery is at {pct} percent, {charging}."

        if action == "get_storage":
            return f"Storage: {result.get('used', '?')} used of {result.get('total', '?')}. {result.get('available', '?')} available."

        if action == "get_ram":
            return f"You have {result.get('total_gb', '?')} gigabytes of RAM."

        if action == "get_ip":
            local = result.get("local_ip", "unknown")
            public = result.get("public_ip", "unknown")
            return f"Local IP: {local}. Public IP: {public}."

        if action == "get_cpu":
            return f"Total CPU usage is {result.get('total_cpu_percent', '?')} percent."

        if action == "get_uptime":
            return result.get("uptime", "Unknown uptime.")

        if action == "get_wifi":
            return f"You're connected to: {result.get('ssid', 'unknown')}."

        if action == "get_time":
            return f"It's {result.get('time', '?')}."

        if action == "get_date":
            return f"Today is {result.get('date', '?')}."

        if action == "get_volume":
            return f"Volume is at {result.get('volume', '?')} percent."

        if action == "get_dark_mode":
            mode = "dark mode" if result.get("dark_mode") else "light mode"
            return f"You're currently in {mode}."

        # ---- Math / convert ----
        if action == "calculate":
            return f"The answer is {result.get('result', '?')}."

        if action == "convert_units":
            return f"{result.get('from', '?')} is {result.get('to', '?')}."

        # ---- Music ----
        if action == "music_play_pause":
            return "Toggling play and pause."
        if action == "music_next":
            return "Skipping to next track."
        if action == "music_previous":
            return "Going back to previous track."
        if action == "get_track":
            track = result.get("track", "Unknown")
            artist = result.get("artist", "Unknown")
            return f"Now playing: {track} by {artist}."

        # ---- Screenshot ----
        if action == "screenshot":
            return "Screenshot saved to your Desktop."

        # ---- Clipboard ----
        if action == "get_clipboard":
            content = result.get("content", "")
            if content:
                return f"Your clipboard contains: {content[:100]}"
            return "Clipboard is empty."

        # ---- Timer ----
        if action == "set_timer":
            secs = kwargs.get("seconds", 0)
            if secs >= 60:
                return f"Timer set for {secs // 60} minutes."
            return f"Timer set for {secs} seconds."

        # ---- Notes ----
        if action == "add_note":
            return f"Note saved: {kwargs.get('content', '')[:80]}"
        if action == "read_notes":
            notes = result.get("notes", [])
            if not notes:
                return "You have no notes yet."
            return f"You have {result.get('count', len(notes))} notes. Most recent: {notes[-1]}"
        if action == "clear_notes":
            return "All notes cleared."

        # ---- WiFi / Bluetooth ----
        if action in ("wifi_on", "wifi_off"):
            return f"WiFi turned {result.get('wifi', 'toggled')}."
        if action in ("bluetooth_on", "bluetooth_off"):
            return f"Bluetooth turned {result.get('bluetooth', 'toggled')}."

        # ---- Processes ----
        if action == "top_processes":
            procs = result.get("processes", [])
            if procs:
                top3 = ", ".join(f"{p['name']} ({p['cpu']}%)" for p in procs[:3])
                return f"Top processes: {top3}."
            return "Couldn't get process info."
        if action == "kill_process":
            return f"Killed process: {kwargs.get('name', 'unknown')}."

        # ---- Dark mode / DND ----
        if action == "toggle_dark_mode":
            return "Dark mode toggled."
        if action == "toggle_dnd":
            return "Do Not Disturb toggled."

        # ---- Trash ----
        if action == "empty_trash":
            return "Trash emptied."

        # ---- Standard ----
        if action == "open_app":
            return f"Opening {kwargs.get('app_name', 'the app')}."
        if action == "close_app":
            return f"Closing {kwargs.get('app_name', 'the app')}."
        if action == "list_apps":
            apps = result.get("apps", [])
            top = ", ".join(apps[:5]) if apps else "none"
            return f"{result.get('count', 0)} apps running. Including: {top}."
        if action == "shell":
            out = result.get("stdout", "")
            if out:
                return f"Done. Output: {out[:150]}"
            return "Command executed."
        if action == "search_files":
            count = result.get("count", 0)
            files = result.get("files", [])
            if files:
                return f"Found {count} files. First: {os.path.basename(files[0])}"
            return "No files found."
        if action == "set_volume":
            return f"Volume set to {kwargs.get('level', '?')} percent."
        if action == "lock_screen":
            return "Locking the screen."
        if action == "open_url":
            return "Opening URL in browser."
        if action == "google_search":
            return f"Searching Google for: {kwargs.get('query', '')}"
        if action == "notify":
            return f"Reminder set: {kwargs.get('message', '')}"

        return "Done."
