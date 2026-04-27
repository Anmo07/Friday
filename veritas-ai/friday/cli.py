#!/usr/bin/env python3
import asyncio
import sys
import threading
import tempfile
import os
import subprocess
import warnings
import speech_recognition as sr
import rumps

# Suppress LangChain and Pydantic warnings for a clean terminal interface
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore")

from core.conversation_layer import ConversationLayer

class FridayMenuApp(rumps.App):
    def __init__(self):
        super(FridayMenuApp, self).__init__("FRIDAY", icon=None, quit_button="Quit FRIDAY")
        self.title = "🤖" # Icon in menu bar
        
        # Define menu items
        self.status_menu = rumps.MenuItem("Status: Active", callback=None)
        self.toggle_mic_menu = rumps.MenuItem("Pause Listening", callback=self.toggle_mic)
        self.clear_mem_menu = rumps.MenuItem("Clear Context Memory", callback=self.clear_memory)
        self.open_dash_menu = rumps.MenuItem("Open Assistant Dashboard", callback=self.open_dashboard)
        self.open_ctrl_menu = rumps.MenuItem("Open Control Room", callback=self.open_control_room)
        
        self.menu = [
            self.status_menu,
            None, # Separator
            self.toggle_mic_menu,
            self.clear_mem_menu,
            None,
            self.open_dash_menu,
            self.open_ctrl_menu,
            None
        ]
        
        self.layer = ConversationLayer()
        self.loop = asyncio.new_event_loop()
        self.listening = True
        
        # Start background tasks
        t = threading.Thread(target=self.start_background_loop)
        t.daemon = True
        t.start()
        
    def start_background_loop(self):
        try:
            print("Initializing FRIDAY...")
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.layer.initialize())
            print("\nHello Boss. FRIDAY online. I'm listening...")
            print("(You can speak or type your commands here)\n")
            
            # Start terminal input thread
            terminal_thread = threading.Thread(target=self.terminal_loop)
            terminal_thread.daemon = True
            terminal_thread.start()
            
            self.listen_loop()
        except Exception as e:
            print(f"\n[Startup Error]: {e}")

    def terminal_loop(self):
        # Allow text interaction from the terminal alongside voice
        while True:
            try:
                user_input = input("")
                if not user_input.strip():
                    continue
                if user_input.strip().lower() in ['exit', 'quit', 'stop']:
                    print("FRIDAY: Shutting down. Goodbye Boss.")
                    rumps.quit_application()
                    break
                
                # We echo the 'You: ' manually if they type
                print(f"You (text): {user_input}")
                
                # Process text input
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
        rumps.notification("FRIDAY", "Memory Cleared", "Conversation context has been reset.")
        print("FRIDAY: Context memory cleared.")

    def open_dashboard(self, _):
        subprocess.Popen(["open", "http://localhost:3000/dashboard"])

    def open_control_room(self, _):
        subprocess.Popen(["open", "http://localhost:3000/control"])

    def listen_loop(self):
        import time
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300  # Set a low base threshold for sensitivity
        recognizer.dynamic_energy_threshold = True
        
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                while True:
                    if not self.listening:
                        time.sleep(0.5)
                        continue
                        
                    try:
                        audio = recognizer.listen(source, timeout=None, phrase_time_limit=10)
                        
                        if not self.listening:
                            continue
                            
                        print("\n[Voice detected, transcribing...]", flush=True)
                        # Process audio
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
            full_response = ""
            print("FRIDAY:", end=" ", flush=True)
            async for chunk in self.layer.process_query_stream(text):
                print(chunk, end="", flush=True)
                full_response += chunk
            print()
            
            # Text to Speech
            from app.voice.tts import speak
            audio_response = await speak(full_response)
            if audio_response:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp.write(audio_response)
                    tmp_path = tmp.name
                
                # Play audio using macOS built-in afplay
                subprocess.Popen(["afplay", tmp_path]).wait()
                os.unlink(tmp_path)
                
        except Exception as e:
            print(f"\n[Error processing text]: {e}")

    async def process_audio(self, audio_bytes: bytes):
        try:
            from app.voice.stt import transcribe
            text = await transcribe(audio_bytes)
            if not text or not text.strip():
                print("[Transcription returned empty]")
                return
                
            print(f"You: {text}")
            
            # Check for interrupt/exit
            if text.strip().lower() in ['exit', 'quit', 'stop listening']:
                rumps.quit_application()
                return
                
            await self.process_text(text)
                
        except Exception as e:
            print(f"\n[Error processing audio]: {e}")

def main():
    # Make sure we don't duplicate run loops
    app = FridayMenuApp()
    app.run()

if __name__ == "__main__":
    main()
