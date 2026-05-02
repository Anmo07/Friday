#!/usr/bin/env python3
import asyncio
import sys
import json
import threading
import tempfile
import os
import time
import httpx
import logging
from pathlib import Path
from enum import Enum

# Determine directories
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import rumps
from AppKit import (
    NSWindow, NSView, NSColor, NSBackingStoreBuffered, NSScreen, NSImage, NSImageView,
    NSWindowStyleMaskBorderless, NSFont, NSTextField, NSTextAlignmentCenter,
    NSVisualEffectView, NSVisualEffectMaterialDark, NSVisualEffectBlendingModeBehindWindow,
    NSWindowLevel, NSAnimationContext, NSFontWeightMedium
)

from friday.core.pipeline import FridayPipeline
from friday.core.startup_validation import validate_startup

# Configure Logging
log_dir = ROOT / "logs"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(filename=str(log_dir / "menubar.log"), level=logging.INFO)

class FridayState(Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    CAPTURED = "CAPTURED"
    PROCESSING = "PROCESSING"
    RESPONDING = "RESPONDING"

class SiriResponseWindow(NSWindow):
    """Floating Siri-style overlay with Glassmorphism."""
    def initWithContentRect_styleMask_backing_defer_(self, rect, style, backing, defer):
        self = super().initWithContentRect_styleMask_backing_defer_(rect, style, backing, defer)
        if self:
            self.setOpaque_(False)
            self.setBackgroundColor_(NSColor.clearColor())
            self.setLevel_(NSWindowLevel + 1)
            self.setHasShadow_(True)
            self.setIgnoresMouseEvents_(True)
            
            # Visual Effect (Blur)
            self.blur = NSVisualEffectView.alloc().init()
            self.blur.setMaterial_(NSVisualEffectMaterialDark)
            self.blur.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
            self.blur.setWantsLayer_(True)
            self.blur.layer().setCornerRadius_(25.0)
            self.setContentView_(self.blur)
            
            # Reactive Text Label
            self.label = NSTextField.alloc().initWithFrame_(((20, 20), (360, 100)))
            self.label.setEditable_(False)
            self.label.setSelectable_(False)
            self.label.setBordered_(False)
            self.label.setDrawsBackground_(False)
            self.label.setTextColor_(NSColor.whiteColor())
            self.label.setFont_(NSFont.systemFontOfSize_weight_(18, NSFontWeightMedium))
            self.label.setAlignment_(NSTextAlignmentCenter)
            self.label.setStringValue_("")
            self.blur.addSubview_(self.label)
            
        return self

class FridayMenuBar(rumps.App):
    def __init__(self):
        icon_path = ROOT / "friday" / "assets" / "orb_icon_processed.png"
        super().__init__("FRIDAY", icon=str(icon_path) if icon_path.exists() else None)
        
        self.state = FridayState.IDLE
        self.pipeline = FridayPipeline()
        self.loop = asyncio.new_event_loop()
        self.listening = True
        
        self.menu = [
            "Neural Status: Active",
            None,
            rumps.MenuItem("Capture Voice Profile", callback=self.enroll_voice),
            rumps.MenuItem("Reset Neural Context", callback=self.clear_memory),
            None,
            "Quit"
        ]
        
        self._setup_native_overlay()
        
        # Start backend thread
        self.bg_thread = threading.Thread(target=self.start_backend)
        self.bg_thread.daemon = True
        self.bg_thread.start()

    def _setup_native_overlay(self):
        screen = NSScreen.mainScreen().visibleFrame()
        sw, sh = screen.size.width, screen.size.height
        
        width, height = 400, 140
        rect = ((sw/2 - width/2, 100), (width, height))
        
        self.window = SiriResponseWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False
        )
        
        self.orb_view = NSImageView.alloc().initWithFrame_(((width/2 - 40, 60), (80, 80)))
        icon_path = ROOT / "friday" / "assets" / "orb_icon_processed.png"
        if icon_path.exists():
            img = NSImage.alloc().initByReferencingFile_(str(icon_path))
            self.orb_view.setImage_(img)
        
        self.window.contentView().addSubview_(self.orb_view)
        self.window.setAlphaValue_(0.0)
        self.window.orderFrontRegardless()

    def start_backend(self):
        try:
            asyncio.run(validate_startup())
            asyncio.set_event_loop(self.loop)
            self.start_acoustic_monitor()
            self.loop.run_forever()
        except Exception as e:
            logging.error(f"Backend Crash: {e}")

    def start_acoustic_monitor(self):
        from friday.app.voice.listener import listener
        async def run_listener():
            try:
                self.state = FridayState.LISTENING
                await listener.start(self.process_audio)
                while True: await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Monitor error: {e}")
        asyncio.run_coroutine_threadsafe(run_listener(), self.loop)

    async def process_audio(self, audio_bytes: bytes):
        if not self.listening: return
        self.state = FridayState.CAPTURED
        try:
            from friday.app.voice.stt_service import stt_service
            text = await stt_service.transcribe(audio_bytes)
            if text and text.strip():
                await self.execute_pipeline(text)
            else:
                self.state = FridayState.LISTENING
        except Exception as e:
            self.state = FridayState.LISTENING

    async def execute_pipeline(self, text: str):
        self.state = FridayState.PROCESSING
        self.window.animator().setAlphaValue_(1.0)
        self.window.label.setStringValue_("Thinking...")
        
        try:
            from friday.app.voice.tts_service import tts_service
            full_response, current_sentence = "", ""
            audio_queue = asyncio.Queue()

            async def audio_worker():
                while True:
                    sentence = await audio_queue.get()
                    if sentence is None: break
                    audio_res = await tts_service.get_audio(sentence.strip())
                    if audio_res:
                        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                            tmp.write(audio_res); tmp_p = tmp.name
                        self.state = FridayState.RESPONDING
                        proc = await asyncio.create_subprocess_exec("afplay", tmp_p)
                        await proc.wait(); os.unlink(tmp_p)
                    audio_queue.task_done()

            worker = asyncio.create_task(audio_worker())
            
            self.window.label.setStringValue_("")
            async for chunk in self.pipeline.stream_run(text, voice_mode=True):
                if chunk.startswith("event: token"):
                    data = json.loads(chunk.split("data: ")[1])
                    token = data.get("t", "")
                    full_response += token; current_sentence += token
                    
                    self.window.label.setStringValue_(full_response)
                    
                    if any(p in current_sentence for p in [". ", "! ", "? "]):
                        parts = current_sentence.split(". ", 1)
                        await audio_queue.put(parts[0] + ". ")
                        current_sentence = parts[1] if len(parts) > 1 else ""
            
            if current_sentence.strip(): await audio_queue.put(current_sentence)
            await audio_queue.put(None); await worker
        except Exception as e:
            logging.error(f"Pipeline Error: {e}")
        finally:
            await asyncio.sleep(2.0)
            self.state = FridayState.LISTENING
            self.window.animator().setAlphaValue_(0.0)

    def enroll_voice(self, _):
        from friday.app.voice.listener import listener
        async def _enroll():
            self.window.animator().setAlphaValue_(1.0)
            self.window.label.setStringValue_("Recording voice profile... speak now.")
            await listener.capture_user_profile(duration=5)
            self.window.label.setStringValue_("Profile captured. Friday is now secured.")
            await asyncio.sleep(2)
            self.window.animator().setAlphaValue_(0.0)
        asyncio.run_coroutine_threadsafe(_enroll(), self.loop)

    def clear_memory(self, _):
        self.pipeline.reset_memory()
        rumps.notification("Friday", "Neural Context Reset", "Memory cleared.")

if __name__ == "__main__":
    FridayMenuBar().run()