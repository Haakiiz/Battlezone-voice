# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Voice-controlled commander for **Battlezone 98 (Windows, 1998)**. The user
holds push-to-talk, speaks Norwegian, and the program presses the in-game keys
and speaks confirmations back. The whole UI/comments are in Norwegian — keep it
that way.

## Run / setup

```bash
pip install -r requirements.txt          # google-genai, sounddevice, keyboard, pydirectinput, PyYAML, python-dotenv
cp .env.example .env                      # then paste a Gemini key from aistudio.google.com/apikey
python src/main.py                        # hold Caps Lock to talk, Esc to quit
```

There is **no test suite, linter, or build step**. Sanity-check changes with:

```bash
python3 -m py_compile src/*.py
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

Note: `keyboard` and `pydirectinput` are Windows/game-runtime libraries and
generally won't import or function in a headless Linux sandbox — do not try to
actually run `main.py` here; rely on `py_compile` and config validation instead.

## Architecture: a 4-stage pipeline

Audio flows through one loop in `src/main.py`:

```
listen.py  -> brain.py    -> commands.py   -> executor.py (+ speak.py)
record mic    Gemini turns    orders become    plays steps: key presses,
audio         audio into a    low-level steps  timed waits, spoken replies
              list of orders
```

The **load-bearing design rule**: Gemini never knows the game's key bindings. It
only emits intent — a list of orders like `[{action: build, unit: scout, count: 2}, {action: follow}]`
via the `execute_orders` function-calling tool (schema in `commands.py:ORDERS_TOOL`).
`commands.py:CommandPlanner` is the only place that maps intent → keys by looking
them up in `config.yaml`. So changing key bindings or build timings means editing
`config.yaml`, never the Python.

Three low-level step types (`commands.py`): `KeyStep`, `WaitStep`, `SayStep`.
`executor.py` is the only thing that interprets them.

## config.yaml is the control panel

All tunables live here, not in code: model names, push-to-talk/quit keys, the
`keymap` (per-unit build sequences + command keys), and `build_times` (the
timer-based "unit is finished" estimates that drive `WaitStep`).

- `dry_run: true` (default) means **no real key presses** — `executor.py` only
  prints what it *would* press. Always keep this on until key sequences are
  verified in-game; only the user can flip it to `false`.
- `keymap.build.<unit>` is `[<producer key>, <menu slot>]`. In BZ98: **5** opens
  the Recycler build menu, **6** the Factory. The producer key is a known BZ98
  default; the menu-slot number is an *estimate* the user must confirm in-game.
- `keymap.select_last_built` uses a chord string (`"ctrl+1"` = all offensive
  units). Chords are written with `+` and handled by `executor.py:_press_chord`;
  plain entries are single key taps.

## Gemini specifics (verify model IDs before changing)

- Brain (audio → orders): `gemini-3.5-flash`. Audio is wrapped as WAV bytes
  (`brain.py:_pcm_to_wav_bytes`) and sent via `types.Part.from_bytes`; orders are
  read from `response.function_calls`.
- TTS (text → voice): `gemini-3.1-flash-tts-preview`, output is 24 kHz int16 PCM
  read from `response.candidates[0].content.parts[0].inline_data.data`
  (`speak.py`). `Voice.say` is intentionally fail-soft — it must never crash the
  loop, only fall back to printing text.

Model IDs move fast; the comments in `config.yaml` list the current alternatives
(`gemini-3.1-pro`, `gemini-3.1-flash-lite`). When changing a model, confirm the
exact ID against current Google docs rather than guessing.
