import sys
import os

# Ensure project root is in path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "friday"))

print("Checking dependencies...")
try:
    import torch
    print(f"Torch: {torch.__version__}")
except ImportError:
    print("Torch NOT installed.")

try:
    import funasr
    print(f"FunASR: {funasr.__version__}")
except ImportError:
    print("FunASR NOT installed.")

try:
    import modelscope
    print(f"ModelScope: {modelscope.__version__}")
except ImportError:
    print("ModelScope NOT installed.")

try:
    from AppKit import NSWindow, NSVisualEffectView
    print("AppKit/PyObjC: OK")
except ImportError:
    print("AppKit NOT installed.")

print("\nValidating VoiceListener...")
try:
    from friday.app.voice.listener import VoiceListener
    l = VoiceListener()
    print("VoiceListener init: OK")
except Exception as e:
    print(f"VoiceListener Error: {e}")

print("\nValidating MenuBar...")
try:
    from friday.menubar import FridayMenuBarApp
    # Don't run it, just check init
    # m = FridayMenuBarApp()
    print("MenuBar class check: OK")
except Exception as e:
    print(f"MenuBar Error: {e}")
