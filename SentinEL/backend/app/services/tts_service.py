"""
TTS Service - Google Cloud Text-to-Speech Integration
负责将 AI 生成的通话脚本转换为高质量语音 (Neural2)
"""

try:
    from google.cloud import texttospeech
    _HAS_TTS = True
except ImportError:
    _HAS_TTS = False
    texttospeech = None

import base64
import logging
from app.core import telemetry

logger = logging.getLogger(__name__)
tracer = telemetry.get_tracer()

class TTSService:
    def __init__(self):
        if _HAS_TTS:
            try:
                self.client = texttospeech.TextToSpeechClient()
                
                # Configuration - Chinese Voice for this User Context
                # Using Wavenet-D (Female) which is more stable and available
                self.voice = texttospeech.VoiceSelectionParams(
                    language_code="cmn-CN",
                    name="cmn-CN-Wavenet-D" 
                )
                
                self.audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                    speaking_rate=1.0, 
                    pitch=0.0
                )
                # 确认初始化成功
                print("✅ TTS Service initialized successfully with voice: cmn-CN-Wavenet-D")
                logger.info("TTS Service initialized successfully with voice: cmn-CN-Wavenet-D")
            except Exception as e:
                logger.error(f"Failed to initialize TTS Client: {e}")
                self.client = None
        else:
            logger.warning("TTS Service disabled (dependency missing)")
            self.client = None

    def generate_voicemail_audio(self, text: str) -> str:
        """
        Generates audio from text and returns Base64 encoded MP3 string.
        
        Trace Span: "TTS: Generate Audio"
        """
        logger.info(f"TTS generate_voicemail_audio called with text length: {len(text) if text else 0}")
        print(f"🎤 TTS generate_voicemail_audio called, text length: {len(text) if text else 0}")
        if not self.client:
             logger.warning("TTS Client is not available - audio will not be generated.")
             return None

        with tracer.start_as_current_span("TTS: Generate Audio") as span:
            span.set_attribute("input.text_length", len(text))
            
            try:
                synthesis_input = texttospeech.SynthesisInput(text=text)

                response = self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=self.voice,
                    audio_config=self.audio_config
                )

                # Convert binary audio content to Base64 string for easy frontend consumption
                audio_base64 = base64.b64encode(response.audio_content).decode("utf-8")
                
                span.set_attribute("output.audio_size_bytes", len(response.audio_content))
                return audio_base64
                
            except Exception as e:
                span.set_attribute("error", True)
                logger.error(f"Error generating TTS: {e}")
                # Return None or raise to let orchestrator handle graceful degradation
                return None
