"""
main.py
-------
Limet som binder alt sammen. Push-to-talk-loop:

  1. Hold push-to-talk-tasten (caps lock) og si en kommando
  2. Gemini hører lyden og lager en handlingsplan
  3. Planlegger gjør planen om til taster + ventetid + talemeldinger
  4. Executor spiller det av (tørrkjøring som standard)

Avslutt med Esc.
"""

import os
import sys
from pathlib import Path

import yaml
import keyboard
from dotenv import load_dotenv

from listen import record_while_held
from brain import Brain
from commands import CommandPlanner
from executor import Executor
from speak import Voice


def load_config() -> dict:
    cfg_path = Path(__file__).resolve().parent.parent / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit("Mangler GEMINI_API_KEY. Kopier .env.example til .env og lim inn nøkkelen.")

    cfg = load_config()
    ptt = cfg["controls"]["push_to_talk"]
    quit_key = cfg["controls"]["quit_key"]
    sample_rate = cfg["audio"]["sample_rate"]

    voice = Voice(cfg, api_key)
    brain = Brain(cfg, api_key)
    planner = CommandPlanner(cfg)
    executor = Executor(cfg, voice)

    mode = "TØRRKJØRING (ingen ekte tastetrykk)" if executor.dry_run else "EKTE (sender taster til spillet)"
    print("=" * 60)
    print("  Battlezone Voice Commander")
    print(f"  Modus: {mode}")
    print(f"  Hold '{ptt}' og snakk. Avslutt med '{quit_key}'.")
    print("=" * 60)

    while True:
        if keyboard.is_pressed(quit_key):
            print("\nAvslutter. Ha det, sjef.")
            break

        print(f"\n🎙️  Hold '{ptt}' og gi en kommando...")
        pcm = record_while_held(ptt, sample_rate)
        if pcm.size == 0:
            continue

        print("🧠  Tolker...")
        orders = brain.understand(pcm)
        if not orders:
            print("   (forsto ikke kommandoen - prøv igjen)")
            continue

        print(f"   Forsto: {orders}")
        steps = planner.plan(orders)
        executor.run(steps)


if __name__ == "__main__":
    main()
