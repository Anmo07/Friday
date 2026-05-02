import asyncio
import sys
import json
import threading
import tempfile
import os
import warnings
import time
from enum import Enum
from typing import Optional, List, Tuple
from datetime import datetime

# Determine directories
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)
sys.path.insert(0, PACKAGE_DIR)
sys.path.insert(0, PROJECT_ROOT)

import logging
log_dir = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_dir, "friday.log"), level=logging.INFO)

for logger_name in ["semantic_router", "transformers", "huggingface_hub", "httpcore", "httpx"]:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

warnings.filterwarnings("ignore")

from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.table import Table
from rich.align import Align
from rich.theme import Theme

console = Console(theme=Theme({"friday": "bold cyan", "user": "bold purple"}))

from core.pipeline import FridayPipeline
from core.startup_validation import validate_startup

class FridayState(Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    CAPTURED = "CAPTURED"
    PROCESSING = "PROCESSING"
    RESPONDING = "RESPONDING"

class FridayMenuApp:
    def __init__(self):
        self.state = FridayState.IDLE
        self.layer = FridayPipeline()
        self.loop = asyncio.new_event_loop()
        self.listening = True
        self.history: List[Tuple[str, str]] = []
        self.score = 0
        self._game_state = {"pos": 0, "obstacles": [], "tick": 0}
        
        t = threading.Thread(target=self.start_backend)
        t.daemon = True
        t.start()

    def start_backend(self):
        try:
            asyncio.run(validate_startup())
            asyncio.set_event_loop(self.loop)
            _ = self.layer
            self.listen_loop()
            self.loop.run_forever()
        except Exception as e: logging.error(f"Backend Error: {e}")

    def listen_loop(self):
        from app.voice.listener import listener
        async def run_listener():
            try:
                self.state = FridayState.LISTENING
                await listener.start(self.process_audio)
                while True: await asyncio.sleep(1)
            except Exception as e: logging.error(f"Listener error: {e}")
        asyncio.run_coroutine_threadsafe(run_listener(), self.loop)

    async def process_audio(self, audio_bytes: bytes):
        if not self.listening: return
        self.state = FridayState.CAPTURED
        try:
            from app.voice.stt_service import stt_service
            text = await stt_service.transcribe(audio_bytes)
            if text and text.strip():
                self.history.append(("user", text))
                await self.process_text(text)
            else: self.state = FridayState.IDLE
        except Exception as e: self.state = FridayState.IDLE

    async def process_text(self, text: str):
        self.state = FridayState.PROCESSING
        try:
            from app.voice.tts_service import tts_service
            full_res, current_sent = "", ""
            audio_queue = asyncio.Queue()

            async def audio_worker():
                while True:
                    sent = await audio_queue.get()
                    if sent is None: break
                    audio = await tts_service.get_audio(sent.strip())
                    if audio:
                        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                            tmp.write(audio); p = tmp.name
                        self.state = FridayState.RESPONDING
                        proc = await asyncio.create_subprocess_exec("afplay", p)
                        await proc.wait(); os.unlink(p)
                    audio_queue.task_done()

            worker = asyncio.create_task(audio_worker())
            res_idx = len(self.history)
            self.history.append(("friday", ""))

            async for chunk in self.layer.stream_run(text, voice_mode=True):
                if chunk.startswith("event: token"):
                    token = json.loads(chunk.split("data: ")[1]).get("t", "")
                    full_res += token; current_sent += token
                    self.history[res_idx] = ("friday", full_res)
                    if any(p in current_sent for p in [". ", "! ", "? "]):
                        parts = current_sent.split(". ", 1)
                        await audio_queue.put(parts[0] + ". ")
                        current_sent = parts[1] if len(parts) > 1 else ""

            if current_sent.strip(): await audio_queue.put(current_sent)
            await audio_queue.put(None); await worker; self.score += 1
        except Exception as e: logging.error(f"Text Error: {e}")
        finally: self.state = FridayState.IDLE

    def render_ui(self) -> Table:
        # Create a single unified table that contains everything
        # This is much more robust than the nested Layout objects
        main_table = Table.grid(expand=True)
        main_table.add_column()
        
        # Header
        header_grid = Table.grid(expand=True)
        header_grid.add_column(justify="left", ratio=1)
        header_grid.add_column(justify="center", ratio=1)
        header_grid.add_column(justify="right", ratio=1)
        header_grid.add_row("[friday]FRIDAY[/friday] [dim]v0.2.0[/dim]", "[bold white]ANTIGRAVITY ENGINE[/bold white]", datetime.now().strftime("%H:%M:%S"))
        main_table.add_row(Panel(header_grid, style="blue"))
        
        # Body (Main + Sidebar)
        body_table = Table.grid(expand=True)
        body_table.add_column(ratio=3); body_table.add_column(ratio=1)
        
        # Main Chat
        chat_text = Text()
        for s, m in self.history[-6:]:
            color = "purple" if s == "user" else "cyan"
            chat_text.append(f"{s} > ", style=f"bold {color}")
            chat_text.append(f"{m}\n", style="white")
        main_chat = Panel(chat_text, title="[bold]NEURAL INTERFACE[/bold]", border_style="cyan", height=15)
        
        # Sidebar
        stats = self.layer.telemetry.stats
        stat_table = Table.grid(padding=(0, 1))
        stat_table.add_column(style="dim cyan", justify="right")
        stat_table.add_column(style="bold white")
        stat_table.add_row("State", f"{self.state.value}")
        stat_table.add_row("Score", f"[yellow]{self.score}[/yellow]")
        stat_table.add_row("FLOPs", f"{stats.get('total_flops', 0):,.0f}")
        stat_table.add_row("Energy", f"{stats.get('total_energy_joules', 0.0):.2f}J")
        stat_table.add_row("Battery", f"{stats.get('battery_level', 1.0)*100:.0f}%")
        sidebar = Panel(stat_table, title="[bold]TELEMETRY[/bold]", border_style="blue", height=15)
        
        body_table.add_row(main_chat, sidebar)
        main_table.add_row(body_table)
        
        # Dino Footer
        width = console.width - 15
        gs = self._game_state; gs["tick"] += 1
        ground = list(" " * width)
        if gs["tick"] % 15 == 0: gs["obstacles"].append(width - 1)
        gs["obstacles"] = [o - 1 for o in gs["obstacles"] if o > 0]
        for o in gs["obstacles"]:
            if o < width: ground[o] = "🌵"
        
        dino_char = "🦖" if self.state != FridayState.RESPONDING else "🔥"
        dino_y = 1 if self.state in [FridayState.PROCESSING, FridayState.CAPTURED] else 0
        
        dino_text = Text()
        if dino_y == 1:
            dino_text.append(" " * 5 + dino_char + "\n", style="yellow")
            dino_text.append("".join(ground) + "\n", style="green")
        else:
            line = "".join(ground); line = line[:5] + dino_char + line[6:]
            dino_text.append(line + "\n", style="green")
        dino_text.append("═" * width, style="blue")
        
        main_table.add_row(Panel(Align.center(dino_text), title="[bold yellow]CHROME MODE[/bold yellow]", border_style="blue", height=6))
        
        return main_table

    def run(self):
        console.clear()
        with Live(self.render_ui(), refresh_per_second=10, screen=True, auto_refresh=False) as live:
            while True:
                try:
                    live.update(self.render_ui())
                    live.refresh()
                    time.sleep(0.1)
                except KeyboardInterrupt: break
                except Exception as e: logging.error(f"UI Error: {e}")

def main():
    FridayMenuApp().run()

if __name__ == "__main__":
    main()
