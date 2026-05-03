# Friday — Industry-Leading Local AI Assistant

> **Private. Secure. Native. The first production-grade Local AI assistant for macOS with Biometric Speaker Verification and Liquid Glass UI.**

![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)
![Security](https://img.shields.io/badge/Security-Biometric-red.svg)
![Intelligence](https://img.shields.io/badge/Intelligence-Multi--Agent-orange.svg)

---

## 🚀 The Vision

Friday is no longer just a truth verification tool; it has evolved into an **Industry-Leading Local AI Assistant**. Designed for power users who demand privacy without compromising on intelligence, Friday lives natively in your macOS environment. It combines state-of-the-art **Biometric Security**, a **Siri-style Liquid Glass UI**, and a **Topological Event-Driven Architecture** to handle everything from system control to deep research.

**Tagline:** *Your Mac, Secured by Intelligence.*

---

## 🏗️ Core Architecture: The "Neural Orchestrator"

Friday operates on a multi-layered async pipeline designed for sub-200ms conversational responsiveness.

### 1. The Biometric Gate (Fun-ASR Integration)
Every acoustic trigger is validated against your unique vocal fingerprint. This prevents unauthorized activation from background noise or secondary speakers.

```python
# snippet from friday/app/voice/listener.py
async def verify_speaker(self, audio_bytes: bytes) -> bool:
    # Prepare audio for embedding computation
    verification_audio, meta = self._prepare_verification_audio(audio_bytes)
    
    # Compute live embedding using Fun-ASR + Torch
    current_embedding = await self._compute_embedding(verification_audio)
    
    # Cosine Similarity check against stored biometric profile
    similarity = torch_f.cosine_similarity(
        current_embedding.unsqueeze(0),
        self.user_embedding.unsqueeze(0),
    ).item()
    
    return similarity >= self.sv_similarity_threshold
```

### 2. Liquid Glass UI (Native PyObjC)
Friday's UI is built using native **Cocoa/AppKit** frameworks via **PyObjC**, ensuring a seamless "Siri-style" experience with high-vibrancy glassmorphism.

```python
# snippet from friday/macos_menu_bar.py
class SiriResponseWindow(NSWindow):
    def initWithContentRect_styleMask_backing_defer_(self, rect, style, backing, defer):
        # ... setup window ...
        self.blur = NSVisualEffectView.alloc().init()
        self.blur.setMaterial_(NSVisualEffectMaterialSidebar)
        self.blur.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        self.blur.layer().setCornerRadius_(28.0)
        
        # Adding a subtle Liquid Gradient gloss
        self.gloss = CAGradientLayer.layer()
        self.gloss.setColors_([NSColor.colorWithWhite_alpha_(1.0, 0.1).CGColor(), ...])
        self.blur.layer().addSublayer_(self.gloss)
```

### 3. Hardware-Aware Scaling (Dynamic VAD)
Friday monitors your system's power state and thermal pressure to dynamically adjust its neural models, preserving battery life without sacrificing critical performance.

```python
# snippet from friday/core/observability.py
def get_scaling_factor(self) -> float:
    """Returns a multiplier for thresholding based on hardware constraints."""
    if self.stats["battery_level"] < 0.15:
        return 0.4  # Ultra-saver mode (lightweight Whisper + high VAD)
    if self.stats["battery_level"] < 0.3 or self.is_on_battery:
        return 0.7  # Balanced mode
    return 1.0      # High Performance mode (Full Agent Swarm)
```

---

## 🛡️ Key Capabilities

| Capability | Integration | Technical Highlight |
|---|---|---|
| **Voice Biometrics** | `Fun-ASR` + `Torch` | 256-dimensional vocal embedding comparison for secure gating. |
| **STT Engine** | `Faster-Whisper` | Beam search transcription with CTranslate2 backend for 5x speed. |
| **Neural TTS** | `Edge-TTS` | Streaming prosody-aware synthesis with SSE text synchronization. |
| **System Control** | `AppKit` + `Subprocess` | Control your Mac: "Open Spotify", "Lock System", "Find my latest PDF". |
| **Agent Swarm** | `CrewAI` + `LangChain` | Autonomous agents for deep research and logic verification. |
| **Liquid UI** | `PyObjC` + `Quartz` | Blur-behind effects and CoreAnimation-driven neural orb. |
| **Security Gate** | `Semantic Router` | MoE-style routing for intent detection and prompt injection protection. |

---

## 📡 Deep Technical Deep Dive

### Topological Event-Driven Stream
Friday uses an internal **Async Event Bus** to manage the flow of data between the microphone, the STT engine, the LLM, and the UI. This architecture eliminates the "Stop-and-Wait" latency common in traditional assistants.

- **Non-Blocking Ingestion**: Audio is captured in 30ms chunks and resampled in-flight to 16kHz for neural compatibility.
- **Speculative Execution**: The LLM begins generating a response the moment the "End of Utterance" is detected, while the STT finalizes the last few words.
- **SSE Sync**: Text is streamed to the UI via Server-Sent Events (SSE), while chunks are sent to the TTS engine for parallel audio synthesis.

### The "Hallucination Firewall"
Integrated between the Agent Swarm and the user, this layer uses **Knowledge Graph Validation (Neo4j)** and **Contradiction Detection** to verify that every claim made by the assistant is grounded in local or retrieved facts.

---

## 📦 Detailed Setup & Integration

### Prerequisites
- **macOS**: 12.0+ (Monterey, Ventura, Sonoma)
- **Python**: 3.9+
- **Hardware**: Apple Silicon (M1/M2/M3) recommended for neural acceleration.

### Professional Installation
```bash
# 1. Clone the High-Performance Branch
git clone https://github.com/Anmo07/Friday.git && cd Friday

# 2. Automated Native Setup
./setup-friday.sh 

# 3. Launch the Orchestrator
friday
```

### Biometric Enrollment Flow
1. Click the **Orb (🤖)** in your Menu Bar.
2. Select **"Capture Voice Profile"**.
3. Speak for 6 seconds. Friday will generate your `user_vocal_embedding.pt` locally.
4. From now on, Friday will ignore any voice that doesn't match this signature.

---

## 🛠️ Tech Stack: The Best of AI

- **Neural Processing:** Fun-ASR, Faster-Whisper, PyTorch, CTranslate2
- **Orchestration:** CrewAI, LangChain, Semantic Router
- **Native macOS Bridge:** PyObjC, Rumps, AppKit, Quartz, CoreAnimation
- **Observability:** PSUtil, Custom TelemetryManager (Energy/FLOPs tracking)
- **Data Layers:** ChromaDB (Vector Memory), Neo4j (Knowledge Graph), SQLite
- **Communication:** FastAPI, Uvicorn, WebSockets, SSE

---

## 📜 License & Ethics

**MIT License.** 
Friday is built on the principle of **Local-First AI**. Your voice data, embeddings, and chat history never leave your machine unless you explicitly configure a cloud provider.

---

<p align="center">
  <strong>Friday</strong> — Built by <a href="https://github.com/anmol">Anmol</a><br/>
  <em>"The future of AI is local. The future of your Mac is Friday."</em>
</p>
