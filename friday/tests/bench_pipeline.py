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


async def benchmark_speaker_verification():
    """Benchmark lightweight speaker verification."""
    print("\n=== Speaker Verification Benchmark ===")
    from app.voice.speaker_verifier import LightweightSpeakerVerifier

    # Create synthetic audio for speaker embedding
    sample_audio = (np.random.randn(16000 * 2) * 5000).astype(np.int16)  # 2 seconds

    verifier = LightweightSpeakerVerifier()

    if not verifier.is_available:
        print("  ONNX speaker verification not available (model not downloaded)")
        return

    try:
        # Benchmark verification speed
        start = time.monotonic()
        result = await verifier.verify(sample_audio.astype(np.float32) / 32768.0)
        elapsed = (time.monotonic() - start) * 1000
        print(f"  Lightweight SV: {elapsed:.1f}ms | Result: {result}")
    except Exception as e:
        print(f"  Speaker Verification: ERROR - {e}")


async def benchmark_streaming_pipeline():
    """Benchmark end-to-end streaming pipeline."""
    print("\n=== End-to-End Streaming Pipeline ===")
    try:
        from friday.core.streaming_pipeline import streaming_pipeline
    except Exception as e:
        print(f"  Skipping streaming pipeline test: {e}")
        return

    # Mock functions for benchmark
    async def mock_stt(audio):
        await asyncio.sleep(0.20)  # Simulate MLX-Whisper latency
        return "What is the weather today"

    async def mock_llm(query):
        # Simulate streaming LLM response
        response = "The weather today is sunny with a high of 75 degrees and low wind."
        for i, token in enumerate(response.split()):
            await asyncio.sleep(0.02)  # Simulate token generation
            yield token + " "

    async def mock_tts(text):
        # Simulate native TTS latency
        await asyncio.sleep(0.05)
        return "/tmp/audio.wav"

    # Generate test audio
    audio = (np.sin(2 * np.pi * 440 * np.linspace(0, 3, 48000)) * 0.5 * 32768).astype(np.int16).tobytes()

    start = time.monotonic()
    total_latency = 0
    token_count = 0

    try:
        async for event in streaming_pipeline.process_streaming(
            audio, mock_stt, mock_llm, mock_tts
        ):
            if event["type"] == "stt":
                print(f"  STT Latency: ~{streaming_pipeline.metrics['stt_latency_ms']:.0f}ms")
            elif event["type"] == "llm_token":
                token_count += 1
            elif event["type"] == "metrics":
                print(f"  LLM First Token: ~{streaming_pipeline.metrics['llm_first_token_ms']:.0f}ms")
                print(f"  TTS First Audio: ~{streaming_pipeline.metrics['tts_first_audio_ms']:.0f}ms")
                print(f"  Total Latency: ~{streaming_pipeline.metrics['total_latency_ms']:.0f}ms")
    except Exception as e:
        print(f"  Streaming Pipeline: ERROR - {e}")


async def benchmark_battery_aware_selection():
    """Benchmark battery-aware model selection logic."""
    print("\n=== Battery-Aware Model Selection ===")
    try:
        # Import based on path setup
        import sys
        if 'core.observability' not in sys.modules:
            from friday.core.observability import TelemetryManager
        else:
            from core.observability import TelemetryManager
    except Exception as e:
        print(f"  Skipping battery test: {e}")
        return

    telemetry = TelemetryManager()

    # Test different battery levels
    battery_levels = [0.1, 0.25, 0.5, 1.0]

    for battery_level in battery_levels:
        telemetry.stats["battery_level"] = battery_level
        telemetry.battery_percent = battery_level

        stt_model = telemetry.get_stt_model_size()
        tts_mode = telemetry.get_tts_mode()
        sv_mode = telemetry.get_speaker_verification_mode()

        mode_name = {
            0.1: "Ultra Saver",
            0.25: "Balanced",
            0.5: "Balanced",
            1.0: "Full Power"
        }.get(battery_level, "Unknown")

        print(f"  Battery {battery_level*100:.0f}% ({mode_name}):")
        print(f"    STT Model: {stt_model}")
        print(f"    TTS Mode:  {tts_mode}")
        print(f"    SV Mode:   {sv_mode}")


async def main():
    print("=" * 70)
    print("  Friday Speech Pipeline Benchmark Suite")
    print("  Target: STT ~200ms, TTS ~50ms, E2E ~250ms")
    print("=" * 70)

    await benchmark_vad()
    await benchmark_native_tts()
    await benchmark_stt()
    await benchmark_speaker_verification()
    await benchmark_battery_aware_selection()
    await benchmark_streaming_pipeline()

    print("\n" + "=" * 70)
    print("  Benchmark complete.")
    print("  See pipeline_overhaul_plan.md for target metrics.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
