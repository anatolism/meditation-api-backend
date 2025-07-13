# meditation_api/voice_service.py

import os
import base64
import struct
import tempfile
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class MeditationVoiceService:
    def __init__(self, preferred_voice="Aoede"):
        """Initialize voice service with preferred voice"""
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.preferred_voice = preferred_voice
        # Use the EXACT instructions from your working test
        self.meditation_instructions = (
            "Read aloud in a warm and friendly tone for calming meditation students. "
            "Don't change intonation much, very calm, smooth and slow. "
            "Use a mildly British / Chinese / Indeterminate accent."
        )
    
    def generate_audio(self, text: str, voice_name: str = None) -> bytes:
        """Generate meditation audio and return as WAV bytes"""
        voice = voice_name or self.preferred_voice
        
        # Use EXACT same format as your working test
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=self.meditation_instructions),
                    types.Part.from_text(text=text),
                ],
            ),
        ]
        
        # Use EXACT same config as your working test
        config = types.GenerateContentConfig(
            temperature=1,  # Changed to match your working test
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                )
            ),
        )
        
        try:
            audio_data = b""
            
            # Use EXACT same streaming logic as your working test
            for chunk in self.client.models.generate_content_stream(
                model="gemini-2.5-flash-preview-tts",
                contents=contents,
                config=config,
            ):
                if (chunk.candidates and 
                    chunk.candidates[0].content and 
                    chunk.candidates[0].content.parts and
                    chunk.candidates[0].content.parts[0].inline_data):
                    
                    inline_data = chunk.candidates[0].content.parts[0].inline_data
                    try:
                        if isinstance(inline_data.data, bytes):
                            decoded_data = base64.b64decode(inline_data.data)
                        else:
                            decoded_data = base64.b64decode(inline_data.data.encode())
                    except Exception:
                        decoded_data = inline_data.data
                    audio_data += decoded_data
            
            if audio_data:
                # Use EXACT same WAV creation as your working test
                return self._create_wav_file(audio_data)
            else:
                raise Exception("No audio data received")
                
        except Exception as e:
            print(f"Voice generation error: {e}")
            raise
    
    def _create_wav_file(self, audio_data: bytes) -> bytes:
        """Create WAV file with proper header - EXACT same as your test"""
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", len(audio_data) + 36, b"WAVE", b"fmt ", 16, 1,
            1, 24000, 48000, 2, 16, b"data", len(audio_data)
        )
        return header + audio_data