"""
listen.py
---------
Mikrofon-opptak med push-to-talk: tar opp lyd så lenge du holder
push-to-talk-tasten inne, og returnerer lyden som int16 numpy-array.
"""

import numpy as np
import sounddevice as sd
import keyboard


def record_while_held(ptt_key: str, sample_rate: int) -> np.ndarray:
    """
    Blokker til push-to-talk-tasten trykkes, ta opp mens den holdes,
    stopp når den slippes. Returnerer mono int16-lyd.
    """
    keyboard.wait(ptt_key)                       # vent på at du trykker
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
