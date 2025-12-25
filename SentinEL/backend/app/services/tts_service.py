"""
TTS Service - Google Cloud Text-to-Speech Integration
负责将 AI 生成的通话脚本转换为高质量语音 (Neural2)
"""

from google.cloud import texttospeech
import base64
from app.core import telemetry

tracer = telemetry.get_tracer()

class TTSService:
    def __init__(self):
        self.client = texttospeech.TextToSpeechClient()
        
        # Configuration - High Quality "Neural2" Voice
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-F"  # Female, highly natural
            # Alternatives: en-US-Studio-M (Male, Studio quality)
        )
        
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0, # Natural pacing
            pitch=0.0
        )

    def generate_voicemail_audio(self, text: str) -> str:
        """
        Generates audio from text and returns Base64 encoded MP3 string.
        
        Trace Span: "TTS: Generate Audio"
        """
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
                print(f"Error generating TTS: {e}")
                # Return None or raise to let orchestrator handle graceful degradation
                return None
