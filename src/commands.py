"""
commands.py
-----------
Oversetter en HØYNIVÅ handlingsplan fra Gemini (f.eks. "bygg 2 scouts,
deretter follow me") til en flat liste av LAVNIVÅ steg som executor.py
kan spille av: tastetrykk, ventetid og talemeldinger.

Hele poenget med dette laget: Gemini trenger ALDRI å vite hvilke taster
spillet bruker. Den sier bare HVA du vil, og denne fila slår opp HVORDAN
i config.yaml. Da kan du endre tastebindinger uten å røre AI-en.
"""

from dataclasses import dataclass


# ---- Lavnivå steg som executor forstår -----------------------------------

@dataclass
class KeyStep:
    keys: list[str]          # tastesekvens, f.eks. ["tab", "3", "3"]
    note: str = ""           # menneskelig beskrivelse (for tørrkjøring/logg)

@dataclass
class WaitStep:
    seconds: float
    note: str = ""

@dataclass
class SayStep:
    text: str                # det stemmen skal si tilbake til deg


Step = KeyStep | WaitStep | SayStep


# ---- Schema som Gemini fyller ut (function calling) ----------------------
# Dette er "verktøyet" Gemini kaller. Beskrivelsene er det modellen leser,
# så de er bevisst tydelige.

ORDERS_TOOL = {
    "name": "execute_orders",
    "description": (
        "Utfør en eller flere ordre i Battlezone, i rekkefølge. "
        "Bruk dette når brukeren gir kommandoer til enhetene sine."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "orders": {
                "type": "array",
                "description": "Ordrene i den rekkefølgen de skal utføres.",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["build", "follow", "hold", "attack", "stop"],
                            "description": "Hva som skal gjøres.",
                        },
                        "unit": {
                            "type": "string",
                            "description": "Enhetstype, f.eks. 'scout', 'tank'. "
                                           "Kun relevant for action=build.",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Antall enheter å bygge. Standard 1.",
                        },
                    },
                    "required": ["action"],
                },
            }
        },
        "required": ["orders"],
    },
}


# ---- Oversetter: ordre -> lavnivå steg -----------------------------------

class CommandPlanner:
    def __init__(self, cfg: dict):
        self.km = cfg["keymap"]
        self.build_times = cfg["build_times"]

    def _build_time(self, unit: str) -> float:
        return float(self.build_times.get(unit, self.build_times["default"]))

    def plan(self, orders: list[dict]) -> list[Step]:
        """Gjør en liste med ordre om til en flat steg-liste."""
        steps: list[Step] = []
        last_built_unit: str | None = None

        for order in orders:
            action = order.get("action")

            if action == "build":
                unit = (order.get("unit") or "scout").lower()
                count = int(order.get("count") or 1)
                last_built_unit = unit
                steps.append(SayStep(f"Bygger {count} {unit}."))
                keys = self.km["build"].get(unit)
                for i in range(count):
                    if keys:
                        steps.append(KeyStep(list(keys), f"bygg {unit} #{i+1}"))
                    steps.append(WaitStep(self._build_time(unit),
                                          f"venter på {unit} #{i+1}"))
                steps.append(SayStep(
                    f"{count} {unit} er ferdig." if count > 1
                    else f"{unit} er ferdig."))

            elif action == "follow":
                # velg de sist bygde enhetene, så deg selv, så "follow me"
                if "select_last_built" in self.km:
                    steps.append(KeyStep(list(self.km["select_last_built"]),
                                         "velg sist bygde enheter"))
                steps.append(KeyStep(list(self.km["follow_me"]), "follow me"))
                steps.append(SayStep("De følger deg nå."))

            elif action in ("hold", "stop"):
                steps.append(KeyStep(list(self.km.get(action, self.km["hold"])),
                                     action))
                steps.append(SayStep("Holder posisjon."))

            elif action == "attack":
                steps.append(KeyStep(list(self.km["attack"]), "attack"))
                steps.append(SayStep("Angriper."))

        return steps
