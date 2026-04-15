"""
Friday System — Master Orchestrator (Phase 45 / Main Entry)
=============================================================
The central nervous system that wires together:
  - Audio Activation Engine  (Phase 36)
  - Speech Processing        (Phase 37)
  - System Control Engine     (Phase 38)
  - Agent Executor            (Phase 39)
  - Memory Engine             (Phase 40)
  - Security Layer            (Phase 41)
  - Event Daemon              (Phase 43)
  - Workflow Engine           (Phase 44)
  - Multi-Modal Input         (Phase 45)

Supports Voice, Text, and API input modes simultaneously.

Usage:
  python -m system.friday_orchestrator
"""

import asyncio
import threading
import time
import logging
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from system.audio_engine import AudioActivationEngine
from system.speech_engine import SpeechToText, TextToSpeech, VoiceCommandCapture
from system.agent_executor import AgentExecutor
from system.memory_engine import (
    log_command, get_recent_commands, predict_next_action,
    set_preference, get_preference, SessionContext,
)
from system.security_layer import validate_command
from system.event_daemon import create_default_daemon
from system.workflow_engine import workflow_engine

logger = logging.getLogger("friday")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WAKE_WORD = "friday"
GREETING = "Friday online. How can I help you?"
FAREWELL = "Going silent. Double-clap or say Friday to wake me."
CONFIRM_PROMPT = "That requires elevated permissions. Should I proceed? Say yes or no."


class FridayOrchestrator:
    """
    The unified runtime for the Friday assistant.
    Manages the full lifecycle: Activation → Listen → Plan → Execute → Respond.
    """

    def __init__(self, enable_voice: bool = True, enable_text: bool = True):
        self.enable_voice = enable_voice
        self.enable_text = enable_text

        # Core engines
        self.stt = SpeechToText(model_size="base")
        self.tts = TextToSpeech(voice="Samantha", rate=190)
        self.capture = VoiceCommandCapture(self.stt, duration=5)
        self.agent = AgentExecutor()
        self.session = SessionContext()

        # Audio activation
        self.audio_engine = AudioActivationEngine(
            on_activate=self._on_activation,
            enable_clap=True,
            enable_wake_word=True,
        ) if enable_voice else None

        # Event daemon
        self.daemon = create_default_daemon()

        # State
        self._active_session = False
        self._running = False

    # -------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------

    def start(self):
        """Start all Friday subsystems."""
        self._running = True
        logger.info("=" * 60)
        logger.info("  FRIDAY AUTONOMOUS SYSTEM ASSISTANT")
        logger.info("  Audio: %s | Text: %s", self.enable_voice, self.enable_text)
        logger.info("=" * 60)

        # Start event daemon
        self.daemon.start()

        # Start audio listener
        if self.audio_engine:
            self.audio_engine.start()

        self.tts.speak(GREETING)

        # If text mode is enabled, run the text REPL in the main thread
        if self.enable_text:
            self._text_repl()
        else:
            # Voice-only mode: just keep alive
            try:
                while self._running:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pass

        self.stop()

    def stop(self):
        """Gracefully shut down all subsystems."""
        self._running = False
        if self.audio_engine:
            self.audio_engine.stop()
        self.daemon.stop()
        self.tts.speak("Friday shutting down. Goodbye.")
        time.sleep(2)
        logger.info("Friday stopped.")

    # -------------------------------------------------------------------
    # Activation Handler (called from audio engine background thread)
    # -------------------------------------------------------------------

    def _on_activation(self, trigger_source: str):
        """
        Called when double-clap or wake word is detected.
        Records audio, transcribes, and processes the command.
        """
        if self._active_session:
            return  # Prevent re-entrant activation

        self._active_session = True
        logger.info(f"Activation via [{trigger_source}]")

        self.tts.speak("Yes?")
        time.sleep(0.8)

        # Capture the voice command
        text = self.capture.capture_and_transcribe()

        if text:
            self._process_input(text, source="voice")
        else:
            self.tts.speak("I didn't catch that. Try again.")

        self._active_session = False

    # -------------------------------------------------------------------
    # Multi-Modal Input Processing (Phase 45)
    # -------------------------------------------------------------------

    def _process_input(self, text: str, source: str = "text"):
        """
        Unified input handler for all modalities: voice, text, API.
        """
        logger.info(f"[{source}] Input: \"{text}\"")
        self.session.add_turn("user", text)

        # Check for exit commands
        lower = text.lower().strip()
        if lower in ("exit", "quit", "stop", "goodbye", "bye"):
            self.tts.speak(FAREWELL)
            self._running = False
            return

        # Check for workflow match first (Phase 44)
        wf = workflow_engine.find_workflow(text)
        if wf:
            self.tts.speak(f"Starting workflow: {wf.name}")
            time.sleep(0.5)

            def on_step(current, total, desc):
                self.tts.speak(f"Step {current} of {total}: {desc}")

            result = workflow_engine.execute_workflow(wf, on_step=on_step)
            summary = f"Workflow {wf.name} {result['status']}."
            self.tts.speak(summary)
            self.session.add_turn("assistant", summary)
            log_command(text, f"workflow:{wf.name}", {}, result["status"], summary)
            return

        # Standard single-command processing (Phase 39)
        response = self.agent.process_command(text)

        action = response.get("action", "")
        status = response.get("status", "unknown")
        speech = response.get("speech_response", "Done.")

        # Elevation check for shell commands
        if status == "no_match":
            # Attempt to interpret as a direct shell command
            validation = validate_command(text)
            if validation.get("needs_confirmation"):
                self.tts.speak(CONFIRM_PROMPT)
                time.sleep(1.5)

                # Listen for confirmation
                if source == "voice":
                    confirm_text = self.capture.capture_and_transcribe()
                else:
                    confirm_text = input("Confirm (yes/no): ")

                if confirm_text and "yes" in confirm_text.lower():
                    from system.control_engine import run_shell_command
                    result = run_shell_command(text)
                    speech = f"Command executed. Exit code: {result.get('exit_code', '?')}"
                    status = result.get("status", "error")
                else:
                    speech = "Cancelled."
                    status = "cancelled"

        self.tts.speak(speech)
        self.session.add_turn("assistant", speech)

        # Log to persistent memory (Phase 40)
        kwargs = response.get("result", {}) if isinstance(response.get("result"), dict) else {}
        log_command(text, action, kwargs, status, speech)

        # Prediction (Phase 40)
        predicted = predict_next_action()
        if predicted:
            logger.debug(f"Predicted next action: {predicted}")

    # -------------------------------------------------------------------
    # Text REPL (for terminal-based interaction)
    # -------------------------------------------------------------------

    def _text_repl(self):
        """Interactive text-based command loop."""
        print("\n" + "=" * 50)
        print("  FRIDAY — Text Mode Active")
        print("  Type commands or say 'exit' to quit.")
        print("=" * 50 + "\n")

        try:
            while self._running:
                try:
                    user_input = input("Friday > ").strip()
                except EOFError:
                    break

                if not user_input:
                    continue

                self._process_input(user_input, source="text")
                print()

        except KeyboardInterrupt:
            print("\n")


