import asyncio
import sys
import json
import threading
import tempfile
import os
import time
import warnings
from enum import Enum
from datetime import datetime

# Determine directories
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)
sys.path.insert(0, PACKAGE_DIR)
sys.path.insert(0, PROJECT_ROOT)

import logging
log_dir = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_dir, "menubar.log"), level=logging.INFO)

for logger_name in ["semantic_router", "transformers", "huggingface_hub", "httpcore", "httpx", "openai"]:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

warnings.filterwarnings("ignore")

import rumps
from AppKit import NSWindow, NSView, NSColor, NSBackingStoreBuffered, NSScreen, NSImage, NSImageView, NSWindowStyleMaskBorderless, NSLayoutAttributeCenterX, NSLayoutAttributeCenterY, NSLayoutConstraint
from core.pipeline import FridayPipeline
from core.startup_validation import validate_startup

class FridayState(Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    CAPTURED = "CAPTURED"
    PROCESSING = "PROCESSING"
    RESPONDING = "RESPONDING"

class FridayOverlayView(NSView):
    def drawRect_(self, rect):
        pass # Animation handled by layer

class FridayMenuBarApp(rumps.App):
    def __init__(self):
        icon_path = os.path.join(PACKAGE_DIR, "assets", "orb_icon_processed.png")
        super(FridayMenuBarApp, self).__init__("FRIDAY", icon=icon_path if os.path.exists(icon_path) else None)
        
        # State & Backend
        self.state = FridayState.IDLE
        self.pipeline = FridayPipeline()
        self.loop = asyncio.new_event_loop()
        self.listening = True
        self.title = None
        
        # UI References
        self.status_item = rumps.MenuItem("Neural Status: Active", callback=None)
        self.signal_item = rumps.MenuItem("Neural Signal: Init...", callback=None)
        
        self.menu = [
            self.status_item,
            self.signal_item,
            None,
            rumps.MenuItem("Start at Login", callback=self.toggle_login_item),
            rumps.MenuItem("Pause Acoustic Monitor", callback=self.toggle_listening),
            rumps.MenuItem("Reset Neural Context", callback=self.clear_memory),
            None,
            rumps.MenuItem("Friday Intelligence v0.2.0", callback=self.about),
        ]
        
        # Timer for real-time acoustic signal monitoring
        self.debug_timer = rumps.Timer(self._update_debug_text, 0.4)
        self.debug_timer.start()

    def _update_debug_text(self, _):
        from app.voice.listener import listener
        try:
            cur = int(getattr(listener, "current_rms", 0))
            amb = int(getattr(listener, "ambient_rms_rolling", 0))
            self.signal_item.title = f"Neural Signal: {cur} / {amb}"
        except: pass
        
        # Initialize Native Overlay
        self._setup_native_overlay()
        
        # Start background thread
        self.bg_thread = threading.Thread(target=self.start_backend)
        self.bg_thread.daemon = True
        self.bg_thread.start()

    def _setup_native_overlay(self):
        screen = NSScreen.mainScreen().frame()
        sw, sh = screen.size.width, screen.size.height
        
        # Circular window
        rect = ((sw - 160, 40), (120, 120))
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False
        )
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(NSColor.clearColor())
        self.window.setHasShadow_(True)
        self.window.setLevel_(3) # Topmost
        
        # Content view with Orb
        self.view = NSImageView.alloc().init()
        icon_path = os.path.join(PACKAGE_DIR, "assets", "orb_icon_processed.png")
        if os.path.exists(icon_path):
            img = NSImage.alloc().initByReferencingFile_(icon_path)
            self.view.setImage_(img)
        
        self.window.setContentView_(self.view)
        self.window.setAlphaValue_(0.0)
        self.window.orderFrontRegardless()

    def _update_ui(self, active=True):
        from app.voice.listener import listener
        def _animate():
            target_alpha = 0.9 if active else 0.0
            self.window.animator().setAlphaValue_(target_alpha)
            
            if active:
                # Siri-like Audio-Visual Binding: Reactive to real-time volume
                rms_norm = min(listener.current_rms / 5000.0, 1.0)
                scale = 1.0 + (rms_norm * 0.4) # Grow up to 140%
                
                # Apply scale and opacity modulation
                self.view.setAlphaValue_(0.7 + 0.3 * rms_norm)
                
                if self.state == FridayState.PROCESSING:
                    # Neural Pulse animation
                    self.view.setAlphaValue_(0.5 + 0.4 * abs(time.time() % 1 - 0.5))
                elif self.state == FridayState.RESPONDING:
                    # Shimmer animation
                    self.view.setAlphaValue_(0.8 + 0.2 * abs(time.time() % 0.4 - 0.2))
        
        rumps.Timer(lambda _: _animate(), 0.05).start()

    def start_backend(self):
        try:
            asyncio.run(validate_startup())
            asyncio.set_event_loop(self.loop)
            _ = self.pipeline
            self.start_acoustic_monitor()
            self.loop.run_forever()
        except Exception as e:
            logging.error(f"Backend Crash: {e}")

    def start_acoustic_monitor(self):
        from app.voice.listener import listener
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
        self._update_ui(True)
        try:
            from app.voice.stt_service import stt_service
            text = await stt_service.transcribe(audio_bytes)
            if text and text.strip():
                await self.execute_pipeline(text)
            else:
                self.state = FridayState.LISTENING
                self._update_ui(False)
        except Exception as e:
            self.state = FridayState.LISTENING
            self._update_ui(False)

    async def execute_pipeline(self, text: str):
        self.state = FridayState.PROCESSING
        try:
            from app.voice.tts_service import tts_service
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
            async for chunk in self.pipeline.stream_run(text, voice_mode=True):
                if chunk.startswith("event: token"):
                    data = json.loads(chunk.split("data: ")[1])
                    token = data.get("t", "")
                    full_response += token; current_sentence += token
                    if any(p in current_sentence for p in [". ", "! ", "? "]):
                        parts = current_sentence.split(". ", 1)
                        await audio_queue.put(parts[0] + ". ")
                        current_sentence = parts[1] if len(parts) > 1 else ""
            
            if current_sentence.strip(): await audio_queue.put(current_sentence)
            await audio_queue.put(None); await worker
        except Exception as e: logging.error(f"Pipeline Error: {e}")
        finally:
            self.state = FridayState.LISTENING
            self._update_ui(False)

    def toggle_listening(self, sender):
        self.listening = not self.listening
        sender.title = "Resume Monitor" if not self.listening else "Pause Monitor"
        self.state = FridayState.IDLE if not self.listening else FridayState.LISTENING

    def clear_memory(self, _):
        self.pipeline.reset_memory()
        rumps.notification("Friday", "Neural Context Reset", "The assistant's short-term memory has been cleared.")

    def toggle_login_item(self, sender):
        sender.state = not sender.state
        app_path = os.path.join(PROJECT_ROOT, "run_project.sh") # Use the orchestrator
        if sender.state:
            cmd = f'osascript -e "tell application \\"System Events\\" to make login item at end with properties {{path:\\"{app_path}\\", name:\\"FridayAI\\", hidden:false}}"'
        else:
            cmd = 'osascript -e "tell application \\"System Events\\" to delete login item \\"FridayAI\\""'
        
        try:
            os.system(cmd)
            rumps.notification("Friday", "Login Items Updated", f"Automatic startup is now {'enabled' if sender.state else 'disabled'}.")
        except Exception as e:
            logging.error(f"Login item error: {e}")

    def about(self, _):
        rumps.alert("FRIDAY Tahoe Edition", "Trigger: Say 'Friday' or Double Clap.")

def main():
    FridayMenuBarApp().run()

if __name__ == "__main__":
    main()
