#!/usr/bin/env python3
import asyncio
import sys
import threading
import tempfile
import os
import subprocess
import speech_recognition as sr
import rumps

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
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.layer.initialize())
        print("Hello Boss. FRIDAY online. I'm listening...")
        self.listen_loop()

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
                            
                        # Process audio
                        asyncio.run_coroutine_threadsafe(
                            self.process_audio(audio.get_wav_data()), self.loop
                        )
                    except sr.WaitTimeoutError:
                        pass
                    except Exception as e:
                        print(f"STT Listen Error: {e}")
        except Exception as e:
            print(f"Microphone init failed: {e}")

    async def process_audio(self, audio_bytes: bytes):
        try:
            from app.voice.stt import transcribe
            text = await transcribe(audio_bytes)
            if not text or not text.strip():
                return
                
            print(f"\nYou: {text}")
            
            # Check for interrupt/exit
            if text.strip().lower() in ['exit', 'quit', 'stop listening']:
                rumps.quit_application()
                return
                
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
            print(f"Error processing audio: {e}")

def main():
    # Make sure we don't duplicate run loops
    app = FridayMenuApp()
    app.run()

if __name__ == "__main__":
    main()