# ---------------------------------------------------------------------------
# WebSocket Bridge — connects Friday to the existing Veritas UI overlay
# ---------------------------------------------------------------------------

async def friday_ws_handler(websocket):
    """
    Phase 42 bridge: accepts commands from the Electron/Tauri UI overlay
    via WebSocket and returns structured responses.
    """
    orchestrator = FridayOrchestrator(enable_voice=False, enable_text=False)
    agent = orchestrator.agent

    async for message in websocket:
        import json
        try:
            payload = json.loads(message)
            text = payload.get("command", "")
        except (json.JSONDecodeError, AttributeError):
            text = str(message)

        if not text.strip():
            await websocket.send(json.dumps({"error": "Empty command"}))
            continue

        # Process through the agent
        response = agent.process_command(text)

        await websocket.send(json.dumps({
            "status": response.get("status"),
            "action": response.get("action"),
            "speech": response.get("speech_response"),
            "result": response.get("result") if isinstance(response.get("result"), dict) else {},
        }))


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    import argparse
    parser = argparse.ArgumentParser(description="Friday Autonomous System Assistant")
    parser.add_argument("--voice-only", action="store_true", help="Voice-only mode (no text REPL)")
    parser.add_argument("--text-only", action="store_true", help="Text-only mode (no microphone)")
    args = parser.parse_args()

    enable_voice = not args.text_only
    enable_text = not args.voice_only

    friday = FridayOrchestrator(enable_voice=enable_voice, enable_text=enable_text)
    friday.start()


if __name__ == "__main__":
    main()
