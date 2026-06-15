"""
commands.py
-----------
Oversetter en HØYNIVÅ handlingsplan fra Gemini (f.eks. "be alle om å
følge meg, så angrip basen") til en flat liste av LAVNIVÅ steg som
executor.py kan spille av: tastetrykk, ventetid og talemeldinger.

Hele poenget med dette laget: Gemini trenger ALDRI å vite hvilke taster
spillet bruker. Den sier bare HVA du vil (action + ev. unit/target), og
denne fila slår opp HVORDAN i config.yaml. Da kan du endre tastebindinger
- eller legge til nye kommandoer - uten å røre AI-en.
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
# så de er bevisst tydelige - dekker hele BZ98-kommandorepertoaret.

ORDERS_TOOL = {
    "name": "execute_orders",
    "description": (
        "Utfør en eller flere ordre i Battlezone, i rekkefølge. Bruk dette "
        "når brukeren gir kommandoer til enhetene sine - bygging, bevegelse, "
        "angrep, forsvar, scavenging, nav-beacons, våpenproduksjon, osv."
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
                            "enum": [
                                "build",     # bygg enhet (Recycler/Factory)
                                "produce",   # produser våpen/spesial (Armory)
                                "follow",    # enheter følger deg
                                "go",        # flytt til der du ser / til nav
                                "attack",    # angrip mål
                                "hold",      # hold posisjon
                                "stop",      # stopp
                                "defend",    # forsvar posisjon/deg
                                "scavenge",  # scavengers samler scrap
                                "get",       # plukk opp / hent objekt
                                "nav",       # plasser nav-beacon
                            ],
                            "description": "Hva som skal gjøres.",
                        },
                        "unit": {
                            "type": "string",
                            "description": (
                                "Hva som skal bygges/produseres, f.eks. 'scout', "
                                "'tank', 'scavenger', 'constructor', 'walker', "
                                "'day_wrecker'. Kun for action=build eller produce."
                            ),
                        },
                        "count": {
                            "type": "integer",
                            "description": "Antall å bygge. Standard 1.",
                        },
                        "target": {
                            "type": "string",
                            "enum": [
                                "self", "all_offensive", "all_defensive",
                                "all_utility", "scavengers", "last_built",
                            ],
                            "description": (
                                "Hvilke enheter ordren gjelder. F.eks. 'be ALLE "
                                "følge meg' -> all_offensive; 'scavengerne skal "
                                "samle' -> scavengers. Utelat for å bruke standard."
                            ),
                        },
                    },
                    "required": ["action"],
                },
            }
        },
        "required": ["orders"],
    },
}


# ---- Standardvalg + bekreftelser pr. kommando ----------------------------
# Hvilken enhetsgruppe en ordre gjelder hvis brukeren ikke spesifiserer det.
DEFAULT_TARGET = {
    "follow": "all_offensive",
    "go": "all_offensive",
    "attack": "all_offensive",
    "hold": "all_offensive",
    "stop": "all_offensive",
    "defend": "all_offensive",
    "scavenge": "scavengers",
    "get": "all_utility",
}

# Det stemmen sier når en kommando er utført.
CONFIRM = {
    "follow": "De følger deg nå.",
    "go": "På vei.",
    "attack": "Angriper.",
    "hold": "Holder posisjon.",
    "stop": "Stopper.",
    "defend": "Forsvarer.",
    "scavenge": "Scavengerne samler scrap.",
    "get": "Henter.",
    "nav": "Nav-beacon plassert.",
}


# ---- Oversetter: ordre -> lavnivå steg -----------------------------------

class CommandPlanner:
    def __init__(self, cfg: dict):
        self.km = cfg["keymap"]
        self.build_times = cfg["build_times"]

    def _build_time(self, unit: str) -> float:
        return float(self.build_times.get(unit, self.build_times["default"]))

    def _select_step(self, target: str | None) -> KeyStep | None:
        """KeyStep for å velge målgruppen før en ordre, eller None."""
        if not target:
            return None
        keys = self.km.get("select", {}).get(target)
        return KeyStep(list(keys), f"velg {target}") if keys else None

    def _menu_open_step(self) -> KeyStep | None:
        """Åpne ordremenyen (Tab e.l.) hvis konfigurert."""
        key = self.km.get("command_menu_key")
        return KeyStep([key], "åpne ordremeny") if key else None

    def plan(self, orders: list[dict]) -> list[Step]:
        """Gjør en liste med ordre om til en flat steg-liste."""
        steps: list[Step] = []

        for order in orders:
            action = order.get("action")
            target = order.get("target")

            if action == "build":
                self._plan_build(order, steps)

            elif action == "produce":
                self._plan_produce(order, steps)

            elif action == "nav":
                keys = self.km.get("nav_beacon")
                if keys:
                    steps.append(KeyStep(list(keys), "nav-beacon"))
                steps.append(SayStep(CONFIRM["nav"]))

            else:
                self._plan_command(action, target, steps)

        return steps

    # -- delplanleggere ----------------------------------------------------

    def _plan_build(self, order: dict, steps: list[Step]) -> None:
        unit = (order.get("unit") or "scout").lower()
        count = int(order.get("count") or 1)
        keys = self.km["build"].get(unit)
        steps.append(SayStep(f"Bygger {count} {unit}."))
        for i in range(count):
            if keys:
                steps.append(KeyStep(list(keys), f"bygg {unit} #{i+1}"))
            steps.append(WaitStep(self._build_time(unit), f"venter på {unit} #{i+1}"))
        steps.append(SayStep(
            f"{count} {unit} er ferdig." if count > 1 else f"{unit} er ferdig."))

    def _plan_produce(self, order: dict, steps: list[Step]) -> None:
        item = (order.get("unit") or "weapon").lower()
        keys = self.km.get("produce", {}).get(item)
        steps.append(SayStep(f"Lager {item}."))
        if keys:
            steps.append(KeyStep(list(keys), f"produser {item}"))

    def _plan_command(self, action: str, target: str | None,
                      steps: list[Step]) -> None:
        keys = self.km.get("commands", {}).get(action)
        if not keys:
            return                      # ukjent kommando - hopp over
        sel = self._select_step(target or DEFAULT_TARGET.get(action))
        if sel:
            steps.append(sel)
        menu = self._menu_open_step()
        if menu:
            steps.append(menu)
        steps.append(KeyStep(list(keys), action))
        steps.append(SayStep(CONFIRM.get(action, "Utført.")))
