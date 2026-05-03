# Pipeline Overhaul Quick Start Guide

## Using the Enhanced Speech Pipeline

### Phase 1: Quick Wins (Enable Now)

#### 1. Native macOS TTS (Default Enabled)
```python
# Already enabled by default
from friday.app.voice.tts_service import tts_service

# Native TTS - Zero network latency, ~50ms
audio_file = await tts_service.synthesize_to_file("Hello world")

# Or stream directly to speakers
await tts_service.speak_direct("Hello world")
```

**Command-line toggle**:
```bash
export FRIDAY_USE_NATIVE_TTS=true
python friday/macos_menu_bar.py
```

#### 2. Speaker Verification Bypass (For Testing)
```python
# Disable SV for latency testing
from friday.app.core.config import settings

# Zero latency - no voice verification
settings.BYPASS_SPEAKER_VERIFICATION = True
```

Or in `.env`:
```
BYPASS_SPEAKER_VERIFICATION=true
```

---

### Phase 2: Deep Fixes (Production)

#### 1. MLX-Whisper STT (Automatic)
```python
from friday.app.voice.mlx_stt import mlx_stt

# Automatically uses Metal-accelerated MLX-Whisper
text = await mlx_stt.transcribe(audio_bytes)  # ~200ms
```

**Configure model size**:
```python
mlx_stt.set_model("base.en")   # ~200ms, best accuracy
mlx_stt.set_model("small.en")  # ~150ms, good accuracy
mlx_stt.set_model("tiny.en")   # ~100ms, low accuracy
```

Environment variable:
```bash
FRIDAY_STT_MODEL_SIZE=base.en
```

#### 2. Lightweight Speaker Verification
```python
from friday.app.voice.speaker_verifier import speaker_verifier

# ONNX-based, ~30ms (vs FunASR ~200ms)
is_authorized = await speaker_verifier.verify(audio_np)

# Enrollment
await speaker_verifier.enroll(audio_np)
```

Configuration:
```
USE_LIGHTWEIGHT_SV=true
SPEAKER_VERIFICATION_THRESHOLD=0.7
```

#### 3. Battery-Aware Model Selection
```python
from friday.core.observability import observability

# Automatically selects optimal models based on battery
telemetry = observability.TelemetryManager()

stt_model = telemetry.get_stt_model_size()      # Returns optimal STT model
tts_mode = telemetry.get_tts_mode()             # Returns optimal TTS mode
sv_mode = telemetry.get_speaker_verification_mode()
```

**Automatic behavior**:
- **Battery < 15%**: Ultra-saver mode (tiny.en STT)
- **Battery 15-30%**: Balanced mode (small.en STT)
- **Battery > 30%**: Full power mode (base.en STT)

---

### Phase 3: Polish (Advanced)

#### 1. WebRTC VAD (Automatic)
```python
from friday.app.voice.vad import vad

# WebRTC-based voice detection
is_speech = vad.is_speech(audio_chunk)

# Configure aggressiveness (0=least, 3=most aggressive)
vad_aggressive = VoiceActivityDetector(aggressiveness=2)
```

#### 2. AVFoundation Ultra-Low-Latency Capture (Optional)
```python
from friday.app.voice.av_capture import av_capture

async def on_audio(audio_chunk):
    print(f"Got {len(audio_chunk)} samples")

# Start capturing at ~5ms latency (vs PyAudio ~20ms)
await av_capture.start(on_audio)

# Stop when done
await av_capture.stop()
```

#### 3. Run Comprehensive Benchmarks
```bash
cd /Users/anmol/Downloads/Developer/Friday
python friday/tests/bench_pipeline.py
```

**Sample output**:
```
=== VAD Benchmark ===
  1000 silence checks: 4.9ms total (0.005ms/call)
  1000 speech checks:  4.4ms total (0.004ms/call)

=== TTS Benchmark ===
  Native TTS:  ~1000ms (158750 bytes)
  Edge TTS:    ~1200ms (27936 bytes)

=== Battery-Aware Model Selection ===
  Battery 10% (Ultra Saver):
    STT Model: tiny.en
    TTS Mode:  native
    SV Mode:   lightweight
```

---

## Configuration Reference

### Environment Variables

```bash
# ===== PHASE 1: Quick Wins =====
FRIDAY_USE_NATIVE_TTS=true              # Enable macOS Native TTS
FRIDAY_NATIVE_TTS_VOICE=samantha        # Voice: alex, samantha, daniel, karen, moira, etc
FRIDAY_NATIVE_TTS_RATE=200              # Speech rate (WPM, range 50-400)

# ===== PHASE 2: Deep Fixes =====
FRIDAY_STT_ENGINE=mlx                   # STT engine: mlx (default), whisper, funasr
FRIDAY_STT_MODEL_SIZE=base.en           # Model: tiny.en, small.en, base.en
FRIDAY_USE_LIGHTWEIGHT_SV=true          # Lightweight speaker verification
FRIDAY_BYPASS_SPEAKER_VERIFICATION=false # Disable SV for testing

# ===== BATTERY AWARENESS =====
FRIDAY_BATTERY_SAVER_THRESHOLD=0.2      # Battery level for ultra-saver mode
FRIDAY_TRACK_TELEMETRY=true             # Enable battery tracking

# ===== SPEAKER VERIFICATION =====
FRIDAY_SPEAKER_VERIFICATION_THRESHOLD=0.7
FRIDAY_SV_MIN_SECONDS=0.80
```

