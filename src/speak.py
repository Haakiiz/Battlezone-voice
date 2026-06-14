"""
speak.py
--------
Stemme tilbake til deg via Gemini TTS. F.eks. "Speiderne er ferdige".
Bruker den beste TTS-modellen for naturlig stemme.

Faller tilbake til ren tekst-utskrift hvis lyd ikke kan spilles av,
så programmet aldri kræsjer av en talemelding.
"""

import numpy as np
import sounddevice as sd
from google import genai
from google.genai import types

# Gemini TTS sender tilbake 24 kHz, 16-bit PCM mono.
TTS_SAMPLE_RATE = 24000


class Voice:
    def __init__(self, cfg: dict, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = cfg["gemini"]["tts_model"]
        self.voice = cfg["gemini"]["tts_voice"]

    def say(self, text: str) -> None:
        print(f"[STEMME] {text}")
        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self.voice
                            )
                        )
                    ),
                ),
            )
            pcm = resp.candidates[0].content.parts[0].inline_data.data
            audio = np.frombuffer(pcm, dtype=np.int16)
            sd.play(audio, samplerate=TTS_SAMPLE_RATE)
            sd.wait()
        except Exception as e:
            # Stemme er "nice to have" - aldri la den stoppe spillingen.
            print(f"[STEMME-feil, fortsetter uten lyd] {e}")
