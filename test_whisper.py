import time
print("Importing...")
from faster_whisper import WhisperModel
print("Loading model...")
model = WhisperModel("base", device="cpu", compute_type="int8")
print("Model loaded.")