### Python Configuration

```python
from friday.app.core.config import settings

# Override settings programmatically
settings.USE_NATIVE_TTS = True
settings.STT_ENGINE = "mlx"
settings.STT_MODEL_SIZE = "base.en"
settings.USE_LIGHTWEIGHT_SV = True
settings.BYPASS_SPEAKER_VERIFICATION = False
settings.SPEAKER_VERIFICATION_THRESHOLD = 0.7
```

---

## Performance Checklist

### Verify Improvements

- [ ] TTS latency < 100ms (target: 50ms)
  ```bash
  grep "Native TTS:" debug.log
  ```

- [ ] STT latency < 250ms (target: 200ms)
  ```bash
  grep "MLX-Whisper Latency:" debug.log
  ```

- [ ] Speaker verification < 50ms (target: 30ms)
  ```bash
  grep "Speaker verification:" debug.log
  ```

- [ ] VAD latency < 0.01ms per frame
  ```python
  python -c "from friday.app.voice.vad import vad; print(vad.is_speech(...))"
  ```

- [ ] Battery-aware selection working
  ```bash
  grep "Battery level:" logs/observability_metrics.json
  ```

---

## Troubleshooting

### Issue: Native TTS Not Available
**Solution**: Check if AppKit is properly installed
```bash
python -c "from AppKit import NSSpeechSynthesizer; print('OK')"
```

### Issue: MLX-Whisper Falls Back to Faster-Whisper
**Solution**: Install MLX-Whisper
```bash
pip install mlx-whisper
```

### Issue: ONNX Speaker Verification Not Loaded
**Solution**: Download ONNX model
```bash
# Model will auto-download to ~/.friday/resemblyzer.onnx
# First run may take time for download
```

### Issue: Battery Awareness Not Working
**Solution**: Install psutil
```bash
pip install psutil
```

---

## Integration Example

### Complete Pipeline with All Phases

```python
import asyncio
from friday.app.voice.listener import listener
from friday.app.voice.tts_service import tts_service
from friday.app.voice.mlx_stt import mlx_stt
from friday.app.voice.speaker_verifier import speaker_verifier
from friday.app.voice.vad import vad
from friday.core.observability import observability

async def full_pipeline():
    # Phase 3: Capture audio with ultra-low latency
    audio_bytes = await listener.capture_audio(duration=3.0)
    
    # Phase 3: VAD check
    if not vad.is_speech(audio_bytes):
        print("No speech detected")
        return
    
    # Phase 2: Speaker verification (lightweight, ~30ms)
    if not await speaker_verifier.verify(audio_bytes):
        print("Voice not recognized")
        return
    
    # Phase 2: Transcribe with MLX-Whisper (~200ms)
    text = await mlx_stt.transcribe(audio_bytes)
    print(f"You said: {text}")
    
    # Phase 1: TTS with Native macOS (~50ms)
    response = "Hello! I understood your command."
    await tts_service.speak_direct(response)  # Direct to speakers
    
    # Get battery-aware suggestion
    telemetry = observability.TelemetryManager()
    print(f"Using STT model: {telemetry.get_stt_model_size()}")

# Run the pipeline
asyncio.run(full_pipeline())
```

---

## Performance Monitoring

### Enable Debug Logging

```bash
export FRIDAY_LOG_LEVEL=DEBUG
python friday/macos_menu_bar.py
```

### Monitor Latency Metrics

```bash
# Watch real-time latency
tail -f logs/observability_metrics.json | grep latency

# View battery-aware decisions
tail -f logs/observability_metrics.json | grep battery_level
```

### Analyze Benchmark Results

```bash
python friday/tests/bench_pipeline.py > results.txt
grep "Latency\|Battery" results.txt
```

---

## FAQ

**Q: Should I enable AVFoundation capture?**  
A: If you need < 5ms latency, yes. Otherwise, current PyAudio (~20ms) is sufficient.

**Q: What's the battery-aware threshold?**  
A: At 20% battery, Friday switches to "tiny.en" (100ms STT) for power savings.

**Q: Can I use cloud TTS instead of native?**  
A: Yes, but it adds 300ms latency. Set `USE_NATIVE_TTS=false` to revert.

**Q: How accurate is MLX-Whisper base.en?**  
A: ~95% WER on clean audio, similar to OpenAI's Whisper base model.

**Q: Is speaker verification mandatory?**  
A: No, set `BYPASS_SPEAKER_VERIFICATION=true` to disable for testing.

---

## See Also

- `pipeline_overhaul_plan.md` - Original implementation plan
- `IMPLEMENTATION_REPORT.md` - Detailed technical report
- `friday/tests/bench_pipeline.py` - Comprehensive benchmarks
- `friday/core/streaming_pipeline.py` - Overlapped streaming architecture

