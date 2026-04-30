import asyncio
import sys
import json
import threading
import tempfile
import os
import subprocess
import warnings
import speech_recognition as sr
import rumps

# Add project root to sys.path to resolve sibling packages
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore")
from core.pipeline import FridayPipeline


class FridayMenuApp(rumps.App):
    def __init__(self):
        super(FridayMenuApp, self).__init__(
            "FRIDAY", icon=None, quit_button="Quit FRIDAY"
        )
        self.title = "🤖"
        self.status_menu = rumps.MenuItem("Status: Active", callback=None)
        self.toggle_mic_menu = rumps.MenuItem(
            "Pause Listening", callback=self.toggle_mic
        )
        self.clear_mem_menu = rumps.MenuItem(
            "Clear Context Memory", callback=self.clear_memory
        )
        self.open_dash_menu = rumps.MenuItem(
            "Open Assistant Dashboard", callback=self.open_dashboard
        )
        self.open_ctrl_menu = rumps.MenuItem(
            "Open Control Room", callback=self.open_control_room
        )
        self.menu = [
            self.status_menu,
            None,
            self.toggle_mic_menu,
            self.clear_mem_menu,
            None,
            self.open_dash_menu,
            self.open_ctrl_menu,
            None,
        ]
        self.layer = FridayPipeline()
        self.loop = asyncio.new_event_loop()
        self.listening = True
        t = threading.Thread(target=self.start_background_loop)
        t.daemon = True
        t.start()

    def _run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start_background_loop(self):
        try:
            print("Initializing FRIDAY...")
            asyncio.set_event_loop(self.loop)
            print("\nHello Boss. FRIDAY online. I'm listening...")
            print("(You can speak or type your commands here)\n")
            loop_thread = threading.Thread(target=self._run_async_loop)
            loop_thread.daemon = True
            loop_thread.start()
            terminal_thread = threading.Thread(target=self.terminal_loop)
            terminal_thread.daemon = True
            terminal_thread.start()
            self.listen_loop()
        except Exception as e:
            print(f"\n[Startup Error]: {e}")

    def terminal_loop(self):
        while True:
            try:
                user_input = input("")
                if not user_input.strip():
                    continue
                if user_input.strip().lower() in ["exit", "quit", "stop"]:
                    print("FRIDAY: Shutting down. Goodbye Boss.")
                    rumps.quit_application()
                    break
                print(f"You (text): {user_input}")
                asyncio.run_coroutine_threadsafe(
                    self.process_text(user_input), self.loop
                )
            except (KeyboardInterrupt, EOFError):
                rumps.quit_application()
                break
            except Exception as e:
                print(f"Terminal Input Error: {e}")

    def toggle_mic(self, sender):
        self.listening = not self.listening
        if self.listening:
            sender.title = "Pause Listening"
            self.status_menu.title = "Status: Active"
            self.title = "🤖"
            print("FRIDAY: Listening resumed.")
        else:
            sender.title = "Resume Listening"
            self.status_menu.title = "Status: Paused"
            self.title = "💤"
            print("FRIDAY: Listening paused.")

    def clear_memory(self, _):
        self.layer.memory.clear()
        rumps.notification(
            "FRIDAY", "Memory Cleared", "Conversation context has been reset."
        )
        print("FRIDAY: Context memory cleared.")

    def open_dashboard(self, _):
        subprocess.Popen(["open", "http://localhost:3000/dashboard"])

    def open_control_room(self, _):
        subprocess.Popen(["open", "http://localhost:3000/control"])

    def listen_loop(self):
        import time

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8
        recognizer.non_speaking_duration = 0.5
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1.5)
                while True:
                    if not self.listening:
                        time.sleep(0.5)
                        continue
                    try:
                        audio = recognizer.listen(
                            source, timeout=None, phrase_time_limit=10
                        )
                        if not self.listening:
                            continue
                        print("\n[Voice detected, transcribing...]", flush=True)
                        asyncio.run_coroutine_threadsafe(
                            self.process_audio(audio.get_wav_data()), self.loop
                        )
                    except sr.WaitTimeoutError:
                        pass
                    except Exception as e:
                        print(f"\n[STT Listen Error]: {e}")
        except Exception as e:
            print(f"\n[Microphone init failed]: {e}")

    async def process_text(self, text: str):
        try:
            from app.voice.tts_service import tts_service

            full_response = ""
            current_sentence = ""
            print("FRIDAY:", end=" ", flush=True)
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
                            proc = await asyncio.create_subprocess_exec(
                                "afplay", tmp_path
                            )
                            await proc.wait()
                            os.unlink(tmp_path)
                    audio_queue.task_done()

            worker_task = asyncio.create_task(audio_worker())
            async for chunk in self.layer.stream_run(text, voice_mode=True):
                if chunk.startswith("event: token"):
                    data = json.loads(chunk.split("data: ")[1])
                    token = data.get("t", "")
                    print(token, end="", flush=True)
                    full_response += token
                    current_sentence += token
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
            print()
            if current_sentence.strip():
                await audio_queue.put(current_sentence)
            await audio_queue.put(None)
            await worker_task
        except Exception as e:
            print(f"\n[Error processing text]: {e}")

    async def process_audio(self, audio_bytes: bytes):
        try:
            from app.voice.stt_service import stt_service

            text = await stt_service.transcribe(audio_bytes)
            if not text or not text.strip():
                print("[Transcription returned empty]")
                return
            print(f"You: {text}")
            if text.strip().lower() in ["exit", "quit", "stop listening"]:
                rumps.quit_application()
                return
            await self.process_text(text)
        except Exception as e:
            print(f"\n[Error processing audio]: {e}")


def main():
    app = FridayMenuApp()
    app.run()


if __name__ == "__main__":
    main()
