# Battlezone Voice Commander

Snakk i mikrofonen ("bygg meg to speidere og la dem følge meg") → Gemini
forstår norsk tale → programmet trykker tastene i Battlezone 98 for deg,
venter på at enhetene bygges, og **snakker tilbake** når de er ferdige.

## Arkitektur (3 lag)

```
  Mikrofon ──► [ LYTT ]  push-to-talk-opptak        (listen.py)
                   │
                   ▼
            [ TOLK ]  Gemini 3.5 Flash hører lyden   (brain.py)
                   │   og lager en handlingsplan
                   ▼
            [ PLANLEGG ]  ordre → taster + ventetid  (commands.py)
                   │
                   ▼
            [ UTFØR ]  sender taster + snakker        (executor.py + speak.py)
```

Gemini vet **aldri** hvilke taster spillet bruker — den sier bare *hva* du
vil. Tastene bor i `config.yaml`, så du kan endre dem uten å røre koden.

## Modeller (juni 2026, det beste som finnes)

| Lag | Modell |
|-----|--------|
| Tale → handling | `gemini-3.5-flash` (hører lyd + function calling) |
| Stemme tilbake | `gemini-3.1-flash-tts-preview` |

## Kommandoer du kan gi med stemmen

Alt i BZ98s kommandomeny er tilgjengelig — Gemini oversetter fritt norsk
til disse handlingene (`commands.py:ORDERS_TOOL`):

| Du sier (eksempel) | Handling |
|--------------------|----------|
| "bygg to speidere" | `build` (Recycler/Factory/Constructor) |
| "lag en day wrecker" | `produce` (Armory-våpen) |
| "alle skal følge meg" | `follow` / `follow_close` |
| "dra dit borte" / "til navet" | `go` |
| "angrip basen" | `attack` |
| "jakt på fiender" | `hunt` |
| "hold posisjon" / "stopp" | `hold` / `stop` |
| "forsvar her" | `defend` |
| "scavengerne skal samle scrap" | `scavenge` |
| "plukk opp den" | `pickup` |
| "dra og reparer" / "fyll ammo" | `repair` / `reload` |
| "send den til gjenvinning" | `recycle` |
| "sett en nav-beacon" | `nav` |

**Hva kan bygges/produseres?** Hele BZ98-menytreet ligger i `config.yaml`
under `keymap.build` (Recycler/Factory/Constructor) og `keymap.produce`
(Armory med under­menyer for kanoner, raketter, mortar og spesialvåpen).
Si f.eks. "bygg en walker", "lag et gun tower", "produser en flash cannon".

Du kan også styre **hvem** ordren gjelder ("be *alle* følge meg",
"*scavengerne* skal samle") — det blir `target` i ordren. Hvilke taster
hver handling sender bor i `config.yaml` under `keymap`, så du kan legge
til eller endre kommandoer uten å røre koden.

## Oppsett (engangs, ~5 min)

1. Installer [Python 3.11+](https://www.python.org/downloads/) (huk av "Add to PATH").
2. Åpne PowerShell i denne mappa og kjør:
   ```powershell
   pip install -r requirements.txt
   ```
3. Hent en API-nøkkel på https://aistudio.google.com/apikey
4. Kopier `.env.example` til `.env` og lim inn nøkkelen.

## Bruk

```powershell
python src/main.py
```

- Hold **push-to-talk-tasten** (`controls.push_to_talk` i config, standard
  satt der) og si en kommando. Slipp for å sende.
- Avslutt med **Esc**.

> 💡 Push-to-talk leses nivåbasert (`keyboard.is_pressed`), så modifikator­taster
> som **venstre Shift/Ctrl** fungerer fint. (Tidligere brukte vi `keyboard.wait`,
> som hang etter noen trykk med modifikatortaster.)

### Får ikke push-to-talk til å virke mens spillet kjører?

`keyboard`-biblioteket bruker en **global** tastaturhook, så du trenger
*ikke* ha terminalen/PyCharm i fokus — start programmet én gang og alt-tab
inn i spillet. Hvis tasten likevel ikke registreres mens BZ98 har fokus:

1. **Kjør terminalen som administrator.** Hvis spillet kjører som admin må
   Python gjøre det også, ellers blokkerer Windows (UIPI) tastetrykkene.
2. **Kjør BZ98 i «Windowed»/«Borderless», ikke ekte fullskjerm** — exclusive
   fullscreen kan sluke globale hooks og ødelegger lyd-avspilling + alt-tab.
3. Unngå toggle-taster som Caps Lock som PTT; en ren tast (f.eks.
   `"left shift"` / `"right ctrl"`) er bedre. Endre `controls.push_to_talk`
   i `config.yaml`.

> ⚠️ Programmet starter i **tørrkjøring** (`dry_run: true` i config). Da
> sender den **ingen ekte tastetrykk** — den skriver bare ut hva den ville
> gjort. Test først her, verifiser at sekvensene stemmer, og sett deretter
> `dry_run: false` for å spille på ekte.

## Det vi må gjøre sammen før det funker på ekte

Menyene i `config.yaml` (`keymap.build` / `keymap.produce`) er fylt inn fra
[StrategyWiki](https://strategywiki.org/wiki/Battlezone_(Activision)/CCA_units)
(NSDF og CCA har identiske menyer, kun andre navn):

- **5** = Recycler, **6** = Factory (bekreftet). **7** = Armory og
  **8** = Constructor er standard utvalgstaster — *verifiser in-game*.
- Andre tallet i hver sekvens er PLASSEN i menyen; Armory-våpen har et
  tredje tall for under­menyen (f.eks. `flash_cannon: ["7","6","5"]`).
- **Constructor-bygninger** (gun tower, barracks osv.) kan ikke plasseres
  helt automatisk: boten trykker tast + slot, men *du* må sikte og trykke
  **Space** for å sette ned bygningen.

Kjør med `dry_run: true` og sjekk at sekvensen i terminalen matcher menyen
din før du setter `dry_run: false`.

Defaults som allerede stemmer i BZ98: **Follow Me = 1**, **Go to Nav = 2**.

## Filer

| Fil | Ansvar |
|-----|--------|
| `src/main.py` | push-to-talk-loop, limer alt sammen |
| `src/listen.py` | mikrofon-opptak |
| `src/brain.py` | Gemini: lyd → strukturert handlingsplan |
| `src/commands.py` | ordre → taster/ventetid/tale + Gemini-verktøyskjema |
| `src/executor.py` | spiller av planen (tørrkjøring eller ekte taster) |
| `src/speak.py` | Gemini TTS-stemme tilbake |
| `config.yaml` | alle innstillinger: modeller, taster, byggetider |
