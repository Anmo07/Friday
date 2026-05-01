# Friday Speech Recognition & Processing Report

This report details the inner workings of Friday's voice interaction system, covering audio capture, calibration, transcription, and response synthesis.

## 1. Audio Capture & Calibration

Friday uses a sophisticated energy-based detection system to manage voice input without requiring a manual push-to-talk button for every interaction.

### Calibration Mechanisms
- **Energy Detection (RMS):** The system calculates the Root Mean Square (RMS) value of incoming audio chunks in real-time.
- **Wake Threshold:** A calibrated `energy_threshold` (default: 1200.0) is used to distinguish background noise from human speech.
- **Silence Timeout:** To detect the end of an utterance, Friday monitors for silence. If the energy drops below 30% of the threshold for a sustained period (`silence_timeout`, default: 3.0s), the system concludes the user has finished speaking.

### Data Processing Flow
1. **Continuous Monitoring:** The `VoiceListener` listens in 1024-sample chunks at a 16kHz sample rate.
2. **Wake Trigger:** When RMS exceeds the `energy_threshold`, the system enters "Capture Mode."
3. **Utterance Buffering:** Audio is collected into a continuous buffer.
4. **Dynamic Termination:** Capture stops when silence is detected or a maximum duration (10 seconds) is reached to prevent infinite loops.

## 2. Speech-to-Text (STT) Processing

Once an audio utterance is captured, it is processed by the `STTService`.

### The Engine
Friday utilizes **Faster-Whisper (Large V3 Turbo)**, a high-performance implementation of OpenAI's Whisper model optimized for speed and accuracy.

### Calibration & Optimization
- **VAD Filter:** Voice Activity Detection (VAD) is applied during transcription to filter out non-speech artifacts and reduce hallucination.
- **Min Silence Duration:** Set to 250ms (optimized for short phrases like "Hello Friday") to ensure natural pauses within a sentence don't fragment the transcription.
- **Contextual Prompting:** An `initial_prompt` ("Friday assistant loop.") is provided to the model to prime it for conversational assistant interactions.

## 3. Intelligence & Response Generation

The transcribed text is passed to the `FridayPipeline`, which determines the best response strategy.

- **Classification:** The `SemanticRouter` categorizes the query into Fast, Standard, or Deep tiers.
- **Context Integration:** Depending on the tier, Friday retrieves relevant data from its Vector Database (Chroma) and Knowledge Graph (Neo4j).
- **Emotion Detection:** Friday analyzes the user's intent and keywords to detect emotions like "Urgent," "Concerned," or "Positive."

## 4. Response Synthesis & Delivery (TTS)

The final response is converted back to speech via the `TTSService`.

### Neural Synthesis
- **Engine:** Friday uses `edge-tts` (Microsoft Edge Neural Voices) for human-like prosody.
- **Default Voice:** `en-US-JennyNeural`.
- **Emotional Calibration:** Based on the detected emotion, the TTS engine dynamically adjusts:
  - **Rate:** Speed increases for "Urgent" (+15%) and decreases for "Negative" (-5%).
  - **Pitch:** Adjusts to match the emotional tone (e.g., +5Hz for "Urgent" vs -3Hz for "Negative").

### Performance Features
- **Streaming TTS:** Audio chunks are streamed as they are synthesized, significantly reducing the "Time To First Audio" (TTFA) and allowing for sub-200ms perceived response times.
- **Text Cleaning:** Markdown symbols and artifacts are stripped before synthesis to ensure smooth delivery.
