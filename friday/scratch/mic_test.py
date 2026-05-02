import sounddevice as sd
import numpy as np
import time

def callback(indata, frames, time_info, status):
    if status:
        print(status)
    rms = np.sqrt(np.mean(indata**2)) * 10000
    print(f"RMS: {rms:.2f} " + ("#" * int(rms/100)))

print("Testing microphone live. Speak into it.")
print("If RMS stays near 0, check your System Settings > Sound > Input.")
with sd.InputStream(callback=callback, channels=1, samplerate=16000):
    time.sleep(10)
