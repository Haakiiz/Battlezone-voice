"""
executor.py
-----------
Spiller av en handlingsplan (liste med steg) mot spillet:
 - KeyStep -> sender tastetrykk (DirectInput-scancodes, virker i spill)
 - WaitStep -> venter (timer-basert "bygg ferdig")
 - SayStep  -> snakker til deg via Gemini TTS

Tørrkjøring (dry_run=true i config) sender INGEN ekte taster - den
skriver bare ut hva den ville gjort. Bruk det til å verifisere
tastesekvensene trygt før du tester på et ekte spill.
"""

import time

import pydirectinput
from commands import KeyStep, WaitStep, SayStep, Step
from speak import Voice

# Ikke legg inn kunstig forsinkelse mellom hver tast - vi styrer selv.
pydirectinput.PAUSE = 0.0


class Executor:
    def __init__(self, cfg: dict, voice: Voice):
        self.dry_run = bool(cfg.get("dry_run", True))
        self.voice = voice
        # liten pause mellom taster så spillets meny rekker å reagere
        self.key_gap = 0.08

    def _press_keys(self, keys: list[str]) -> None:
        for key in keys:
            if key.upper() == "VERIFISER":
                print(f"   ⚠️  '{key}' - tast ikke satt i config enda, hopper over")
                continue
            if self.dry_run:
                print(f"   [TØRRKJØRING] ville trykket: {key}")
            else:
                pydirectinput.press(key)
            time.sleep(self.key_gap)

    def run(self, steps: list[Step]) -> None:
        for step in steps:
            if isinstance(step, SayStep):
                self.voice.say(step.text)

            elif isinstance(step, KeyStep):
                label = f" ({step.note})" if step.note else ""
                print(f"-> taster {step.keys}{label}")
                self._press_keys(step.keys)

            elif isinstance(step, WaitStep):
                label = f" ({step.note})" if step.note else ""
                print(f"-> venter {step.seconds:.0f}s{label}")
                self._countdown(step.seconds)

    @staticmethod
    def _countdown(seconds: float) -> None:
        end = time.time() + seconds
        while time.time() < end:
            remaining = end - time.time()
            print(f"   ...{remaining:4.0f}s   ", end="\r")
            time.sleep(min(1.0, remaining))
        print(" " * 20, end="\r")
