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
- `build_times.<unit>` are seconds. Each unit has a **fixed** build time in BZ98
  (not scrap-dependent); the current values are estimates pending the user's
  in-game numbers.
- The `keymap` is **data-driven** — adding/changing a command means editing
  config, and `commands.py:CommandPlanner` consumes these sections generically:
  - `keymap.build.<unit>` / `keymap.produce.<item>` = `[<producer/armory key>, <menu slot>]`
    (5 = Recycler, 6 = Factory; producer keys are BZ98 defaults, slots are estimates).
  - `keymap.select.<target>` = how to select a unit group before an order
    (`all_offensive` = `ctrl+1`, etc.). Orders carry an optional `target`.
  - `keymap.commands.<action>` = the order key (`follow`/`hold` are confirmed
    BZ98 defaults; the rest are estimates). `command_menu_key` (e.g. `tab`) is
    pressed first if set; `nav_beacon` is a standalone key.
- Chord strings use `+` (e.g. `"ctrl+1"`), handled by `executor.py:_press_chord`;
  plain entries are single key taps. `DEFAULT_TARGET`/`CONFIRM` in `commands.py`
  set the fallback selection and spoken reply per action.

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
