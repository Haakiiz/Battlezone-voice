"""
brain.py
--------
Sender mikrofon-lyden din til Gemini og får tilbake en strukturert
handlingsplan (via function calling). Gemini hører hva du sier på norsk,
forstår intensjonen, og kaller verktøyet execute_orders med en liste ordre.

Vi bruker gemini-3.5-flash (se config.yaml) fordi den både forstår
lyd direkte og er sterk på function calling - da slipper vi et eget
tale-til-tekst-steg. Bytt til gemini-3.1-pro i config hvis Flash
misforstår deg ofte.
"""

import io
import wave

import numpy as np
from google import genai
from google.genai import types

from commands import ORDERS_TOOL


SYSTEM_INSTRUCTION = (
    "Du er en kommando-tolk for spillet Battlezone. Brukeren snakker norsk "
    "og gir militære ordre til enhetene sine. Oversett ALT de sier til ett "
    "eller flere strukturerte kall til execute_orders, i riktig rekkefølge.\n"
    "Du kan uttrykke hele repertoaret via action: build (bygg enhet), "
    "produce (lag våpen/spesial i Armory), follow, go (flytt), attack, hold, "
    "stop, defend, scavenge (samle scrap), get (plukk opp), nav (nav-beacon).\n"
    "Bruk 'target' for HVEM ordren gjelder: si f.eks. 'be alle om å følge meg' "
    "-> follow med target=all_offensive; 'scavengerne skal samle' -> scavenge "
    "med target=scavengers.\n"
    "Eksempler:\n"
    "  'bygg to speidere og la dem følge meg' -> build(unit=scout,count=2), "
    "follow(target=last_built)\n"
    "  'alle enheter angrip' -> attack(target=all_offensive)\n"
    "  'lag en day wrecker' -> produce(unit=day_wrecker)\n"
    "  'sett en nav-beacon' -> nav\n"
    "Hvis du ikke forstår en kommando, ikke kall verktøyet."
)


def _pcm_to_wav_bytes(pcm: np.ndarray, sample_rate: int) -> bytes:
    """Pakk rå int16-lyd inn i et WAV-format Gemini godtar."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)            # int16
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


class Brain:
    def __init__(self, cfg: dict, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = cfg["gemini"]["brain_model"]
        self.sample_rate = cfg["audio"]["sample_rate"]
        self.tool = types.Tool(function_declarations=[ORDERS_TOOL])

    def understand(self, pcm: np.ndarray) -> list[dict]:
        """Lyd inn -> liste med ordre ut (tom liste hvis ikke forstått)."""
        wav = _pcm_to_wav_bytes(pcm, self.sample_rate)

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Content(role="user", parts=[
                    types.Part.from_bytes(data=wav, mime_type="audio/wav"),
                ]),
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[self.tool],
                temperature=0.0,        # vil ha forutsigbar tolkning
            ),
        )

        # Plukk ut function call-argumentene
        for call in (response.function_calls or []):
            if call.name == "execute_orders":
                return list(call.args.get("orders", []))
        return []
