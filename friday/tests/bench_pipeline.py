"""
Friday Speech Pipeline Benchmark Suite
=======================================
Validates latency improvements across all pipeline stages.
"""
import asyncio
import time
import sys
import os
import numpy as np

# Ensure project imports work
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "friday"))


async def benchmark_native_tts():
    """Benchmark macOS Native TTS vs Edge-TTS."""
    print("\n=== TTS Benchmark ===")
    text = "This is a test sentence for benchmarking text-to-speech synthesis speed."

    # Native TTS
    try:
        from app.voice.native_tts import NativeTTS
        tts = NativeTTS()
        start = time.monotonic()
        path = await tts.synthesize_to_file(text)
        elapsed = (time.monotonic() - start) * 1000
        print(f"  Native TTS:  {elapsed:.0f}ms", end="")
        if path:
            size = os.path.getsize(path)
            os.unlink(path)
            print(f" ({size} bytes)")
        else:
            print(" (failed)")
    except Exception as e:
        print(f"  Native TTS:  ERROR - {e}")

    # Edge-TTS
    try:
        import edge_tts
        start = time.monotonic()
        comm = edge_tts.Communicate(text, "en-US-JennyNeural")
        audio = b""
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        elapsed = (time.monotonic() - start) * 1000
        print(f"  Edge TTS:    {elapsed:.0f}ms ({len(audio)} bytes)")
    except Exception as e:
        print(f"  Edge TTS:    ERROR - {e}")


async def benchmark_stt():
    """Benchmark MLX-Whisper vs Faster-Whisper."""
    print("\n=== STT Benchmark ===")
    # Generate 3 seconds of test audio (sine wave with noise)
    sr = 16000
    duration = 3.0
    t = np.linspace(0, duration, int(sr * duration), dtype=np.float32)
    audio = (np.sin(2 * np.pi * 440 * t) * 0.5 * 32768).astype(np.int16)
    audio_bytes = audio.tobytes()

    # MLX-Whisper
    try:
        from app.voice.mlx_stt import MLXWhisperSTT
        stt = MLXWhisperSTT(model_size="base.en")
        start = time.monotonic()
        text = await stt.transcribe(audio_bytes)
        elapsed = (time.monotonic() - start) * 1000
        print(f"  MLX-Whisper (base.en): {elapsed:.0f}ms | '{text[:50]}'")
    except Exception as e:
        print(f"  MLX-Whisper: ERROR - {e}")

    # Faster-Whisper
    try:
        from app.voice.stt_service import STTService
        stt = STTService()
        start = time.monotonic()
        text = await stt.transcribe(audio_bytes)
        elapsed = (time.monotonic() - start) * 1000
        print(f"  Faster-Whisper:       {elapsed:.0f}ms | '{text[:50]}'")
    except Exception as e:
        print(f"  Faster-Whisper: ERROR - {e}")


async def benchmark_vad():
    """Benchmark VAD detection speed."""
    print("\n=== VAD Benchmark ===")
    from app.voice.vad import VoiceActivityDetector

    vad = VoiceActivityDetector()
    # Silent audio
    silence = np.zeros(1024, dtype=np.int16)
    # Speech-like audio
    speech = (np.random.randn(1024) * 5000).astype(np.int16)

    iterations = 1000
    start = time.monotonic()
    for _ in range(iterations):
        vad.is_speech(silence)
    elapsed_silence = (time.monotonic() - start) * 1000

    vad.reset()
    start = time.monotonic()
    for _ in range(iterations):
        vad.is_speech(speech)
    elapsed_speech = (time.monotonic() - start) * 1000

    print(f"  {iterations} silence checks: {elapsed_silence:.1f}ms total ({elapsed_silence/iterations:.3f}ms/call)")
    print(f"  {iterations} speech checks:  {elapsed_speech:.1f}ms total ({elapsed_speech/iterations:.3f}ms/call)")


async def main():
    print("=" * 60)
    print("  Friday Speech Pipeline Benchmark")
    print("=" * 60)

    await benchmark_vad()
    await benchmark_native_tts()
    await benchmark_stt()

    print("\n" + "=" * 60)
    print("  Benchmark complete.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
