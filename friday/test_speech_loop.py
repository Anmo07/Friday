import asyncio
import logging
import os
import sys

# Add the project root to sys.path to allow imports from app.*
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("speech_test")

async def test_speech_pipeline():
    try:
        from app.voice import stt, tts
        from app.core.assistant import assistant_orchestrator
        
        logger.info("--- Phase 1: TTS Generation ---")
        # Generate a small audio clip saying "Hello Friday"
        test_text = "Hello Friday, check the weather."
        audio_bytes = await tts.speak(test_text)
        if audio_bytes:
            logger.info(f"TTS generated {len(audio_bytes)} bytes of audio.")
        else:
            logger.error("TTS failed to generate audio.")
            return

        logger.info("--- Phase 2: STT Transcription ---")
        # Now transcribe it back
        # Note: If TTS used MP3 (edge-tts), whisper might need ffmpeg or specific wav format.
        # Faster-whisper handles many formats if ffmpeg is in path.
        transcription = await stt.transcribe(audio_bytes)
        logger.info(f"STT Transcription: '{transcription}'")

        if not transcription:
            logger.warning("STT returned empty string. This might happen if audio is too short or format incompatible.")
        
        logger.info("--- Phase 3: Assistant Execution ---")
        # Run assistant on the transcribed text
        # Using a simple query to keep it fast
        response = await assistant_orchestrator.execute(transcription or test_text)
        logger.info(f"Assistant Summary: {response.get('summary', 'No summary')}")
        logger.info(f"Truth Score: {response.get('truth_score', 'N/A')}")

        logger.info("--- Phase 4: Final TTS Response ---")
        final_audio = await tts.speak(response.get('summary', "Verification complete."))
        logger.info(f"Final TTS generated {len(final_audio)} bytes.")
        
        logger.info("SUCCESS: Full Speech-to-Speech loop logic verified.")

    except Exception as e:
        logger.exception(f"Speech pipeline test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_speech_pipeline())
