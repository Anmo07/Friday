#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import subprocess
import sys
import tempfile
import threading
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import httpx
import objc
import rumps
import math
from Quartz import (
    CABasicAnimation,
    CAMediaTimingFunction,
    kCAMediaTimingFunctionEaseInEaseOut,
)
from AppKit import (
    NSBackingStoreBuffered,
    NSColor,
    NSFont,
    NSFontWeightMedium,
    NSFontWeightRegular,
    NSImage,
    NSImageView,
    NSLineBreakByWordWrapping,
    NSScreen,
    NSTextAlignmentCenter,
    NSTextField,
    NSVisualEffectBlendingModeBehindWindow,
    NSVisualEffectMaterialSidebar,
    NSVisualEffectView,
    NSWindow,
    NSStatusWindowLevel,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskFullSizeContentView,
)
from Quartz import (
    CAGradientLayer,
    CALayer,
    kCAGravityCenter,
)
from PyObjCTools.AppHelper import callAfter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "friday"))

import nest_asyncio
nest_asyncio.apply()

from friday.app.core.config import settings
from friday.app.voice.listener import listener
from friday.app.voice.stt_service import stt_service
from friday.app.voice.tts_service import tts_service
from friday.core.startup_validation import validate_startup

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
# Clear existing handlers to ensure our basicConfig takes effect
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    filename=str(LOG_DIR / "menubar.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class FridayState(Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    CAPTURED = "CAPTURED"
    PROCESSING = "PROCESSING"
    RESPONDING = "RESPONDING"
    LOCKED = "LOCKED"


class SiriResponseWindow(NSWindow):
    def initWithContentRect_styleMask_backing_defer_(self, rect, style, backing, defer):
        self = objc.super(SiriResponseWindow, self).initWithContentRect_styleMask_backing_defer_(
            rect, style, backing, defer
        )
        if self:
            self.setOpaque_(False)
            self.setBackgroundColor_(NSColor.clearColor())
            self.setLevel_(NSStatusWindowLevel + 1)
            self.setHasShadow_(True)
            self.setIgnoresMouseEvents_(True)
            self.setMovableByWindowBackground_(False)
            self.setCollectionBehavior_(1 << 0 | 1 << 6)  # NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary

            # Liquid Glass Effect View
            self.blur = NSVisualEffectView.alloc().init()
            self.blur.setMaterial_(NSVisualEffectMaterialSidebar)
            self.blur.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
            self.blur.setState_(1)  # NSVisualEffectStateActive
            self.blur.setWantsLayer_(True)
            self.blur.layer().setCornerRadius_(28.0)
            self.blur.layer().setMasksToBounds_(True)
            self.blur.layer().setBorderWidth_(0.5)
            self.blur.layer().setBorderColor_(NSColor.colorWithWhite_alpha_(1.0, 0.2).CGColor())
            
            # Subtle Gloss/Liquid Gradient
            self.gloss = CAGradientLayer.layer()
            self.gloss.setColors_([
                NSColor.colorWithWhite_alpha_(1.0, 0.1).CGColor(),
                NSColor.colorWithWhite_alpha_(1.0, 0.0).CGColor(),
                NSColor.colorWithWhite_alpha_(1.0, 0.05).CGColor(),
            ])
            self.gloss.setLocations_([0.0, 0.5, 1.0])
            self.blur.layer().addSublayer_(self.gloss)
            
            self.setContentView_(self.blur)

            # Responsive Text Label
            self.label = NSTextField.alloc().initWithFrame_(((30, 20), (420, 40)))
            self.label.setEditable_(False)
            self.label.setSelectable_(False)
            self.label.setBordered_(False)
            self.label.setDrawsBackground_(False)
            self.label.setTextColor_(NSColor.whiteColor())
            self.label.setFont_(NSFont.systemFontOfSize_weight_(19, NSFontWeightRegular))
            self.label.setAlignment_(NSTextAlignmentCenter)
            self.label.setLineBreakMode_(NSLineBreakByWordWrapping)
            self.label.setUsesSingleLineMode_(False)
            self.label.cell().setWraps_(True)
            self.label.setStringValue_("")
            self.blur.addSubview_(self.label)
        return self

    def layout(self):
        super().layout()
        if hasattr(self, "gloss"):
            self.gloss.setFrame_(self.blur.bounds())


class FridayMenuBar(rumps.App):
    def __init__(self):
        icon_path = ROOT / "friday" / "assets" / "orb_icon_processed.png"
        super().__init__("FRIDAY", icon=str(icon_path) if icon_path.exists() else None, quit_button=None)

        self.state = FridayState.IDLE
        self.loop = asyncio.new_event_loop()
        self.background_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.response_lock = asyncio.Lock()
        self.client: httpx.AsyncClient | None = None
        self.backend_process: subprocess.Popen | None = None
        self.backend_log_handle = None
        self.backend_started_here = False
        self.listening_enabled = True

        self.api_base_url = settings.PUBLIC_API_BASE_URL.rstrip("/")
        self.api_key = os.getenv("FRIDAY_API_KEY") or os.getenv("VERITAS_DEV_API_KEY")

        self.status_item = rumps.MenuItem("Neural Status: Starting")
        self.security_item = rumps.MenuItem("Voice Profile: Checking")
        self.listening_item = rumps.MenuItem(
            "Pause Acoustic Monitor", callback=self.toggle_listening
        )

        self.menu = [
            rumps.MenuItem("Force Trigger (Debug)", callback=self.force_trigger),
            None,
            self.status_item,
            self.security_item,
            None,
            rumps.MenuItem("Capture Voice Profile", callback=self.enroll_voice),
            self.listening_item,
            rumps.MenuItem("Reset Overlay", callback=self.reset_overlay),
            None,
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]

        self._setup_native_overlay()
        self.background_thread.start()

    def _setup_native_overlay(self):
        screen = NSScreen.mainScreen().visibleFrame()
        self.default_width = 480
        self.min_height = 140
        rect = (
            (screen.origin.x + screen.size.width / 2 - self.default_width / 2, screen.origin.y + 100),
            (self.default_width, self.min_height),
        )

        self.window = SiriResponseWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )

        # Orb at the top
        self.orb_view = NSImageView.alloc().initWithFrame_(((self.default_width / 2 - 35, self.min_height - 65), (70, 70)))
        icon_path = ROOT / "friday" / "assets" / "orb_icon_processed.png"
        if icon_path.exists():
            image = NSImage.alloc().initByReferencingFile_(str(icon_path))
            self.orb_view.setImage_(image)
        
        self.orb_view.setWantsLayer_(True)
        self.window.contentView().addSubview_(self.orb_view)
        self.window.setAlphaValue_(0.0)
        self.window.orderFrontRegardless()

    def _run_loop(self):
        """Main entry point for the background thread's event loop."""
        asyncio.set_event_loop(self.loop)
        # nest_asyncio is critical for supporting nested loops (e.g. within certain libraries)
        nest_asyncio.apply(self.loop)
        
        self.loop.create_task(self._bootstrap())
        try:
            self.loop.run_forever()
        except Exception as e:
            logger.error(f"Event loop died: {e}", exc_info=True)

    def force_trigger(self, _):
        logger.info("Manual trigger activated via Menu Bar.")
        asyncio.run_coroutine_threadsafe(self._force_trigger_task(), self.loop)

    async def _force_trigger_task(self):
        self._set_state(FridayState.PROCESSING)
        self._set_overlay_text("I'm listening...")
        self._set_overlay_visible(True)
        await self.execute_pipeline("hello friday")

    async def _bootstrap(self):
        """Initializes the backend, validates services, and starts the acoustic monitor."""
        if hasattr(self, "_bootstrapping") and self._bootstrapping:
            return
        self._bootstrapping = True
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=4.0, read=None, write=30.0, pool=5.0)
        )
        try:
            # 1. Validate Ollama and local models
            success = await validate_startup()
            if not success:
                logger.error("Startup validation failed.")
                return

            # 2. Sync with Backend (Auto-start if needed)
            await self._ensure_backend_ready()
            
            # 3. Ignite Acoustic Monitor
            listener.energy_threshold = 200 # Lowered energy threshold
            if not listener.is_running:
                await listener.start(self.process_audio)
            
            self._set_state(
                FridayState.LISTENING
            )
            self._update_security_status(listener.has_voice_profile)
            logger.info("Friday Engine is now fully operational.")
            
            # Diagnostic: Check for dead mic
            if listener.current_rms < 10 and not listener.is_running:
                 logger.warning("Microphone seems silent (RMS < 10). Check permissions.")
        except Exception as exc:
            logger.error("Engine failure during bootstrap: %s", exc, exc_info=True)
            self._set_overlay_text("Engine failure.")
            self._set_overlay_visible(True)
            rumps.notification("Friday Engine", "Bootstrap Error", str(exc)[:120])
        finally:
            self._bootstrapping = False

    async def _ensure_backend_ready(self):
        if await self._backend_healthcheck():
            return

        parsed = urlparse(self.api_base_url)
        if parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise RuntimeError(
                f"Friday backend is unreachable at {self.api_base_url} and cannot be auto-started for a non-local host."
            )

        port = self._pick_available_port(parsed.hostname or "127.0.0.1", parsed.port or 8001)
        host_for_url = parsed.hostname or "127.0.0.1"
        self.api_base_url = self._replace_url_port(self.api_base_url, host_for_url, port)

        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ROOT), str(ROOT / "friday"), env.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        if not self.api_key:
            env["ALLOW_ANONYMOUS_QUERY_ENDPOINT"] = "true"
        env["FRIDAY_PARENT_PID"] = str(os.getpid())

        self.backend_log_handle = open(LOG_DIR / "backend.log", "a", encoding="utf-8")
        self.backend_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                host_for_url,
                "--port",
                str(port),
            ],
            cwd=str(ROOT / "friday"),
            env=env,
            stdout=self.backend_log_handle,
            stderr=subprocess.STDOUT,
        )
        self.backend_started_here = True
        logger.info("Started local backend at %s.", self.api_base_url)

        for _ in range(40):
            await asyncio.sleep(0.5)
            if await self._backend_healthcheck():
                return

        raise RuntimeError("Local Friday backend did not become healthy in time.")

    async def _backend_healthcheck(self) -> bool:
        if self.client is None:
            return False
        try:
            response = await self.client.get(f"{self.api_base_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    def _pick_available_port(self, host: str, preferred_port: int) -> int:
        for port in range(preferred_port, preferred_port + 10):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if probe.connect_ex((host, port)) != 0:
                    return port
        raise RuntimeError("No free local port was available for the Friday backend.")

    @staticmethod
    def _replace_url_port(url: str, host: str, port: int) -> str:
        parsed = urlparse(url)
        scheme = parsed.scheme or "http"
        netloc = f"{host}:{port}"
        return urlunparse(parsed._replace(scheme=scheme, netloc=netloc)).rstrip("/")

    def _request_headers(self) -> dict[str, str]:
        if self.api_key:
            return {"X-API-KEY": self.api_key}
        return {}

    def _set_state(self, state: FridayState):
        self.state = state
        callAfter(self._set_status_title, f"Neural Status: {state.value.title()}")
        
        # Update menu bar title for quick glance
        status_text = ""
        if state == FridayState.LISTENING: status_text = "󰔊" # Mic icon or similar
        elif state == FridayState.PROCESSING: status_text = "󰑭" # Thinking
        elif state == FridayState.RESPONDING: status_text = "󰓃" # Speaking
        
        # We can also just use text if symbols aren't supported
        titles = {
            FridayState.LISTENING: "FRIDAY (Live)",
            FridayState.PROCESSING: "FRIDAY (Thinking...)",
            FridayState.RESPONDING: "FRIDAY (Speaking...)",
            FridayState.IDLE: "FRIDAY"
        }
        callAfter(self._set_app_title, titles.get(state, "FRIDAY"))

    def _set_app_title(self, title: str):
        self.title = title

    def _set_status_title(self, title: str):
        self.status_item.title = title

    def _update_security_status(self, has_profile: bool):
        status = "Loaded" if has_profile else "Required"
        callAfter(self._set_security_title, f"Voice Profile: {status}")

    def _set_security_title(self, title: str):
        self.security_item.title = title

    def _set_overlay_visible(self, visible: bool):
        def _animate():
            alpha = 1.0 if visible else 0.0
            self.window.animator().setAlphaValue_(alpha)
            if visible:
                self._update_orb_animation()
            else:
                # Reset window size when hiding
                self._update_window_height(self.min_height)

        callAfter(_animate)

    def _update_window_height(self, new_height: float):
        frame = self.window.frame()
        diff = new_height - frame.size.height
        if abs(diff) < 2:
            return
            
        new_origin_y = frame.origin.y - diff / 2 # Expand from center/bottom
        new_frame = ((frame.origin.x, frame.origin.y), (frame.size.width, new_height))
        
        # Adjust orb and label positions
        self.window.setFrame_display_animate_(new_frame, True, True)
        self.orb_view.setFrame_(((self.default_width / 2 - 35, new_height - 65), (70, 70)))
        self.window.label.setFrame_(((30, 25), (420, new_height - 85)))

    def _update_orb_animation(self):
        if not hasattr(self, "orb_view") or not self.orb_view:
            return

        layer = self.orb_view.layer()
        layer.removeAllAnimations()

        if self.state in [FridayState.LISTENING, FridayState.CAPTURED]:
            # Pulsing animation for listening
            pulse = CABasicAnimation.animationWithKeyPath_("transform.scale")
            pulse.setFromValue_(1.0)
            pulse.setToValue_(1.15)
            pulse.setDuration_(0.8)
            pulse.setAutoreverses_(True)
            pulse.setRepeatCount_(float("inf"))
            pulse.setTimingFunction_(
                CAMediaTimingFunction.functionWithName_(kCAMediaTimingFunctionEaseInEaseOut)
            )
            layer.addAnimation_forKey_(pulse, "pulse")
        elif self.state == FridayState.PROCESSING:
            # Subtle glow/pulse for thinking, no rotation
            glow = CABasicAnimation.animationWithKeyPath_("opacity")
            glow.setFromValue_(1.0)
            glow.setToValue_(0.4)
            glow.setDuration_(1.2)
            glow.setAutoreverses_(True)
            glow.setRepeatCount_(float("inf"))
            layer.addAnimation_forKey_(glow, "glow")

    def _set_overlay_text(self, text: str):
        def _update():
            self.window.label.setStringValue_(text)
            
            # Calculate required height
            field_editor = self.window.label.cell().fieldEditorForView_(self.window.label)
            available_size = (420, 1000) # Max height
            ideal_size = self.window.label.cell().cellSizeForBounds_(((0, 0), available_size))
            
            new_height = max(self.min_height, ideal_size.height + 100) # padding for orb
            if new_height > 600: new_height = 600 # Cap height
            
            self._update_window_height(new_height)
            
        callAfter(_update)

    async def process_audio(self, audio_bytes: bytes):
        if not self.listening_enabled:
            return
        if self.response_lock.locked():
            return

        async with self.response_lock:
            logger.info(f"Processing audio utterance ({len(audio_bytes)} bytes)...")
            self._set_state(FridayState.CAPTURED)
            self._set_overlay_text("Transcribing...")
            self._set_overlay_visible(True)

            try:
                text = await stt_service.transcribe(audio_bytes)
                logger.info(f"STT Result: '{text}'")
                
                if not text.strip():
                    logger.info("STT returned empty text. Cancelling interaction.")
                    self._set_state(
                        FridayState.LISTENING
                    )
                    self._set_overlay_visible(False)
                    return
                
                # Check for voice-triggered enrollment
                if any(cmd in text.lower() for cmd in ["enroll my voice", "set up my voice", "identify my voice", "voice setup"]):
                    logger.info("Voice enrollment triggered by voice command.")
                    await self._enroll_voice_profile()
                    return

                # Proactive Enrollment Prompt
                if not listener.has_voice_profile:
                    logger.info("No voice profile found. Prompting for proactive enrollment.")
                    # Acknowledge the query first but then suggest setup
                    # We'll let the pipeline run, but we can also just pivot to setup
                    # Let's pivot to setup if the user is just saying 'hello' or 'hey friday'
                    if len(text.split()) <= 3:
                         self._set_overlay_text("I don't recognize you yet, Boss. Let's set up your voice profile.")
                         self._set_overlay_visible(True)
                         await asyncio.sleep(2.0)
                         await self._enroll_voice_profile()
                         return

                await self.execute_pipeline(text)
            except Exception as exc:
                logger.error("Audio processing failed: %s", exc, exc_info=True)
                self._set_overlay_text("I lost the audio path.")
                await asyncio.sleep(1.5)
                self._set_overlay_visible(False)
                self._set_state(
                    FridayState.LISTENING
                )

    async def execute_pipeline(self, text: str):
        self._set_state(FridayState.PROCESSING)
        self._set_overlay_text("Thinking...")
        self._set_overlay_visible(True)

        phrase_queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=12)
        audio_task = asyncio.create_task(self._audio_worker(phrase_queue))
        full_response = ""
        phrase_buffer = ""

        try:
            async for event_name, payload in self._stream_response_events(text):
                if event_name == "token":
                    token = payload.get("t", "")
                    if not token:
                        continue
                    full_response += token
                    phrase_buffer += token

                    ready_phrases, phrase_buffer = self._split_ready_phrases(
                        phrase_buffer
                    )
                    for phrase in ready_phrases:
                        await phrase_queue.put(phrase)
                elif event_name == "done":
                    break
                elif event_name == "done":
                    break

            ready_phrases, phrase_buffer = self._split_ready_phrases(
                phrase_buffer, flush=True
            )
            for phrase in ready_phrases:
                await phrase_queue.put(phrase)
        except Exception as exc:
            logger.error("Streaming pipeline failed: %s", exc, exc_info=True)
            self._set_overlay_text("Response stream failed.")
        finally:
            await phrase_queue.put(None)
            await audio_task
            await asyncio.sleep(2.0) # Keep visible for a moment after speaking
            self._set_overlay_visible(False)
            self._spoken_text = ""
            
            # Re-enable listener
            listener.enabled = True
            
            await asyncio.sleep(1.2)
            self._set_state(
                FridayState.LISTENING
            )

    async def _stream_response_events(self, query: str):
        if self.client is None:
            raise RuntimeError("HTTP client is not initialized")

        payload = {"query": query, "voice_mode": True}
        headers = self._request_headers()

        async with self.client.stream(
            "POST",
            f"{self.api_base_url}/stream",
            json=payload,
            headers=headers,
        ) as response:
            if response.status_code == 401:
                raise RuntimeError(
                    "Backend rejected the menu bar request. Set VERITAS_DEV_API_KEY or FRIDAY_API_KEY for authenticated backends."
                )
            response.raise_for_status()

            event_name = None
            data_lines: list[str] = []

            async for line in response.aiter_lines():
                if line == "":
                    if event_name and data_lines:
                        raw_payload = "\n".join(data_lines)
                        yield event_name, json.loads(raw_payload)
                    event_name = None
                    data_lines = []
                    continue

                if line.startswith(":"):
                    continue
                if line.startswith("event:"):
                    event_name = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())

    async def _audio_worker(self, phrase_queue: asyncio.Queue[str | None]):
        while True:
            phrase = await phrase_queue.get()
            try:
                if phrase is None:
                    return
                cleaned = phrase.strip()
                if not cleaned:
                    continue

                logger.info(f"Reciting: {cleaned[:50]}...")
                self._set_state(FridayState.RESPONDING)
                
                # Mute listener while speaking
                listener.enabled = False
                
                # Show text in sync with recitation
                self._set_overlay_visible(True)
                current_text = getattr(self, "_spoken_text", "")
                self._spoken_text = current_text + " " + cleaned
                self._set_overlay_text(self._spoken_text)
                
                # Use local TTS directly (bypass network round-trip)
                audio_path = await tts_service.synthesize_to_file(cleaned)
                if not audio_path:
                    # Fallback to network TTS
                    audio_path = await self._fetch_tts_audio(cleaned)
                
                if not audio_path:
                    logger.warning("Failed to fetch TTS audio")
                    continue
                try:
                    # Use afplay but with logging
                    logger.info(f"Playing audio from {audio_path}")
                    process = await asyncio.create_subprocess_exec("afplay", audio_path)
                    await process.wait()
                    logger.info("Playback finished")
                except Exception as e:
                    logger.error(f"Playback failed: {e}")
                finally:
                    try:
                        os.unlink(audio_path)
                    except FileNotFoundError:
                        pass
            finally:
                phrase_queue.task_done()

    async def _fetch_tts_audio(self, text: str) -> str | None:
        if self.client is None:
            return None

        headers = self._request_headers()
        async with self.client.stream(
            "POST",
            f"{self.api_base_url}/voice/stream",
            json={"text": text},
            headers=headers,
        ) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            suffix = ".wav" if "wav" in content_type else ".mp3"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
                async for chunk in response.aiter_bytes():
                    if chunk:
                        handle.write(chunk)
                return handle.name

    @staticmethod
    def _split_ready_phrases(buffer: str, flush: bool = False) -> tuple[list[str], str]:
        ready: list[str] = []
        boundaries = ".?!;:"
        minimum_phrase_length = 24

        while True:
            cut_index = -1
            for idx, char in enumerate(buffer):
                if char in boundaries and idx + 1 >= minimum_phrase_length:
                    cut_index = idx + 1
                    break

            if cut_index == -1:
                break

            ready.append(buffer[:cut_index])
            buffer = buffer[cut_index:].lstrip()

        if flush and buffer.strip():
            ready.append(buffer)
            buffer = ""

        return ready, buffer

    def enroll_voice(self, _):
        logger.info("Voice enrollment requested.")
        asyncio.run_coroutine_threadsafe(self._enroll_voice_profile(), self.loop)

    async def _enroll_voice_profile(self):
        was_running = listener.is_running
        try:
            if was_running:
                await listener.stop()

            self._set_overlay_text(
                "Recording your reference voice. Speak for six seconds."
            )
            self._set_overlay_visible(True)
            await listener.capture_user_profile(duration=6)
            self._update_security_status(True)
            self._set_overlay_text("Voice profile captured.")
            await asyncio.sleep(1.5)
        except Exception as exc:
            logger.error("Voice enrollment failed: %s", exc, exc_info=True)
            self._set_overlay_text("Voice enrollment failed.")
            await asyncio.sleep(1.5)
        finally:
            if self.listening_enabled and not listener.is_running:
                await listener.start(self.process_audio)
            self._set_overlay_visible(False)
            self._set_state(FridayState.LISTENING)

    def toggle_listening(self, sender):
        self.listening_enabled = not self.listening_enabled
        sender.title = (
            "Resume Acoustic Monitor"
            if not self.listening_enabled
            else "Pause Acoustic Monitor"
        )
        target_state = (
            FridayState.IDLE
            if not self.listening_enabled
            else (FridayState.LISTENING)
        )
        self._set_state(target_state)

    def reset_overlay(self, _):
        logger.info("Overlay reset requested.")
        self._set_overlay_text("")
        self._set_overlay_visible(False)

    def quit_app(self, _):
        try:
            future = asyncio.run_coroutine_threadsafe(self._shutdown(), self.loop)
            future.result(timeout=6)
        except Exception as exc:
            logger.warning("Graceful shutdown was incomplete: %s", exc)
        rumps.quit_application()

    async def _shutdown(self):
        try:
            if listener.is_running:
                await listener.stop()
        finally:
            if self.client is not None:
                await self.client.aclose()
                self.client = None

            if self.backend_process is not None and self.backend_started_here:
                self.backend_process.terminate()
                try:
                    await asyncio.to_thread(self.backend_process.wait, 5)
                except Exception:
                    self.backend_process.kill()
                self.backend_process = None

            if self.backend_log_handle is not None:
                self.backend_log_handle.close()
                self.backend_log_handle = None

            self.loop.call_soon(self.loop.stop)


def main():
    FridayMenuBar().run()


if __name__ == "__main__":
    main()
