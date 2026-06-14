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

- Hold **Caps Lock** og si en kommando. Slipp for å sende.
- Avslutt med **Esc**.

> ⚠️ Programmet starter i **tørrkjøring** (`dry_run: true` i config). Da
> sender den **ingen ekte tastetrykk** — den skriver bare ut hva den ville
> gjort. Test først her, verifiser at sekvensene stemmer, og sett deretter
> `dry_run: false` for å spille på ekte.

## Det vi må gjøre sammen før det funker på ekte

Bygge-tastene i `config.yaml` (`keymap.build.*`) har nå **kvalifiserte
forslag** basert på BZ98s standardoppsett:

- **5** åpner Recycler-byggmenyen, **6** åpner Factory-byggmenyen.
- Det andre tallet i hver sekvens er PLASSEN enheten har i menyen — det
  er et anslag du må lese av og bekrefte in-game.
- `select_last_built` er satt til **Ctrl+1** (alle offensive enheter).

Battlezone bygger enheter via et kommando-menysystem (talltastene 1–0),
og den nøyaktige plasseringen avhenger av din Input Configuration / faksjon.
Kjør med `dry_run: true` og sjekk at sekvensen i terminalen matcher menyen
din før du setter `dry_run: false`.

Defaults som allerede stemmer i BZ98: **Follow Me = 1**, **Hold = 4**.

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
