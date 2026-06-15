"""
listen.py
---------
Mikrofon-opptak med push-to-talk: tar opp lyd så lenge du holder
push-to-talk-tasten inne, og returnerer lyden som int16 numpy-array.

VIKTIG: vi bruker nivåbasert `keyboard.is_pressed()`-polling, IKKE
`keyboard.wait()`. `wait()` bygger på add_hotkey(), som er upålitelig
for rene modifikatortaster (shift/ctrl/alt) - den kan slutte å utløses
etter noen trykk og henge programmet. is_pressed() leser tastens
faktiske tilstand og virker likt for vanlige taster og modifikatorer.
"""

import time

import numpy as np
import sounddevice as sd
import keyboard

_POLL = 0.02   # sekunder mellom hver tastesjekk


def wait_for_ptt(ptt_key: str, quit_key: str) -> bool:
    """
    Vent på et RENT push-to-talk-trykk. Returnerer True når tasten
    trykkes, eller False hvis quit_key trykkes i stedet (så hovedløkka
    kan avslutte). Venter først til ptt er sluppet - det rydder opp i en
    evt. fastlåst tastetilstand før vi venter på et nytt trykk.
    """
    while keyboard.is_pressed(ptt_key):           # selv-helbred: vent til sluppet
        if keyboard.is_pressed(quit_key):
            return False
        time.sleep(_POLL)
    while not keyboard.is_pressed(ptt_key):       # vent på friskt trykk
        if keyboard.is_pressed(quit_key):
            return False
        time.sleep(_POLL)
    return True


def record_while_held(ptt_key: str, sample_rate: int) -> np.ndarray:
    """
    Ta opp mens push-to-talk holdes. Forutsetter at tasten ALLEREDE er
    nede (kall wait_for_ptt() først). Returnerer mono int16-lyd.
    """
    frames: list[np.ndarray] = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    with sd.InputStream(samplerate=sample_rate, channels=1,
                        dtype="int16", callback=callback):
        while keyboard.is_pressed(ptt_key):       # ta opp mens du holder
            sd.sleep(50)

    if not frames:
        return np.zeros(0, dtype=np.int16)
    return np.concatenate(frames, axis=0).flatten()
