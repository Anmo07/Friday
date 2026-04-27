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
        super(FridayMenuApp, self).__init__("FRIDAY", icon=None)
        self.title = "🤖" # Icon in menu bar
        self.menu = ["Listen", "Quit"]
        self.layer = ConversationLayer()
        self.loop = asyncio.new_event_loop()
        self.listening = False
        
        # Start background tasks
        t = threading.Thread(target=self.start_background_loop)
        t.daemon = True
        t.start()
        
    def start_background_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.layer.initialize())
        print("Hello Boss. FRIDAY online. I'm listening...")
        self.listen_loop()

    def listen_loop(self):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                while True:
                    try:
                        audio = recognizer.listen(source, timeout=None, phrase_time_limit=10)
                        
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

    @rumps.clicked("Quit")
    def quit_app(self, _):
        rumps.quit_application()

def main():
    # Make sure we don't duplicate run loops
    app = FridayMenuApp()
    app.run()

if __name__ == "__main__":
    main()
