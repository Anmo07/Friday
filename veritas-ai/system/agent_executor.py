"""
Friday System — Autonomous Agent Executor (Phase 39)
=====================================================
Bridges voice input to system actions via an intent-planning agent.

Flow:
  Voice → STT (Phase 37) → IntentPlanner → ActionExecutor → ControlEngine (Phase 38) → TTS Feedback

The planner uses rule-based intent matching for reliability and speed.
In production, this can be upgraded to an LLM-based planner using Ollama.
"""

import re
import logging
from typing import Optional
from system.control_engine import execute_action, COMMAND_REGISTRY

logger = logging.getLogger("friday.agent_executor")


# ---------------------------------------------------------------------------
# Intent Patterns — maps natural language to structured actions
# ---------------------------------------------------------------------------

INTENT_PATTERNS = [
    # Application control
    (r"(?:open|launch|start)\s+(.+)", "open_app", lambda m: {"app_name": m.group(1).strip()}),
    (r"(?:close|quit|exit|kill)\s+(.+)", "close_app", lambda m: {"app_name": m.group(1).strip()}),
    (r"(?:focus|switch to|go to)\s+(.+)", "focus_app", lambda m: {"app_name": m.group(1).strip()}),
    (r"(?:list|show|what).+(?:running|open|active)\s*(?:apps|applications)?", "list_apps", lambda m: {}),

    # Shell commands
    (r"(?:run|execute|do)\s+(?:command\s+)?(.+)", "shell", lambda m: {"command": m.group(1).strip()}),
    (r"(?:start|run)\s+docker\s*(.*)", "shell", lambda m: {"command": f"docker {m.group(1).strip()}".strip()}),
    (r"(?:start|run)\s+(?:the\s+)?server", "shell", lambda m: {"command": "npm run dev"}),

    # File operations
    (r"(?:search|find|locate)\s+(?:file|files?|for)\s+(.+)", "search_files", lambda m: {"query": m.group(1).strip()}),
    (r"(?:create|make)\s+(?:a\s+)?(?:folder|directory)\s+(?:called\s+)?(.+)", "mkdir", lambda m: {"path": m.group(1).strip()}),

    # System settings
    (r"(?:set|change)\s+volume\s+(?:to\s+)?(\d+)", "set_volume", lambda m: {"level": int(m.group(1))}),
    (r"(?:mute|silence)", "set_volume", lambda m: {"level": 0}),
    (r"(?:max|maximum)\s+volume", "set_volume", lambda m: {"level": 100}),
    (r"(?:set|change)\s+brightness\s+(?:to\s+)?(\d+)", "set_brightness", lambda m: {"level": int(m.group(1)) / 100.0}),
    (r"(?:lock)\s+(?:the\s+)?(?:screen|computer|mac)", "lock_screen", lambda m: {}),
    (r"(?:sleep|hibernate)", "sleep", lambda m: {}),

    # Browser / web
    (r"(?:open|go to|navigate to|visit)\s+(?:the\s+)?(?:url|website|site)?\s*(https?://\S+)", "open_url", lambda m: {"url": m.group(1)}),
    (r"(?:google|search|look up)\s+(?:for\s+)?(.+)", "google_search", lambda m: {"query": m.group(1).strip()}),

    # Notifications
    (r"(?:remind|notify|alert)\s+(?:me\s+)?(?:to\s+)?(.+)", "notify", lambda m: {"title": "Friday Reminder", "message": m.group(1).strip()}),
]


class IntentPlanner:
    """
    Matches free-form text to a structured intent + parameters.
    Returns (action_name, kwargs) or None if no match.
    """

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
                    logger.error(f"Extractor error for pattern {pattern}: {e}")

        logger.info(f"❓ No intent matched for: \"{text}\"")
        return None


class AgentExecutor:
    """
    The central orchestrator. Given a text command:
      1. Parses intent via IntentPlanner
      2. Dispatches to ControlEngine via execute_action()
      3. Generates a human-readable response for TTS
    """

    def __init__(self):
        self.planner = IntentPlanner()

    def process_command(self, text: str) -> dict:
        """
        Process a voice command end-to-end.
        Returns a dict with 'result' and 'speech_response'.
        """
        intent = self.planner.parse(text)

        if intent is None:
            return {
                "status": "no_match",
                "speech_response": f"I didn't understand the command: {text}. Could you try rephrasing?",
                "result": None,
            }

        action_name, kwargs = intent
        result = execute_action(action_name, **kwargs)

        speech = self._generate_response(action_name, kwargs, result)

        return {
            "status": result.get("status", "unknown"),
            "action": action_name,
            "result": result,
            "speech_response": speech,
        }

    def _generate_response(self, action: str, kwargs: dict, result: dict) -> str:
        """Build a natural-language response based on action result."""
        status = result.get("status", "error")

        if status == "blocked":
            return "That command was blocked by the security policy. I can't execute that."

        if status == "error":
            msg = result.get("message", "An unknown error occurred.")
            return f"Sorry, I hit an issue: {msg}"

        if status == "timeout":
            return "The command timed out before completing."

        # Success responses
        if action == "open_app":
            return f"Opening {kwargs.get('app_name', 'the application')}."
        elif action == "close_app":
            return f"Closing {kwargs.get('app_name', 'the application')}."
        elif action == "list_apps":
            apps = result if isinstance(result, list) else []
            return f"There are {len(apps)} applications running."
        elif action == "shell":
            stdout = result.get("stdout", "")
            if stdout:
                return f"Command completed. Output: {stdout[:200]}"
            return "Command executed successfully."
        elif action == "search_files":
            files = result if isinstance(result, list) else []
            if files:
                return f"Found {len(files)} files. First result: {os.path.basename(files[0])}"
            return "No files found matching that query."
        elif action == "set_volume":
            return f"Volume set to {kwargs.get('level', '?')} percent."
        elif action == "lock_screen":
            return "Locking the screen now."
        elif action == "open_url":
            return f"Opening the URL in your browser."
        elif action == "google_search":
            return f"Searching Google for: {kwargs.get('query', '')}"
        elif action == "notify":
            return f"Reminder set: {kwargs.get('message', '')}"

        return "Done."


# Need os for basename in _generate_response
import os

# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor = AgentExecutor()

    test_commands = [
        "Open VS Code",
        "Set volume to 50",
        "Search for file requirements.txt",
        "Google what is the weather today",
        "Run command ls -la",
        "Lock the screen",
        "This is gibberish blah blah",
    ]

    for cmd in test_commands:
        print(f"\n📝 Command: \"{cmd}\"")
        response = executor.process_command(cmd)
        print(f"   → Speech: {response['speech_response']}")
        print(f"   → Status: {response['status']}")
