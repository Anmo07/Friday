import asyncio
import sys
import json
import threading
import tempfile
import os
import subprocess
import warnings
import time
from enum import Enum
from typing import Optional

# Add project root to sys.path to resolve sibling packages
# This ensures that imports like 'core', 'app', 'models' work regardless of where it's launched from
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import logging
logging.getLogger("semantic_router").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore")

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text
from rich.status import Status

console = Console()

from core.pipeline import FridayPipeline
from core.startup_validation import validate_startup
from core.service_registry import service_registry

class FridayState(Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    CAPTURED = "CAPTURED"
    PROCESSING = "PROCESSING"
    RESPONDING = "RESPONDING"

class FridayMenuApp:
    def __init__(self):
        # rumps might not be available in all environments, but we keep it for Mac focus
        try:
            import rumps
            self.has_gui = True
        except ImportError:
            self.has_gui = False
            
        self.state = FridayState.IDLE
        self.layer = FridayPipeline()
        self.loop = asyncio.new_event_loop()
        self.listening = True
        self.current_task = None
        self.current_proc = None
        self.processing_status = None
        
        if self.has_gui:
            import rumps
            self.app = rumps.App("FRIDAY", icon=None, quit_button="Quit FRIDAY")
            self.app.title = "🤖"
            self.status_menu = rumps.MenuItem("Status: Active", callback=None)
            self.toggle_mic_menu = rumps.MenuItem("Pause Listening", callback=self.toggle_mic)
            self.clear_mem_menu = rumps.MenuItem("Clear Context Memory", callback=self.clear_memory)
            self.open_dash_menu = rumps.MenuItem("Open Assistant Dashboard", callback=self.open_dashboard)
            self.open_ctrl_menu = rumps.MenuItem("Open Control Room", callback=self.open_control_room)
            self.app.menu = [
                self.status_menu,
                None,
                self.toggle_mic_menu,
                self.clear_mem_menu,
                None,
                self.open_dash_menu,
                self.open_ctrl_menu,
                None,
            ]
        
        t = threading.Thread(target=self.start_background_loop)
        t.daemon = True
        t.start()

    def _run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start_background_loop(self):
        try:
            with console.status("[bold cyan]Initializing FRIDAY...", spinner="dots"):
                # Run startup validation
                valid = asyncio.run(validate_startup())
                if not valid:
                    console.print("[bold red]Startup validation failed. Please check Ollama and models.[/bold red]")
                    # We continue but in limited mode
                
                asyncio.set_event_loop(self.loop)
                # Force pipeline load
                _ = self.layer
            
            console.clear()
            header = "[bold blue]FRIDAY ONLINE[/bold blue]\n[dim]High-Performance Assistant Engine v0.2.0[/dim]"
            if service_registry.limited_mode:
                header += "\n[bold yellow]⚠️ LIMITED MODE ACTIVE: Some services are offline.[/bold yellow]"
            
            console.print(Panel.fit(header, border_style="cyan"))
            console.print("[dim]Type [bold white]/help[/bold white] for commands or just start talking.[/dim]\n")
            
            loop_thread = threading.Thread(target=self._run_async_loop)
            loop_thread.daemon = True
            loop_thread.start()
            
            terminal_thread = threading.Thread(target=self.terminal_loop)
            terminal_thread.daemon = True
            terminal_thread.start()
            
            self.listen_loop()
        except Exception as e:
            console.print(f"[bold red]Startup Error:[/bold red] {e}")

    def terminal_loop(self):
        while True:
            try:
                user_input = console.input("[bold purple]user[/bold purple] [dim]> [/dim]")
                if not user_input.strip():
                    continue
                
                cmd = user_input.strip().lower()
                if cmd in ["exit", "quit", "stop"]:
                    console.print("[italic yellow]FRIDAY: Shutting down. Goodbye Boss.[/italic yellow]")
                    if self.has_gui:
                        import rumps
                        rumps.quit_application()
                    else:
                        os._exit(0)
                    break
                
                if cmd == "/help":
                    self.show_help()
                    continue

                if cmd == "/clear":
                    console.clear()
                    continue

                if cmd == "/reset":
                    self.clear_memory(None)
                    continue

                # Cancel previous task if a new one starts
                if self.current_task:
                    self.current_task.cancel()
                
                self.current_task = asyncio.run_coroutine_threadsafe(
                    self.process_text(user_input), self.loop
                )
            except (KeyboardInterrupt, EOFError):
                if self.has_gui:
                    import rumps
                    rumps.quit_application()
                else:
                    os._exit(0)
                break
            except Exception as e:
                console.print(f"[bold red]Terminal Input Error:[/bold red] {e}")

    def show_help(self):
        help_text = """
### Available Commands
- **Text Input**: Just type normally to talk to FRIDAY.
- **Voice Input**: Speak anytime (microphone is active).
- `/help`: Show this help message.
- `/clear`: Clear the terminal screen.
- `/reset`: Clear conversation context memory.
- `exit` / `quit`: Shut down FRIDAY.

### State Machine (Live Ear)
- **IDLE**: Waiting for input.
- **LISTENING**: Microphone is active and detecting audio.
- **CAPTURED**: Audio utterance has been recorded.
- **PROCESSING**: Transcribing and thinking.
- **RESPONDING**: Generating and playing audio response.
"""
        console.print(Panel(Markdown(help_text), title="[bold cyan]FRIDAY Help[/bold cyan]", border_style="cyan"))

    def toggle_mic(self, sender):
        self.listening = not self.listening
        if self.listening:
            sender.title = "Pause Listening"
            if self.has_gui:
                self.status_menu.title = "Status: Active"
                self.app.title = "🤖"
            self.state = FridayState.IDLE
            console.print("[italic green]FRIDAY: Listening resumed.[/italic green]")
        else:
            sender.title = "Resume Listening"
            if self.has_gui:
                self.status_menu.title = "Status: Paused"
                self.app.title = "💤"
            console.print("[italic yellow]FRIDAY: Listening paused.[/italic yellow]")

    def clear_memory(self, _):
        self.layer.reset_memory()
        if self.has_gui:
            import rumps
            rumps.notification("FRIDAY", "Memory Cleared", "Conversation context has been reset.")
        console.print("[italic cyan]FRIDAY: Context memory cleared.[/italic cyan]")

    def open_dashboard(self, _):
        subprocess.Popen(["open", "http://localhost:3000/dashboard"])

    def open_control_room(self, _):
        subprocess.Popen(["open", "http://localhost:3000/control"])

    def listen_loop(self):
        """Main voice interaction loop using the custom VoiceListener."""
        from app.voice.listener import listener
        
        # Configure listener calibration
        listener.energy_threshold = 1000.0
        # silence_timeout is now 0.8s by default in the class
        
        async def run_listener():
            try:
                self.state = FridayState.LISTENING
                await listener.start(self.process_audio)
                while True:
                    await asyncio.sleep(1)
            except Exception as e:
                console.print(f"[bold red]Listener Error:[/bold red] {e}")
            finally:
                await listener.stop()

        asyncio.run_coroutine_threadsafe(run_listener(), self.loop)

    async def process_text(self, text: str):
        self.state = FridayState.PROCESSING
        try:
            from app.voice.tts_service import tts_service

            full_response = ""
            current_sentence = ""
            audio_queue = asyncio.Queue()

            async def audio_worker():
                while True:
                    sentence = await audio_queue.get()
                    if sentence is None:
                        audio_queue.task_done()
                        break
                    if sentence.strip():
                        audio_response = await tts_service.get_audio(sentence.strip())
                        if audio_response:
                            with tempfile.NamedTemporaryFile(
                                suffix=".mp3", delete=False
                            ) as tmp:
                                tmp.write(audio_response)
                                tmp_path = tmp.name
                            
                            self.state = FridayState.RESPONDING
                            self.current_proc = await asyncio.create_subprocess_exec(
                                "afplay", tmp_path
                            )
                            await self.current_proc.wait()
                            self.current_proc = None
                            os.unlink(tmp_path)
                            self.state = FridayState.PROCESSING # Back to processing if more sentences
                    audio_queue.task_done()

            worker_task = asyncio.create_task(audio_worker())
            
            console.print("[bold cyan]friday[/bold cyan] [dim]> [/dim]", end="")
            
            with Live(Text(""), refresh_per_second=20, console=console) as live:
                async for chunk in self.layer.stream_run(text, voice_mode=True):
                    if chunk.startswith("event: token"):
                        data = json.loads(chunk.split("data: ")[1])
                        token = data.get("t", "")
                        full_response += token
                        current_sentence += token
                        live.update(Text(full_response))
                        
                    if any(
                        punct in current_sentence
                        for punct in [". ", "! ", "? ", ".\n", "!\n", "?\n"]
                    ):
                        for punct in [". ", "! ", "? ", ".\n", "!\n", "?\n"]:
                            if punct in current_sentence:
                                parts = current_sentence.split(punct, 1)
                                sentence_to_speak = parts[0] + punct
                                current_sentence = parts[1] if len(parts) > 1 else ""
                                await audio_queue.put(sentence_to_speak)
                                break
                
            console.print()
            if current_sentence.strip():
                await audio_queue.put(current_sentence)
            await audio_queue.put(None)
            await worker_task
        except asyncio.CancelledError:
            if self.current_proc:
                try:
                    self.current_proc.terminate()
                except:
                    pass
            console.print("\n[italic yellow][Interrupted][/italic yellow]")
        except Exception as e:
            console.print(f"\n[bold red]Error processing text:[/bold red] {e}")
        finally:
            self.current_task = None
            self.state = FridayState.IDLE

    async def process_audio(self, audio_bytes: bytes):
        if not self.listening:
            return
            
        self.state = FridayState.CAPTURED
        # Show "Processing..." feedback during STT
        with console.status("[bold yellow]Processing...[/bold yellow]", spinner="bouncingBar"):
            try:
                from app.voice.stt_service import stt_service
                text = await stt_service.transcribe(audio_bytes)

                if not text or not text.strip():
                    self.state = FridayState.IDLE
                    return
                
                self.state = FridayState.PROCESSING
                console.print(f"[bold purple]user (voice)[/bold purple] [dim]> [/dim]{text}")
                
                # Handle interruption
                if text.strip().lower() in ["stop", "hold on", "quiet", "shut up"]:
                    if self.current_task:
                        self.current_task.cancel()
                        console.print("[italic yellow]FRIDAY: Stopping as requested.[/italic yellow]")
                    self.state = FridayState.IDLE
                    return

                if text.strip().lower() in ["exit", "quit", "stop listening"]:
                    if self.has_gui:
                        import rumps
                        rumps.quit_application()
                    else:
                        os._exit(0)
                    return
                
                # Cancel previous task if a new one starts
                if self.current_task:
                    self.current_task.cancel()
                
                self.current_task = asyncio.create_task(self.process_text(text))
                await self.current_task
            except Exception as e:
                console.print(f"\n[bold red]Error processing audio:[/bold red] {e}")
                self.state = FridayState.IDLE

    def run(self):
        if self.has_gui:
            self.app.run()
        else:
            # Keep main thread alive if no GUI
            while True:
                time.sleep(1)

def main():
    app = FridayMenuApp()
    app.run()

if __name__ == "__main__":
    main()
